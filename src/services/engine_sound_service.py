import os
import threading
import time
from pyo import Server, SfPlayer, Mix, Biquad, Tone, Disto, SigTo, Sine, PinkNoise
import sounddevice as sd
from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType


class EngineSoundService(BaseService):
    def __init__(self, api, storage, engine_path):
        super().__init__("EngineSound", storage)
        self.api = api
        self.server = None
        self.engine_path = engine_path

        self.RPM_IDLE = 803.0
        self.RPM_MID = 1500.0
        self.RPM_HIGH = 3500.0

        available_models = ["standard"]
        if os.path.exists(self.engine_path):
            folders = [d for d in os.listdir(self.engine_path) if os.path.isdir(os.path.join(self.engine_path, d))]
            if folders:
                available_models = folders

        self.register_param("sound_model", "Modele de Son", ServiceParamType.LIST, available_models[0], persistent=True,
                            options=available_models)
        self.register_param("max_vol", "Volume Maximum (%)", ServiceParamType.SLIDER, 80.0, min_val=0.0, max_val=100.0)
        self.register_param("idle_vol", "Volume au Ralenti (%)", ServiceParamType.SLIDER, 10.0, min_val=0.0, max_val=100.0)
        self.register_param("master_gain", "Amplificateur Global (x)", ServiceParamType.SLIDER, 2.5, min_val=1.0, max_val=5.0)
        self.register_param("bass_boost", "Boost Basses Naturelles (%)", ServiceParamType.SLIDER, 40.0, min_val=0.0, max_val=100.0)

        self.register_param("cabin_freq", "Filtre Habitacle (Hz)", ServiceParamType.SLIDER, 1500.0, min_val=300.0, max_val=8000.0)
        self.register_param("rasp_vol", "Raclement V8 (Rasp) (%)", ServiceParamType.SLIDER, 50.0, min_val=0.0, max_val=100.0)
        self.register_param("rasp_freq", "Frequence Rasp (Hz)", ServiceParamType.SLIDER, 400.0, min_val=100.0, max_val=1500.0)

        self.register_param("turbo_on", "Activer Turbo", ServiceParamType.TOGGLE, True)
        self.register_param("turbo_vol", "Sifflement (Whine) (%)", ServiceParamType.SLIDER, 10.0, min_val=0.0, max_val=100.0)
        self.register_param("wind_vol", "Aspiration (Whoosh) (%)", ServiceParamType.SLIDER, 70.0, min_val=0.0, max_val=100.0)
        self.register_param("turbo_charge", "Temps Charge (s)", ServiceParamType.SLIDER, 0.6, min_val=0.1, max_val=2.0)

        self.register_param("wg_active", "Activer Wastegate", ServiceParamType.TOGGLE, True)
        self.register_param("wg_vol", "Volume Wastegate (%)", ServiceParamType.SLIDER, 40.0, min_val=0.0, max_val=100.0)
        self.register_param("wg_duration", "Duree Pschhht (s)", ServiceParamType.SLIDER, 0.4, min_val=0.1, max_val=1.5)

        self.register_param("turbo_decay_wg", "Decharge avec WG (s)", ServiceParamType.SLIDER, 0.08, min_val=0.01, max_val=0.3)
        self.register_param("turbo_decay_slow", "Decharge sans WG (s)", ServiceParamType.SLIDER, 0.8, min_val=0.3, max_val=3.0)

        self.player_idle = None
        self.player_mid = None
        self.player_high = None
        self.output = None

        self.last_throttle = 0.0
        self.last_boost_target = 0.0
        self.wg_timer = 0.0

    def _has_audio_output(self) -> bool:
        """Vérifie qu'une sortie audio exploitable est présente avant de démarrer pyo."""
        try:
            devices = sd.query_devices()
        except Exception:
            return False

        output_devices = [d for d in devices if d.get("max_output_channels", 0) > 0]
        if not output_devices:
            return False

        try:
            default_dev = sd.default.device
            out_index = default_dev[1] if isinstance(default_dev, (list, tuple)) else default_dev
            if isinstance(out_index, int) and out_index >= 0:
                out_info = sd.query_devices(out_index)
                if out_info.get("max_output_channels", 0) > 0:
                    return True
        except Exception:
            pass

        # Si le périphérique par défaut est invalide, autorise le démarrage
        # dès qu'une sortie audio physique est détectée.
        return True

    def on_param_changed(self, key: str, value):
        if key == "sound_model" and self.server:
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

            self.mono_mixer = Mix([
                self.player_idle, self.player_mid, self.player_high,
                self.turbo_whistle, self.turbo_harmonic,
                self.spool_filter,
                self.wg_synth
            ], voices=1)

            self.natural_bass = Biquad(self.mono_mixer, freq=120.0, q=1.0, type=0, mul=self.bass_vol_ctrl)

            self.rasp_bp = Biquad(self.mono_mixer, freq=self.rasp_freq_ctrl, q=2.0, type=2)
            self.rasp_disto = Disto(self.rasp_bp, drive=0.85, slope=0.9, mul=self.rasp_vol_ctrl)

            self.stereo_balancer = self.mono_mixer.mix(2)
            self.bass_stereo = self.natural_bass.mix(2)
            self.rasp_stereo = self.rasp_disto.mix(2)

            self.final_mix = self.stereo_balancer + self.bass_stereo + self.rasp_stereo

            self.cabin_muffler = Biquad(self.final_mix, freq=self.cabin_freq_ctrl, q=0.7, type=0)
            self.output = self.cabin_muffler * self.master_vol_ctrl
            self.output.out()

            self.set_ok(f"Modele '{model_name}' charge.")
        else:
            self.set_error(f"Fichiers manquants dans {model_name}/")

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)

        if not self._has_audio_output():
            self.set_error("No audio output")
            return

        try:
            self.server = Server(duplex=0).boot()
            self.server.start()

            self.pitch_idle = SigTo(value=1.0, time=0.05)
            self.pitch_mid = SigTo(value=1.0, time=0.05)
            self.pitch_high = SigTo(value=1.0, time=0.05)

            self.vol_idle = SigTo(value=1.0, time=0.05)
            self.vol_mid = SigTo(value=0.0, time=0.05)
            self.vol_high = SigTo(value=0.0, time=0.05)

            self.bass_vol_ctrl = SigTo(value=0.0, time=0.1)

            self.rasp_vol_ctrl = SigTo(value=0.0, time=0.05)
            self.rasp_freq_ctrl = SigTo(value=400.0, time=0.1)

            self.cabin_freq_ctrl = SigTo(value=1500.0, time=0.1)

            # Chaîne de synthèse turbo/admission.
            self.turbo_freq_ctrl = SigTo(value=800.0, time=0.6)
            self.turbo_vol_ctrl = SigTo(value=0.0, time=0.6)

            self.turbo_whistle = Sine(freq=self.turbo_freq_ctrl, mul=self.turbo_vol_ctrl)
            # Harmonique limitée pour conserver un timbre naturel.
            self.turbo_harmonic = Sine(freq=self.turbo_freq_ctrl * 1.5, mul=self.turbo_vol_ctrl * 0.1)

            self.wind_freq_ctrl = SigTo(value=300.0, time=0.6)
            self.wind_vol_ctrl = SigTo(value=0.0, time=0.6)
            self.spool_noise = PinkNoise()

            # Filtre passe-bas avec résonance pour modeler l'admission.
            self.spool_filter = Biquad(self.spool_noise, freq=self.wind_freq_ctrl, q=1.2, type=0,
                                       mul=self.wind_vol_ctrl)

            self.wg_vol_ctrl = SigTo(value=0.0, time=0.05)
            self.wg_noise = PinkNoise()
            # Décharge filtrée pour un rendu cockpit.
            self.wg_synth = Biquad(self.wg_noise, freq=1800.0, q=1.0, type=0, mul=self.wg_vol_ctrl)

            self.master_vol_ctrl = SigTo(value=0.0, time=0.1)

            self._load_sound_model()

        except Exception as e:
            self.set_error("No audio output")
            self.print_message(f"Audio backend init failed: {e}")
            self.server = None
            return

        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name=self.service_name).start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            if self.status.value == "OK":
                safe_data = self.api.get_display_data()

                rpm = safe_data.get("rpm", 0.0)

                if rpm < 100.0:
                    self.master_vol_ctrl.value = 0.0
                    self.bass_vol_ctrl.value = 0.0
                    self.turbo_vol_ctrl.value = 0.0
                    self.wind_vol_ctrl.value = 0.0
                    self.wg_vol_ctrl.value = 0.0
                    self.rasp_vol_ctrl.value = 0.0
                    time.sleep(0.1)
                    continue

                throttle = safe_data.get("accel_pos", 0.0) / 100.0
                speed = safe_data.get("speed", 0.0)
                raw_torque = safe_data.get("driver_torque_request")

                if raw_torque is not None:
                    engine_load = max(0.0, float(raw_torque)) / 100.0
                else:
                    engine_load = throttle if speed > 5.0 else throttle * 0.15

                max_v = self._params["max_vol"]["value"] / 100.0
                idle_v = self._params["idle_vol"]["value"] / 100.0
                gain = self._params["master_gain"]["value"]

                bass_level = self._params["bass_boost"]["value"] / 100.0
                rasp_level = self._params["rasp_vol"]["value"] / 100.0
                rasp_freq = self._params["rasp_freq"]["value"]
                cabin_base = self._params["cabin_freq"]["value"]

                t_vol = (self._params["turbo_vol"]["value"] / 100.0) ** 2
                w_vol = (self._params["wind_vol"]["value"] / 100.0) ** 2
                wg_vol = (self._params["wg_vol"]["value"] / 100.0) ** 2

                is_turbo_on = self._params["turbo_on"]["value"]
                if is_turbo_on:
                    wg_active = self._params["wg_active"]["value"]
                    wg_duration = self._params["wg_duration"]["value"]
                    decay_wg = self._params["turbo_decay_wg"]["value"]
                    decay_slow = self._params["turbo_decay_slow"]["value"]
                    charge_spd = self._params["turbo_charge"]["value"]

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

                    # Plafonne les fréquences pour éviter un rendu agressif en habitacle.
                    self.turbo_freq_ctrl.value = 800.0 + (boost_target * 2000.0)
                    self.wind_freq_ctrl.value = 300.0 + (boost_target * 1200.0)

                    # Pondération des composantes whistle/whoosh.
                    self.turbo_vol_ctrl.value = boost_target * 0.03 * t_vol
                    self.wind_vol_ctrl.value = boost_target * 0.8 * w_vol

                    self.last_throttle = throttle
                    self.last_boost_target = boost_target
                else:
                    self.turbo_vol_ctrl.value = 0.0
                    self.wind_vol_ctrl.value = 0.0
                    self.wg_vol_ctrl.value = 0.0

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

                rpm_ratio = min(1.0, rpm / self.RPM_HIGH)

                self.bass_vol_ctrl.value = (0.2 + (engine_load * 2.0)) * bass_level

                self.rasp_freq_ctrl.value = rasp_freq
                self.rasp_vol_ctrl.value = engine_load * 1.5 * rasp_level

                self.cabin_freq_ctrl.value = cabin_base + (engine_load * 1000.0) + (rpm_ratio * 1000.0)

                self.master_vol_ctrl.value = (idle_v + (engine_load * (max_v - idle_v))) * gain

            time.sleep(0.05)

    def stop(self):
        super().stop()
        if self.server:
            try:
                self.server.stop()
                self.server.shutdown()
            except Exception:
                pass
            finally:
                self.server = None
