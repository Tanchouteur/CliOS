"""OBD-II diagnostics with strict, multi-ECU ISO-TP transport."""

from __future__ import annotations

import collections
import threading
import time

from src.isotp import IsoTpError, IsoTpReassembler
from src.services.base_service import BaseService


class DiagnosticService(BaseService):
    GLOBAL_TIMEOUT_S = 2.5
    RESPONSE_QUIET_S = 0.25
    FLOW_TIMEOUT_S = 0.75

    def __init__(self, runtime, can_provider, *, clock=time.monotonic):
        super().__init__("Diag")
        self.runtime = runtime
        self.provider = can_provider
        self.clock = clock
        self.thread = None
        self._scan_requested = threading.Event()
        self._rx_buffer = collections.deque(maxlen=256)
        self._rx_lock = threading.Lock()

        self.runtime.publish("diagnostics", {
            "codes": [], "scanning": False, "has_scanned": False, "ignition_on": False,
        }, source="diagnostics")

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(
            target=self._run, args=(stop_event,), name=self.service_name, daemon=True,
        )
        self.thread.start()
        super().start(stop_event, implemented=True)

    def request_scan(self):
        self._scan_requested.set()

    def receive_obd_frame(self, frame):
        if 0x7E8 <= frame.arbitration_id <= 0x7EF:
            with self._rx_lock:
                self._rx_buffer.append(frame)

    def _pop_frame(self):
        with self._rx_lock:
            return self._rx_buffer.popleft() if self._rx_buffer else None

    def _clear_frames(self):
        with self._rx_lock:
            self._rx_buffer.clear()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            snapshot = self.runtime.snapshot()
            ignition_on = bool(snapshot.domain("powertrain").get("key_run", False))
            diagnostics = snapshot.domain("diagnostics")
            is_connected = self.provider.is_connected
            self.runtime.publish("diagnostics", {"ignition_on": ignition_on}, source="diagnostics")
            if not is_connected:
                self.set_error("Adaptateur CAN non détecté")
            elif not diagnostics.get("scanning", False):
                self.set_ok("Prêt pour scan")

            if self._scan_requested.wait(timeout=0.5):
                if is_connected:
                    try:
                        self._perform_scan()
                    except (OSError, RuntimeError, ValueError) as exc:
                        self.set_error(f"Erreur pendant le scan : {exc}")
                        self.logger.exception("Échec du scan OBD", extra={"error_code": "OBD_SCAN_FAILED"})
                self._scan_requested.clear()

    def _perform_scan(self):
        self.runtime.publish("diagnostics", {"scanning": True, "codes": []}, source="diagnostics")
        self.set_ok("Initialisation de la communication...")
        self._clear_frames()

        try:
            self.provider.send_frame(0x7DF, [0x02, 0x01, 0x00, 0x55, 0x55, 0x55, 0x55, 0x55])
            time.sleep(0.15)
            self._clear_frames()
            if not self.provider.send_frame(0x7DF, [0x01, 0x03, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55]):
                raise RuntimeError("Impossible d'écrire sur le bus CAN")

            transport = IsoTpReassembler(flow_timeout_s=self.FLOW_TIMEOUT_S)
            deadline = self.clock() + self.GLOBAL_TIMEOUT_S
            quiet_deadline = None
            responses: dict[int, bytes] = {}

            while self.clock() < deadline:
                now = self.clock()
                frame = self._pop_frame()
                if frame is None:
                    for response_id in transport.expire(now):
                        self.logger.warning(
                            "Flux ISO-TP ECU 0x%03X expiré", response_id,
                            extra={"error_code": "ISOTP_FLOW_TIMEOUT"},
                        )
                    if responses and not transport.flows and quiet_deadline is not None and now >= quiet_deadline:
                        break
                    time.sleep(0.005)
                    continue

                response_id = frame.arbitration_id
                try:
                    result = transport.feed(response_id, frame.data, now)
                except IsoTpError as exc:
                    self.logger.warning(str(exc), extra={"error_code": "ISOTP_MALFORMED_FRAME"})
                    continue

                if result.flow_control_id is not None:
                    self.logger.info(
                        "Flow Control ECU 0x%03X vers 0x%03X", response_id, result.flow_control_id,
                        extra={"error_code": "ISOTP_FLOW_CONTROL"},
                    )
                    self.provider.send_frame(
                        result.flow_control_id,
                        [0x30, 0x00, 0x00, 0x55, 0x55, 0x55, 0x55, 0x55],
                    )
                if result.payload is not None:
                    responses[response_id] = result.payload
                    quiet_deadline = now + self.RESPONSE_QUIET_S
                    self.logger.info(
                        "Réponse OBD complète reçue de l'ECU 0x%03X", response_id,
                        extra={"error_code": "OBD_ECU_RESPONSE"},
                    )

            codes: list[str] = []
            seen: set[str] = set()
            for response_id in sorted(responses):
                for code in self._extract_dtc_payload(responses[response_id], response_id):
                    if code not in seen:
                        seen.add(code)
                        codes.append(code)

            self.runtime.publish(
                "diagnostics", {"codes": codes, "has_scanned": True}, source="diagnostics",
            )
            if responses:
                self.set_ok(f"Terminé. {len(codes)} défaut(s) lu(s) sur {len(responses)} ECU.")
            else:
                self.set_warning("Aucune réponse valide des calculateurs")
        finally:
            self.runtime.publish("diagnostics", {"scanning": False}, source="diagnostics")

    def _extract_dtc_payload(self, payload: bytes, response_id: int) -> list[str]:
        if len(payload) < 2 or payload[0] != 0x43:
            self.logger.warning(
                "ECU 0x%03X: réponse rejetée (service attendu 0x43)", response_id,
                extra={"error_code": "OBD_WRONG_SERVICE"},
            )
            return []

        num_dtcs = payload[1]
        codes = []
        for index in range(num_dtcs):
            offset = 2 + index * 2
            if offset + 1 >= len(payload):
                self.logger.warning(
                    "ECU 0x%03X: payload coupé avant DTC %d", response_id, index + 1,
                    extra={"error_code": "OBD_TRUNCATED_PAYLOAD"},
                )
                break
            a, b = payload[offset], payload[offset + 1]
            if a == 0 and b == 0:
                continue
            letter = ("P", "C", "B", "U")[a >> 6]
            codes.append(f"{letter}{(a >> 4) & 0x03}{a & 0x0F:X}{b >> 4:X}{b & 0x0F:X}")
        return codes

    def _decode_dtc_payload(self, payload):
        """Compatibility helper retained for callers outside the transport loop."""
        codes = self._extract_dtc_payload(bytes(payload), 0x7E8)
        self.runtime.publish(
            "diagnostics", {"codes": codes, "has_scanned": True}, source="diagnostics",
        )
        self.set_ok(f"Terminé. {len(codes)} défaut(s) lu(s).")
