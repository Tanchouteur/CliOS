import time
import threading


class PhysicsMockProvider:
    """Moteur physique temps réel avec simulation dynamique et boîte manuelle."""

    def __init__(self, api):
        self.api = api
        self.is_connected = False
        self._running = False

        # --- COMMANDES (Inputs du joueur) ---
        self.throttle = 0.0  # 0 à 100 %
        self.brake = 0.0  # 0 à 100 %
        self.gear = 0  # 0 = N, 1-5 = Vitesses

        # --- ÉTAT PHYSIQUE (Outputs) ---
        self.speed_kmh = 0.0
        self.rpm = 800.0
        self.torque_request = 0.0  # NOUVEAU : Simule la charge moteur (Load)

    def connect(self) -> bool:
        self.is_connected = True
        self._running = True
        threading.Thread(target=self._physics_loop, daemon=True, name="PhysicsMock").start()
        print("[INFO] Moteur Physique (Mock) connecté et en route.")
        return True

    def close(self):
        self.is_connected = False
        self._running = False

    def read_frame(self, timeout=0.1):
        """Méthode factice pour que le CanService boucle sagement."""
        time.sleep(timeout)
        return None

    def _physics_loop(self):
        last_time = time.time()

        self.api._data["ignition_on"] = True
        self.api._data["key_run"] = True

        ratios = {0: 0, 1: 14.5, 2: 8.2, 3: 5.4, 4: 3.9, 5: 3.1}

        while self._running:
            now = time.time()
            dt = now - last_time
            last_time = now

            # --- NOUVEAU : Calcul du Torque Request (Charge ECU) ---
            if self.gear == 0:
                # Au point mort, le moteur ne force pas (15% max)
                target_torque = self.throttle * 0.15
            else:
                # En prise, la demande de couple suit la pédale
                target_torque = self.throttle

            # Lissage pour imiter l'inertie du papillon des gaz et du calculateur
            self.torque_request += (target_torque - self.torque_request) * 5.0 * dt

            # 1. Calcul de la Force Motrice sur les roues
            engine_force = self.throttle * 0.6 if self.gear != 0 else 0.0
            drag = 0.012 * (self.speed_kmh ** 2)
            friction = 0.5

            acceleration = (engine_force - drag - friction - (self.brake * 2.0))
            self.speed_kmh += acceleration * dt
            if self.speed_kmh < 0:
                self.speed_kmh = 0.0

            # 2. Calcul du RPM
            if self.gear == 0:
                target_rpm = 800 + (self.throttle * 60)
            else:
                ratio = ratios.get(self.gear, 1)
                target_rpm = (self.speed_kmh * ratio * 10.0) + 800

                if self.throttle > 50 and self.speed_kmh < 15:
                    target_rpm += (self.throttle * 15)

            self.rpm += (target_rpm - self.rpm) * 8.0 * dt

            if self.rpm < 800: self.rpm = 800
            if self.rpm > 6500: self.rpm = 6500 - (time.time() % 0.1) * 200

            # 3. Dynamique des roues
            front_speed = self.speed_kmh
            rear_speed = self.speed_kmh

            if self.throttle > 80 and self.speed_kmh < 50 and self.gear == 1:
                rear_speed = self.speed_kmh + 30.0
            if self.brake > 80:
                front_speed = 0.0

            # 4. Rapport brut
            if self.gear == 1:
                gear_raw = 106
            elif self.gear == 2:
                gear_raw = 109
            elif self.gear == 3:
                gear_raw = 112
            elif self.gear == 4:
                gear_raw = 113
            elif self.gear == 5:
                gear_raw = 115
            else:
                gear_raw = 100

            # 5. Injection de la télémétrie dans l'API
            current_odo = self.api._data.get("odometer", 10000.0)
            current_fuel = self.api._data.get("fuel_used", 0.0)
            fuel_rate = 0.001 + (self.throttle * 0.0005)

            self.api._data["speed"] = round(self.speed_kmh, 1)
            self.api._data["rpm"] = int(self.rpm)
            self.api._data["wheel_speed_fl"] = round(front_speed, 1)
            self.api._data["wheel_speed_fr"] = round(front_speed, 1)
            self.api._data["wheel_speed_rl"] = round(rear_speed, 1)
            self.api._data["wheel_speed_rr"] = round(rear_speed, 1)
            self.api._data["gear_raw"] = gear_raw
            self.api._data["odometer"] = current_odo + (self.speed_kmh * (dt / 3600.0))
            self.api._data["fuel_used"] = current_fuel + (fuel_rate * dt)
            self.api._data["accel_pos"] = self.throttle
            self.api._data["brake"] = self.brake > 0
            self.api._data["driver_torque_request"] = round(self.torque_request, 1)

            time.sleep(0.02)