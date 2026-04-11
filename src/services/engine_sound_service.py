import os
import threading
import time
from pyo import Server, SfPlayer, Mix, LFO, Biquad, SigTo
from src.services.base_service import BaseService


class EngineSoundService(BaseService):
    IDLE_RPM = 800.0

    def __init__(self, api, storage, audio_path="assets/sounds/v6_idle.wav"):
        super().__init__("EngineSound", storage)
        self.api = api
        self.audio_path = audio_path
        self.server = None
        self.player = None

        # --- DÉCLARATION DES PARAMÈTRES ---
        self.register_param("max_vol", "Volume Maximum (%)", "slider", 80.0, min_val=0.0, max_val=100.0)
        self.register_param("idle_vol", "Volume au Ralenti (%)", "slider", 10.0, min_val=0.0, max_val=100.0)
        self.register_param("bass_boost", "Niveau des Basses (%)", "slider", 60.0, min_val=0.0, max_val=100.0)
        self.register_param("tone", "Ouverture Filtre (Hz)", "slider", 3500.0, min_val=1000.0, max_val=6000.0)

        # NOUVEAU : Réglage de l'élasticité (Pitch) pour éviter l'effet "Chipmunk"
        self.register_param("pitch_factor", "Sensibilité Tr/min", "slider", 50.0, min_val=10.0, max_val=150.0)

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        try:
            self.server = Server(duplex=0).boot()
            self.server.start()

            if os.path.exists(self.audio_path):
                # --- 1. LES LISSEURS DE SIGNAUX (Anti-Clic & Anti-Lag) ---
                # "time=0.05" signifie que l'audio mettra 50ms à glisser vers la nouvelle valeur.
                self.pitch_ctrl = SigTo(value=1.0, time=0.05)
                self.bass_freq_ctrl = SigTo(value=40.0, time=0.05)
                self.bass_vol_ctrl = SigTo(value=0.0, time=0.05)
                self.master_vol_ctrl = SigTo(value=0.0, time=0.1)  # Plus lent pour le volume général
                self.filter_ctrl = SigTo(value=3500.0, time=0.1)

                # --- 2. LE ROUTAGE AUDIO (Lié aux lisseurs) ---
                self.player = SfPlayer(self.audio_path, loop=True, speed=self.pitch_ctrl, mul=0.6)
                self.raw_synth = LFO(freq=self.bass_freq_ctrl, type=3, mul=self.bass_vol_ctrl)
                self.muffled_synth = Biquad(self.raw_synth, freq=150, type=0)

                self.mixer = Mix([self.player, self.muffled_synth], voices=2)
                self.master_filter = Biquad(self.mixer, freq=self.filter_ctrl, type=0)

                # Le volume master est maintenant directement le lisseur
                self.output = self.master_filter * self.master_vol_ctrl
                self.output.out()

                self.set_ok("Active Sound (Anti-Clic activé) en ligne.")
            else:
                self.set_warning(f"Fichier audio introuvable : {self.audio_path}")

        except Exception as e:
            self.set_error(f"Échec pyo : {e}")

        threading.Thread(target=self._run, args=(stop_event,), daemon=True).start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            if self.player and self.status.value == "OK":
                rpm = self.api._data.get("rpm", self.IDLE_RPM)
                throttle = self.api._data.get("accel_pos", 0.0) / 100.0

                max_v = self._params["max_vol"]["value"] / 100.0
                idle_v = self._params["idle_vol"]["value"] / 100.0
                bass_level = self._params["bass_boost"]["value"] / 100.0
                base_tone = self._params["tone"]["value"]
                pitch_sens = self._params["pitch_factor"]["value"] / 100.0

                # --- MISE À JOUR DES LISSEURS ---

                # Basses
                real_hz = (rpm / 60.0) * 3.0
                self.bass_freq_ctrl.value = real_hz
                self.muffled_synth.setFreq(150 + (throttle * 150))  # Petit ajustement direct permis
                self.bass_vol_ctrl.value = (0.2 + (throttle * 0.8)) * bass_level

                # WAV (Pitch)
                # Formule plus réaliste : Si RPM x2, vitesse audio x2.
                # On pondère avec 'pitch_sens' pour éviter que ça ne monte trop vite dans les aigus.
                ratio = 1.0 + (((rpm / self.IDLE_RPM) - 1.0) * pitch_sens)
                self.pitch_ctrl.value = max(0.5, ratio)  # Ne descend jamais en dessous de la moitié

                # Filtre & Volume Master
                self.filter_ctrl.value = base_tone + (throttle * 1500)
                self.master_vol_ctrl.value = idle_v + (throttle * (max_v - idle_v))

            time.sleep(0.05)

    def stop(self):
        super().stop()
        if self.player:
            self.player.stop()
        if self.server:
            self.server.stop()
            self.server.shutdown()