import threading

from src.services.base_service import BaseService


class PowertrainMetricsService(BaseService):
    """Computes presentation-independent engine metrics from the vehicle profile."""

    RATE_SECONDS = 1.0 / 20.0

    def __init__(self, api, config, storage=None):
        super().__init__("PowertrainMetrics", storage)
        self.api = api
        engine = config.get("engine", {})
        self._max_torque_nm = float(engine.get("max_torque_nm", 200.0))
        raw_curve = engine.get("performance_curve", [])
        self._curve = sorted(
            (
                (float(point["rpm"]), float(point["torque_nm"]))
                for point in raw_curve
                if isinstance(point, dict) and "rpm" in point and "torque_nm" in point
            ),
            key=lambda point: point[0],
        )
        self._thread = None

    def torque_at_rpm(self, rpm: float) -> float:
        if not self._curve:
            return self._max_torque_nm
        rpm = max(0.0, float(rpm))
        if rpm <= self._curve[0][0]:
            return self._curve[0][1]
        for left, right in zip(self._curve, self._curve[1:]):
            if rpm <= right[0]:
                span = max(1.0, right[0] - left[0])
                fraction = (rpm - left[0]) / span
                return left[1] + (right[1] - left[1]) * fraction
        return self._curve[-1][1]

    @staticmethod
    def _load_pct(data: dict) -> float:
        for key in ("engine_load", "driver_torque_request", "accel_pos", "throttle", "throttle_pct"):
            value = data.get(key)
            if value is not None:
                try:
                    return max(0.0, min(100.0, float(value)))
                except (TypeError, ValueError):
                    continue
        return 0.0

    def calculate(self, data: dict) -> dict:
        rpm = max(0.0, float(data.get("rpm", 0.0) or 0.0))
        load_pct = self._load_pct(data)
        torque_nm = self.torque_at_rpm(rpm) * load_pct / 100.0
        power_kw = rpm * torque_nm / 9549.0 if rpm > 0.0 else 0.0
        return {
            "engine_load_pct": round(load_pct, 1),
            "estimated_torque_nm": round(max(0.0, torque_nm), 1),
            "estimated_power_kw": round(max(0.0, power_kw), 1),
            "estimated_power_hp": round(max(0.0, power_kw * 1.359621617), 1),
        }

    def start(self, stop_event: threading.Event):
        self._thread = threading.Thread(
            target=self._run, args=(stop_event,), daemon=True, name="PowertrainMetricsWorker"
        )
        self._thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            try:
                metrics = self.calculate(self.api.get_display_data())
                self.api.update_domain(
                    "powertrain", metrics, source="powertrain-metrics", ttl_s=0.25
                )
                self.set_ok()
            except Exception as exc:
                self.set_error(f"Calcul moteur impossible : {exc}")
            stop_event.wait(self.RATE_SECONDS)
