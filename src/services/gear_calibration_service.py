import json
import threading
import time
from collections import defaultdict
from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType


class GearCalibrationService(BaseService):
    def __init__(self, api, storage, profile_manager, dynamics_service):
        super().__init__("GearCalibration", storage)
        self.api = api
        self.profile_manager = profile_manager
        self.dynamics_service = dynamics_service

        self.is_calibrating = False
        self.collected_ratios = []
        self._ratio_hist = defaultdict(int)

        self._min_peak_samples = 18
        self._merge_tolerance = 8.0
        self._live_push_period_sec = 2.5
        self._storage_save_period_sec = 1.0
        self._last_live_push = 0.0
        self._last_storage_save = 0.0

        self._profile_id = getattr(self.profile_manager, "active_profile_id", "default") or "default"
        self._storage_hist_key = f"calibration.{self._profile_id}.ratio_hist"
        self._load_progress_from_storage()

        # Initialise l'état de calibration visible par l'interface.
        self.api.update({
            "calibration_active": False,
            "calibration_ratio": 0.0,
            "calibration_count": 0,
            "calibration_gears_found": len(self._extract_reliable_peaks()),
            "calibration_target_gears": self._target_gear_count(),
        })

        self.register_param("calib_toggle", "Mode Étalonnage", ServiceParamType.TOGGLE, False, persistent=False)

    def on_param_changed(self, key: str, value):
        if key == "calib_toggle":
            if value is True:
                self.start_calibration()
            else:
                self.stop_and_save_calibration()

    def start_calibration(self):
        self.is_calibrating = True
        self.collected_ratios.clear()

        # Active l'état de calibration dans l'API.
        self.api.update({
            "calibration_active": True,
            "calibration_count": 0,
            "calibration_gears_found": len(self._extract_reliable_peaks()),
            "calibration_target_gears": self._target_gear_count(),
        })

        self.set_ok("Étalonnage en cours...")
        self.print_message("Étalonnage incrémental actif. Les rapports trouvés sont conservés entre trajets.")

    def stop_and_save_calibration(self):
        self.is_calibrating = False

        # Désactive l'état de calibration dans l'API.
        self.api.update({
            "calibration_active": False,
            "calibration_ratio": 0.0
        })

        if not self.collected_ratios and not self._ratio_hist:
            self.set_warning("Annulé : Aucune donnée.")
            return False

        new_ratios = self._build_candidate_ratios()
        if not new_ratios:
            self.set_error("Échec : Données instables.")
            return False

        config_path = self.profile_manager.get_config_path()
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            if "transmission" not in config_data:
                config_data["transmission"] = {"tolerance": 5.0}

            config_data["transmission"]["ratios"] = new_ratios

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)

            self.dynamics_service.reload_config(config_data)
            self._save_progress_to_storage(force=True)

            self.set_ok(f"Succès : {len(new_ratios)} rapports enregistrés.")
            self.print_message(f"Rapports recalibrés: {new_ratios}")
            return True

        except Exception as e:
            self.set_error(f"Erreur d'écriture : {str(e)}")
            return False

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name=self.service_name).start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            if self.is_calibrating:
                safe_data = self.api.get_display_data()
                speed = safe_data.get("speed", 0.0)
                rpm = safe_data.get("rpm", 0.0)
                throttle = safe_data.get("accel_pos", 0.0)
                clutch = safe_data.get("clutch", False)
                brake = safe_data.get("brake", False)
                reverse = safe_data.get("reverse_engaged", False)

                if throttle > 8.0 and speed > 4.0 and rpm > 900 and not clutch and not brake and not reverse:
                    current_ratio = rpm / speed
                    if self._is_ratio_sample_valid(current_ratio, speed, rpm):
                        self.collected_ratios.append(current_ratio)
                        self._ratio_hist[round(current_ratio)] += 1

                        self.api.update({
                            "calibration_ratio": round(current_ratio, 1),
                            "calibration_count": len(self.collected_ratios),
                            "calibration_gears_found": len(self._extract_reliable_peaks()),
                            "calibration_target_gears": self._target_gear_count(),
                        })

                        now = time.time()
                        self._save_progress_to_storage(now=now)

                        # Ajustement dynamique en RAM toutes les quelques secondes.
                        if now - self._last_live_push >= self._live_push_period_sec:
                            live_ratios = self._build_candidate_ratios()
                            if live_ratios:
                                self.dynamics_service.reload_config({"transmission": {"ratios": live_ratios}})
                            self._last_live_push = now
                else:
                    self.api.update({"calibration_ratio": 0.0})

            stop_event.wait(0.05)

    def _load_existing_ratios(self):
        try:
            config_path = self.profile_manager.get_config_path()
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            ratios = config_data.get("transmission", {}).get("ratios", {})
            return {str(k): float(v) for k, v in ratios.items()}
        except Exception:
            return {}

    def _target_gear_count(self):
        existing = self._load_existing_ratios()
        return max(1, len(existing) if existing else 5)

    def _load_progress_from_storage(self):
        if not self.storage:
            return
        raw = self.storage.get(self._storage_hist_key, {})
        if not isinstance(raw, dict):
            return
        for key, count in raw.items():
            try:
                ratio = int(key)
                samples = int(count)
            except (TypeError, ValueError):
                continue
            if samples > 0:
                self._ratio_hist[ratio] = samples

    def _save_progress_to_storage(self, now=None, force=False):
        if not self.storage:
            return
        now = time.time() if now is None else now
        if not force and (now - self._last_storage_save) < self._storage_save_period_sec:
            return

        payload = {str(r): int(c) for r, c in self._ratio_hist.items() if c > 0}
        self.storage.set(self._storage_hist_key, payload)
        self._last_storage_save = now

    def _is_ratio_sample_valid(self, ratio, speed, rpm):
        if ratio < 8 or ratio > 260:
            return False
        # Renforce la fiabilité en bas rapport pour mieux capter 1/2.
        if speed < 12.0 and rpm < 1500:
            return False
        return True

    def _extract_reliable_peaks(self):
        peaks = [ratio for ratio, count in self._ratio_hist.items() if count >= self._min_peak_samples]
        peaks.sort(reverse=True)
        return peaks

    def _build_candidate_ratios(self):
        peaks = self._extract_reliable_peaks()
        existing = self._load_existing_ratios()

        if not peaks and not existing:
            return {}

        merged = []
        used_peak_idx = set()

        # Préserve les rapports déjà connus, puis les affine si un pic proche est trouvé.
        for _, old_ratio in sorted(existing.items(), key=lambda kv: int(kv[0])):
            best_idx = None
            best_diff = float("inf")

            for idx, peak in enumerate(peaks):
                if idx in used_peak_idx:
                    continue
                diff = abs(float(peak) - old_ratio)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = idx

            if best_idx is not None and best_diff <= self._merge_tolerance:
                used_peak_idx.add(best_idx)
                merged.append(round((old_ratio * 2.0 + float(peaks[best_idx])) / 3.0, 1))
            else:
                merged.append(round(old_ratio, 1))

        # Ajoute les pics non associés.
        for idx, peak in enumerate(peaks):
            if idx not in used_peak_idx:
                merged.append(round(float(peak), 1))

        # Déduplication + tri décroissant (1ère = ratio le plus élevé).
        cleaned = sorted({r for r in merged if r > 0}, reverse=True)
        return {str(i + 1): float(r) for i, r in enumerate(cleaned)}
