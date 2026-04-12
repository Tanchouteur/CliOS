import os
import threading
import time
from pyo import Server, SfPlayer, Mix, LFO, Biquad, Tone, Disto, Interp, SigTo, Sine, PinkNoise
from src.services.base_service import BaseService


class EngineSoundService(BaseService):
    def __init__(self, api, storage, engine_path):
        super().__init__("EngineSound", storage)
        self.api = api
        self.server = None
        self.engine_path = engine_path

        self.RPM_IDLE = 903.0
        self.RPM_MID = 2000.0
        self.RPM_HIGH = 4000.0

        available_models = ["standard"]
        if os.path.exists(self.engine_path):
            folders = [d for d in os.listdir(self.engine_path) if os.path.isdir(os.path.join(self.engine_path, d))]
            if folders:
                available_models = folders

        # --- PARAMÈTRES AUDIO ---
        self.register_param("sound_model", "Modèle de Son", "list", available_models[0], persistent=True,
                            options=available_models)
        self.register_param("max_vol", "Volume Maximum (%)", "slider", 80.0, min_val=0.0, max_val=100.0)
        self.register_param("idle_vol", "Volume au Ralenti (%)", "slider", 10.0, min_val=0.0, max_val=100.0)
        self.register_param("master_gain", "Amplificateur Global (x)", "slider", 2.5, min_val=1.0, max_val=5.0)
        self.register_param("bass_boost", "Niveau des Basses (%)", "slider", 40.0, min_val=0.0, max_val=100.0)

        # NOUVEAU : Filtre habitacle naturel et Raclement V8 sans déphasage
        self.register_param("cabin_freq", "Filtre Habitacle (Hz)", "slider", 4000.0, min_val=500.0, max_val=15000.0)
        self.register_param("rasp_vol", "Raclement V8 (Rasp) (%)", "slider", 50.0, min_val=0.0, max_val=100.0)

        # --- PARAMÈTRES TURBO & WASTEGATE ---
        self.register_param("turbo_on", "Activer Turbo", "toggle", True)
        self.register_param("turbo_vol", "Sifflement (Whine) (%)", "slider", 10.0, min_val=0.0, max_val=100.0)
        self.register_param("wind_vol", "Aspiration (Whoosh) (%)", "slider", 70.0, min_val=0.0, max_val=100.0)
        self.register_param("turbo_charge", "Temps Charge (s)", "slider", 0.6, min_val=0.1, max_val=2.0)

        self.register_param("wg_active", "Activer Wastegate", "toggle", True)
        self.register_param("wg_vol", "Volume Wastegate (%)", "slider", 40.0, min_val=0.0, max_val=100.0)
        self.register_param("wg_duration", "Durée Pschhht (s)", "slider", 0.4, min_val=0.1, max_val=1.5)

        self.register_param("turbo_decay_wg", "Décharge avec WG (s)", "slider", 0.08, min_val=0.01, max_val=0.3)
        self.register_param("turbo_decay_slow", "Décharge sans WG (s)", "slider", 0.8, min_val=0.3, max_val=3.0)

        self.player_idle = None
        self.player_mid = None
        self.player_high = None
        self.output = None

        self.last_throttle = 0.0
        self.last_boost_target = 0.0
        self.wg_timer = 0.0

    def on_param_changed(self, key: str, value):
        if key == "sound_model" and self.server:
            self.print_message(f"Chargement du nouveau moteur : {value}")
            self._load_sound_model()

    def _load_sound_model(self):
        model_name = self._params["sound_model"]["value"]
        final_sound_path = os.path.join(self.engine_path, model_name)

        path_idle = os.path.join(final_sound_path, "idle.wav")
        path_mid = os.path.join(final_sound_path, "mid.wav")
        path_high = os.path.join(final_sound_path, "high.wav")

        if os.path.exists(path_idle) and os.path.exists(path_mid) and os.path.exists(path_high):
            if self.output:
                self.output.stop()

            self.player_idle = SfPlayer(path_idle, loop=True, speed=self.pitch_idle, mul=self.vol_idle)
            self.player_mid = SfPlayer(path_mid, loop=True, speed=self.pitch_mid, mul=self.vol_mid)
            self.player_high = SfPlayer(path_high, loop=True, speed=self.pitch_high, mul=self.vol_high)

            # 1. Mixage des sources brutes (Mono parfait)
            self.mono_mixer = Mix([
                self.player_idle, self.player_mid, self.player_high,
                self.muffled_synth,
                self.turbo_whistle, self.turbo_harmonic,
                self.spool_filter,
                self.wg_synth
            ], voices=1)

            # 2. Le Raclement (Rasp) repensé : Distorsion harmonique intégrée
            # Au lieu de doubler le son, on crée une version distordue et on fait un fondu (crossfade)
            self.rasp_disto = Disto(self.mono_mixer, drive=0.4, slope=0.8)
            self.rasp_blend = Interp(self.mono_mixer, self.rasp_disto, interp=self.rasp_mix_ctrl)

            # 3. Dual Mono pour l'équilibre G/D
            self.stereo_balancer = self.rasp_blend.mix(2)

            # 4. Le filtre Habitacle : "Tone" (Filtre du 1er ordre, très naturel)
            self.cabin_muffler = Tone(self.stereo_balancer, freq=self.cabin_freq_ctrl)

            # 5. Sortie Master (Amplifiée)
            self.output = self.cabin_muffler * self.master_vol_ctrl
            self.output.out()

            self.set_ok(f"Modèle '{model_name}' chargé.")
        else:
            self.set_error(f"Fichiers manquants dans {model_name}/")

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        try:
            self.server = Server(duplex=0).boot()
            self.server.start()

            self.pitch_idle = SigTo(value=1.0, time=0.05)
            self.pitch_mid = SigTo(value=1.0, time=0.05)
            self.pitch_high = SigTo(value=1.0, time=0.05)

            self.vol_idle = SigTo(value=1.0, time=0.05)
            self.vol_mid = SigTo(value=0.0, time=0.05)
            self.vol_high = SigTo(value=0.0, time=0.05)

            # --- SYNTHÉTISEUR DE BASSES ---
            self.bass_freq_ctrl = SigTo(value=40.0, time=0.05)
            self.bass_vol_ctrl = SigTo(value=0.0, time=0.05)
            self.raw_synth = LFO(freq=self.bass_freq_ctrl, type=1, mul=self.bass_vol_ctrl)
            self.muffled_synth = Biquad(self.raw_synth, freq=120, q=2.0, type=0)

            # --- CONTRÔLE DU RACLEMENT (Blend dynamique) ---
            self.rasp_mix_ctrl = SigTo(value=0.0, time=0.1)

            # --- CONTRÔLE DU FILTRE HABITACLE ---
            self.cabin_freq_ctrl = SigTo(value=4000.0, time=0.1)

            # --- TURBO & WASTEGATE ---
            self.turbo_freq_ctrl = SigTo(value=1000.0, time=0.6)
            self.turbo_vol_ctrl = SigTo(value=0.0, time=0.6)

            self.turbo_whistle = Sine(freq=self.turbo_freq_ctrl, mul=self.turbo_vol_ctrl)
            self.turbo_harmonic = Sine(freq=self.turbo_freq_ctrl * 2.0, mul=self.turbo_vol_ctrl * 0.3)

            self.wind_freq_ctrl = SigTo(value=200.0, time=0.6)
            self.wind_vol_ctrl = SigTo(value=0.0, time=0.6)
            self.spool_noise = PinkNoise()
            self.spool_filter = Biquad(self.spool_noise, freq=self.wind_freq_ctrl, q=0.8, type=2,
                                       mul=self.wind_vol_ctrl)

            self.wg_vol_ctrl = SigTo(value=0.0, time=0.05)
            self.wg_noise = PinkNoise()
            self.wg_synth = Biquad(self.wg_noise, freq=2500.0, q=1.0, type=2, mul=self.wg_vol_ctrl)

            # Contrôle Maître
            self.master_vol_ctrl = SigTo(value=0.0, time=0.1)

            self._load_sound_model()

        except Exception as e:
            self.set_error(f"Échec pyo : {e}")

        threading.Thread(target=self._run, args=(stop_event,), daemon=True).start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            if self.status.value == "OK":
                rpm = self.api._data.get("rpm", 0.0)

                if rpm < 100.0:
                    self.master_vol_ctrl.value = 0.0
                    self.bass_vol_ctrl.value = 0.0
                    self.turbo_vol_ctrl.value = 0.0
                    self.wind_vol_ctrl.value = 0.0
                    self.wg_vol_ctrl.value = 0.0
                    self.rasp_mix_ctrl.value = 0.0
                    time.sleep(0.1)
                    continue

                throttle = self.api._data.get("accel_pos", 0.0) / 100.0
                speed = self.api._data.get("speed", 0.0)

                max_v = self._params["max_vol"]["value"] / 100.0
                idle_v = self._params["idle_vol"]["value"] / 100.0
                gain = self._params["master_gain"]["value"]

                # Échelles
                bass_level = self._params["bass_boost"]["value"] / 100.0
                rasp_level = self._params["rasp_vol"]["value"] / 100.0
                cabin_base = self._params["cabin_freq"]["value"]

                t_vol = (self._params["turbo_vol"]["value"] / 100.0) ** 2
                w_vol = (self._params["wind_vol"]["value"] / 100.0) ** 2
                wg_vol = (self._params["wg_vol"]["value"] / 100.0) ** 2

                # --- TURBO LOGIC ---
                is_turbo_on = self._params["turbo_on"]["value"]
                if is_turbo_on:
                    wg_active = self._params["wg_active"]["value"]
                    wg_duration = self._params["wg_duration"]["value"]
                    decay_wg = self._params["turbo_decay_wg"]["value"]
                    decay_slow = self._params["turbo_decay_slow"]["value"]
                    charge_spd = self._params["turbo_charge"]["value"]

                    raw_torque = self.api._data.get("driver_torque_request")
                    if raw_torque is not None:
                        engine_load = max(0.0, float(raw_torque)) / 100.0
                    else:
                        engine_load = throttle if speed > 5.0 else throttle * 0.15

                    boost_capacity = 0.0
                    if rpm > 2200.0:
                        boost_capacity = 1.0
                    elif rpm > 1400.0:
                        boost_capacity = (rpm - 1400.0) / (2200.0 - 1400.0)

                    boost_target = boost_capacity * engine_load
                    is_releasing = throttle < 0.1 and self.last_throttle >= 0.1

                    if wg_active:
                        if is_releasing and self.last_boost_target > 0.3:
                            self.wg_vol_ctrl.time = 0.05
                            self.wg_vol_ctrl.value = self.last_boost_target * wg_vol
                            self.wg_timer = time.time()

                        if time.time() - self.wg_timer > 0.05:
                            self.wg_vol_ctrl.time = wg_duration
                            self.wg_vol_ctrl.value = 0.0

                        if time.time() - self.wg_timer < wg_duration:
                            boost_target = 0.0
                            self.turbo_vol_ctrl.time = decay_wg
                            self.wind_vol_ctrl.time = decay_wg
                            self.turbo_freq_ctrl.time = decay_wg
                            self.wind_freq_ctrl.time = decay_wg
                        else:
                            if boost_target > self.last_boost_target:
                                self.turbo_vol_ctrl.time = charge_spd
                                self.wind_vol_ctrl.time = charge_spd
                                self.turbo_freq_ctrl.time = charge_spd
                                self.wind_freq_ctrl.time = charge_spd
                            else:
                                self.turbo_vol_ctrl.time = decay_slow
                                self.wind_vol_ctrl.time = decay_slow
                                self.turbo_freq_ctrl.time = decay_slow
                                self.wind_freq_ctrl.time = decay_slow
                    else:
                        self.wg_vol_ctrl.value = 0.0
                        if boost_target > self.last_boost_target:
                            self.turbo_vol_ctrl.time = charge_spd
                            self.wind_vol_ctrl.time = charge_spd
                            self.turbo_freq_ctrl.time = charge_spd
                            self.wind_freq_ctrl.time = charge_spd
                        else:
                            self.turbo_vol_ctrl.time = decay_slow
                            self.wind_vol_ctrl.time = decay_slow
                            self.turbo_freq_ctrl.time = decay_slow
                            self.wind_freq_ctrl.time = decay_slow

                    self.turbo_freq_ctrl.value = 1000.0 + (boost_target * 4000.0)
                    self.wind_freq_ctrl.value = 200.0 + (boost_target * 1800.0)

                    self.turbo_vol_ctrl.value = boost_target * 0.05 * t_vol
                    self.wind_vol_ctrl.value = boost_target * 0.5 * w_vol

                    self.last_throttle = throttle
                    self.last_boost_target = boost_target
                else:
                    self.turbo_vol_ctrl.value = 0.0
                    self.wind_vol_ctrl.value = 0.0
                    self.wg_vol_ctrl.value = 0.0

                # --- LECTURE DES WAVS ---
                self.pitch_idle.value = max(0.5, rpm / self.RPM_IDLE)
                self.pitch_mid.value = max(0.5, rpm / self.RPM_MID)
                self.pitch_high.value = max(0.5, rpm / self.RPM_HIGH)

                v_idle = max(0.0, 1.0 - (abs(rpm - self.RPM_IDLE) / (self.RPM_MID - self.RPM_IDLE)))
                if rpm < self.RPM_MID:
                    v_mid = max(0.0, 1.0 - (abs(rpm - self.RPM_MID) / (self.RPM_MID - self.RPM_IDLE)))
                else:
                    v_mid = max(0.0, 1.0 - (abs(rpm - self.RPM_MID) / (self.RPM_HIGH - self.RPM_MID)))

                v_high = max(0.0, 1.0 - (abs(rpm - self.RPM_HIGH) / (self.RPM_HIGH - self.RPM_MID)))
                if rpm > self.RPM_HIGH: v_high = 1.0

                self.vol_idle.value = v_idle
                self.vol_mid.value = v_mid
                self.vol_high.value = v_high

                # --- DYNAMIQUE MOTEUR ---
                self.bass_freq_ctrl.value = (rpm / 60.0) * 4.0
                self.bass_vol_ctrl.value = (0.2 + (throttle * 0.8)) * bass_level

                # Interpolation du raclement (0.0 = son pur, 0.7 = très crade)
                # Lié à la pédale pour que le moteur "grogne" en charge
                self.rasp_mix_ctrl.value = (throttle * 0.7) * rasp_level

                # Dynamique du Filtre Habitacle
                # Plus on accélère et plus on monte dans les tours, plus le son perce l'isolation
                rpm_ratio = min(1.0, rpm / self.RPM_HIGH)
                self.cabin_freq_ctrl.value = cabin_base + (throttle * 1500.0) + (rpm_ratio * 3000.0)

                # Sortie Master amplifiée
                self.master_vol_ctrl.value = (idle_v + (throttle * (max_v - idle_v))) * gain

            time.sleep(0.05)

    def stop(self):
        super().stop()
        if self.server:
            self.server.stop()
            self.server.shutdown()