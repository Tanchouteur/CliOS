import threading

from src.services.base_service import BaseService
from src.state_store import StatePatch


class VehicleMetricsService(BaseService):
    """Produces profile-aware powertrain metrics and alert states at 20 Hz."""

    RATE_SECONDS = 1.0 / 20.0

    def __init__(self, runtime, config, storage=None):
        super().__init__("VehicleMetrics", storage)
        self.runtime = runtime
        engine = config.get("engine", {})
        fuel = config.get("fuel", {})
        temperature = config.get("engine_temp", {})
        tachometer = config.get("tachometer", {})
        self._max_torque_nm = float(engine.get("max_torque_nm", 200.0))
        self._fuel_capacity_l = float(fuel.get("max_liters", 55.0))
        self._fuel_reserve_ratio = float(fuel.get("reserve_percentage", 0.15))
        self._temperature_warning_c = float(temperature.get("warning", 105.0))
        self._redline_rpm = float(tachometer.get("redline_rpm", 6500.0))
        self._curve = sorted(
            (
                (float(point["rpm"]), float(point["torque_nm"]))
                for point in engine.get("performance_curve", [])
                if isinstance(point, dict) and "rpm" in point and "torque_nm" in point
            ),
            key=lambda point: point[0],
        )
        self._thread = None

    def torque_at_rpm(self, rpm):
        if not self._curve:
            return self._max_torque_nm
        rpm = max(0.0, float(rpm))
        if rpm <= self._curve[0][0]:
            return self._curve[0][1]
        for left, right in zip(self._curve, self._curve[1:]):
            if rpm <= right[0]:
                fraction = (rpm - left[0]) / max(1.0, right[0] - left[0])
                return left[1] + (right[1] - left[1]) * fraction
        return self._curve[-1][1]

    @staticmethod
    def _load_pct(powertrain):
        # Les métriques dérivées publiées par ce service ne doivent jamais être
        # réutilisées comme entrée au cycle suivant. La charge suit uniquement
        # les signaux bruts ECU, avec la pédale comme repli.
        for key in ("driver_torque_request", "accel_pos"):
            if powertrain.get(key) is not None:
                try:
                    return max(0.0, min(100.0, float(powertrain[key])))
                except (TypeError, ValueError):
                    pass
        return 0.0

    def calculate(self, powertrain):
        rpm = max(0.0, float(powertrain.get("rpm", 0.0) or 0.0))
        load_pct = self._load_pct(powertrain)
        available_torque_nm = self.torque_at_rpm(rpm)
        torque_nm = available_torque_nm * load_pct / 100.0
        power_kw = rpm * torque_nm / 9549.0 if rpm > 0.0 else 0.0
        fuel_level = max(0.0, float(powertrain.get("fuel_level", 0.0) or 0.0))
        engine_temp = float(powertrain.get("engine_temp", 0.0) or 0.0)
        ignition = bool(powertrain.get("ignition_on") or powertrain.get("key_run"))
        return (
            {
                "engine_load_pct": round(load_pct, 1),
                "available_torque_nm": round(available_torque_nm, 1),
                "estimated_torque_nm": round(torque_nm, 1),
                "estimated_power_kw": round(power_kw, 1),
                "estimated_power_hp": round(power_kw * 1.359621617, 1),
            },
            {
                "low_fuel": self._fuel_capacity_l > 0 and fuel_level / self._fuel_capacity_l <= self._fuel_reserve_ratio,
                "hot_engine": engine_temp >= self._temperature_warning_c,
                "redline": rpm >= self._redline_rpm,
                "engine_light": "ORANGE" if ignition and rpm < 300.0 else "OFF",
            },
        )

    def start(self, stop_event):
        self._thread = threading.Thread(
            target=self._run, args=(stop_event,), daemon=True, name="VehicleMetricsWorker"
        )
        self._thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event):
        while not stop_event.is_set():
            try:
                powertrain = self.runtime.snapshot().domain("powertrain")
                metrics, alerts = self.calculate(powertrain)
                self.runtime.publish_many((
                    StatePatch(
                        "powertrain", metrics, "vehicle-metrics", ttl_s=0.25,
                        units={
                            "engine_load_pct": "%",
                            "available_torque_nm": "N·m",
                            "estimated_torque_nm": "N·m",
                            "estimated_power_kw": "kW",
                            "estimated_power_hp": "ch",
                        },
                    ),
                    StatePatch("alerts", alerts, "vehicle-metrics", ttl_s=0.25),
                ))
                self.set_ok()
            except Exception as exc:
                self.set_error(f"Calcul véhicule impossible : {exc}")
            stop_event.wait(self.RATE_SECONDS)
