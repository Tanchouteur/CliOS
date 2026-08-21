"""Fournisseur matériel virtuel CAN et moteur physique unifié pour CliOS.

Assure l'interface matérielle virtuelle attendue par CanService et DiagnosticService,
génère les trames CAN réelles et maintient la synchronisation du runtime véhicule.
"""

import time
import threading
import can
from src.state_store import StatePatch
from src.simulation.models import VehicleParameters
from src.simulation.physics_engine import PhysicsEngine
from src.simulation.can_encoder import CanFrameEncoder
from src.simulation.scenarios import ScenarioRunner, get_builtin_scenarios


class PhysicsMockProvider:
    """Fournisseur CAN virtuel complet avec moteur physique et répondeur ISO-TP OBD2."""

    def __init__(self, runtime, config: dict | None = None, can_db_path: str | None = None):
        self.runtime = runtime
        self.channel = "mock-can0"
        self.is_connected = False
        self._running = False
        self._thread = None
        self._lock = threading.RLock()

        # Initialisation des sous-systèmes
        self.params = VehicleParameters.from_config(config) if config else VehicleParameters()
        self.engine = PhysicsEngine(self.params)
        self.encoder = CanFrameEncoder()
        self.scenario_runner = ScenarioRunner(self)
        self.scenarios = {s.name: s for s in get_builtin_scenarios()}
        self.obd_callback = None

    def register_obd_callback(self, callback):
        """Enregistre une fonction de rappel pour la réception directe des trames OBD2."""
        self.obd_callback = callback

    # =========================================================================
    # INTERFACE CAN PROVIDER (Attendue par CanService et DiagnosticService)
    # =========================================================================

    def connect(self) -> bool:
        """Démarre le bus virtuel et la boucle physique temps réel."""
        with self._lock:
            if self.is_connected:
                return True
            self.is_connected = True
            self._running = True
            self._thread = threading.Thread(
                target=self._physics_loop,
                daemon=True,
                name="PhysicsMockThread"
            )
            self._thread.start()
            print(f"[INFO] Simulateur Physique & Bus CAN Virtuel ({self.params.label}) démarré.")
            return True

    def close(self):
        """Arrête la simulation et clôture l'interface virtuelle."""
        with self._lock:
            self.is_connected = False
            self._running = False
            self.scenario_runner.stop()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.5)
            self._thread = None

    def read_frame(self, timeout: float = 0.01) -> can.Message | None:
        """Extrait la trame CAN suivante de la file d'attente générée."""
        if not self.is_connected:
            return None

        # Dépile une trame si disponible
        if self.encoder.frame_queue:
            try:
                return self.encoder.frame_queue.popleft()
            except IndexError:
                pass

        if timeout > 0:
            time.sleep(min(timeout, 0.005))

        if self.encoder.frame_queue:
            try:
                return self.encoder.frame_queue.popleft()
            except IndexError:
                pass

        return None

    def send_frame(self, can_id: int, data: list) -> bool:
        """Reçoit une trame émise sur le bus virtuel (ex: requêtes OBD-II de DiagnosticService)."""
        if not self.is_connected:
            return False

        msg = can.Message(arbitration_id=can_id, data=bytearray(data), is_extended_id=False, timestamp=time.time())
        # Traitement immédiat par le répondeur ISO-TP OBD2
        responses = self.encoder.handle_obd_request(msg, self.engine.state.active_dtcs)
        if self.obd_callback:
            for resp in responses:
                self.obd_callback(resp)
        return True

    # =========================================================================
    # PROPRIÉTÉS ET COMMANDES DE PILOTAGE
    # =========================================================================

    @property
    def throttle(self) -> float:
        return self.engine.state.throttle_pedal

    @throttle.setter
    def throttle(self, value: float):
        self.engine.state.throttle_pedal = max(0.0, min(100.0, float(value)))

    @property
    def brake(self) -> float:
        return self.engine.state.brake_pedal

    @brake.setter
    def brake(self, value: float):
        self.engine.state.brake_pedal = max(0.0, min(100.0, float(value)))

    @property
    def clutch(self) -> float:
        return self.engine.state.clutch_pedal

    @clutch.setter
    def clutch(self, value: float):
        self.engine.state.clutch_pedal = max(0.0, min(100.0, float(value)))

    @property
    def gear(self) -> int:
        return self.engine.state.selected_gear

    @gear.setter
    def gear(self, value: int):
        self.engine.state.selected_gear = int(value)

    @property
    def steering(self) -> float:
        return self.engine.state.steering_angle_deg

    @steering.setter
    def steering(self, value: float):
        self.engine.state.steering_angle_deg = float(value)

    @property
    def handbrake(self) -> bool:
        return self.engine.state.handbrake

    @handbrake.setter
    def handbrake(self, value: bool):
        self.engine.state.handbrake = bool(value)

    @property
    def speed_kmh(self) -> float:
        return self.engine.state.speed_kmh

    @property
    def rpm(self) -> float:
        return self.engine.state.rpm

    @property
    def torque_request(self) -> float:
        return self.engine.state.driver_torque_request

    def set_ignition(self, state: bool):
        """Active ou coupe le contact."""
        self.engine.state.ignition_on = state
        self.engine.state.key_run = state
        self.engine.state.key_acc = state
        if not state:
            self.engine.state.engine_running = False

    def set_starter(self, active: bool):
        """Actionne le démarreur."""
        self.engine.state.starter_active = active

    def inject_dtcs(self, dtcs: list[str]):
        """Injecte une liste de codes défauts OBD2."""
        self.engine.state.active_dtcs = list(dtcs)

    def clear_dtcs(self):
        """Efface les codes défauts."""
        self.engine.state.active_dtcs.clear()

    # =========================================================================
    # BOUCLE PHYSIQUE ET SYNCHRONISATION RUNTIME
    # =========================================================================

    def _physics_loop(self):
        last_time = time.time()
        last_sync_ts = 0.0

        # Publication initiale
        self.runtime.publish("powertrain", {
            "ignition_on": self.engine.state.ignition_on,
            "key_run": self.engine.state.key_run,
            "key_acc": self.engine.state.key_acc,
        }, source="physics-mock")

        while self._running:
            now = time.time()
            dt = now - last_time
            last_time = now

            # Évite les pas de temps aberrants lors de freezes système
            dt = min(0.05, max(0.001, dt))

            # 1. Mise à jour de la physique du véhicule
            state = self.engine.update(dt)

            # 2. Ordonnancement et émission des trames CAN
            self.encoder.schedule_frames(state, now)

            # 3. Synchronisation directe sécurisée avec le Runtime à 50 Hz
            if now - last_sync_ts >= 0.02:
                last_sync_ts = now
                self.runtime.publish_many((
                    StatePatch("powertrain", {
                        "rpm": int(state.rpm),
                        "engine_temp": state.engine_temp_c,
                        "fuel_used": round(state.fuel_used_total_l, 4),
                        "fuel_level": round(state.fuel_level_l, 1),
                        "accel_pos": state.throttle_pedal,
                        "accel_computed": state.throttle_pedal,
                        "driver_torque_request": state.driver_torque_request,
                        "torque_available": state.torque_available,
                        "glow_plug_status": state.glow_plug_status,
                        "ignition_on": state.ignition_on,
                        "key_acc": state.key_acc,
                        "key_run": state.key_run,
                    }, "physics-mock", ttl_s=0.25),

                    StatePatch("motion", {
                        "speed": state.speed_kmh,
                        "speed_dashboard": state.speed_dashboard_kmh,
                        "odometer": round(state.odometer_km, 1),
                        "distance": round(state.distance_trip_km, 2),
                        "gear_raw": state.gear_raw,
                        "brake": state.brake_pedal > 0.0 or state.handbrake,
                        "brake_pressed": state.brake_pedal > 0.0 or state.handbrake,
                        "clutch": state.clutch_pedal > 20.0,
                        "handbrake": state.handbrake,
                        "reverse": state.selected_gear == -1,
                        "reverse_engaged": state.selected_gear == -1,
                    }, "physics-mock", ttl_s=0.25),

                    StatePatch("wheels", {
                        "wheel_fl_speed": state.wheel_fl_speed,
                        "wheel_fr_speed": state.wheel_fr_speed,
                        "wheel_rl_speed": state.wheel_rl_speed,
                        "wheel_rr_speed": state.wheel_rr_speed,
                        "wheel_slip_fl": state.wheel_fl_slip,
                        "wheel_slip_fr": state.wheel_fr_slip,
                        "wheel_slip_rl": state.wheel_rl_slip,
                        "wheel_slip_rr": state.wheel_rr_slip,
                        "wheel_lock_fl": state.wheel_fl_lock,
                        "wheel_lock_fr": state.wheel_fr_lock,
                        "wheel_lock_rl": state.wheel_rl_lock,
                        "wheel_lock_rr": state.wheel_rr_lock,
                    }, "physics-mock", ttl_s=0.25),

                    StatePatch("body", {
                        "pos_lights": state.pos_lights or state.low_beam or state.high_beam,
                        "low_beam": state.low_beam,
                        "high_beam": state.high_beam,
                        "fog_front": state.fog_front,
                        "fog_rear": state.fog_rear,
                        "turn_left": state.turn_left or state.hazard,
                        "turn_right": state.turn_right or state.hazard,
                        "door_fl_open": state.door_fl_open,
                        "door_fr_open": state.door_fr_open,
                        "door_rl_open": state.door_rl_open,
                        "door_rr_open": state.door_rr_open,
                        "trunk_open": state.trunk_open,
                        "doors_locked": state.doors_locked,
                        "trunk_locked": state.trunk_locked,
                        "driver_unbelted": state.driver_unbelted,
                        "passenger_disabled": state.passenger_disabled,
                        "brightness": state.brightness_pct,
                    }, "physics-mock", ttl_s=0.25),

                    StatePatch("dynamics", {
                        "steering_angle": state.steering_angle_deg,
                        "steering_speed": state.steering_speed_dps,
                    }, "physics-mock", ttl_s=0.25),

                    StatePatch("assistance", {
                        "regulateur_mode": state.regulateur_mode,
                        "regulateur_statut": state.regulateur_statut,
                        "vitesse_regulateur": state.vitesse_regulateur_kmh,
                    }, "physics-mock", ttl_s=0.25),

                    StatePatch("environment", {
                        "outside_temp": state.outside_temp_c,
                    }, "physics-mock", ttl_s=0.25),
                ))

            time.sleep(0.01)  # ~100 Hz
