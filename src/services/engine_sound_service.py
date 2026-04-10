import os
import threading
import time
from pyo import Server, SfPlayer, Mix, LFO, Biquad, Sig
from src.services.base_service import BaseService


class EngineSoundService(BaseService):
    IDLE_RPM = 800.0

    def __init__(self, api, storage, audio_path="assets/sounds/v6_idle.wav"):
        super().__init__("EngineSound", storage)
        self.master_volume = None
        self.output = None
        self.master_filter = None
        self.raw_synth = None
        self.muffled_synth = None
        self.api = api
        self.audio_path = audio_path
        self.server = None
        self.player = None
        self.exhaust_synth = None
        self.mixer = None

        # --- DÉCLARATION DES PARAMÈTRES (Visibles en QML) ---
        self.register_param("max_vol", "Volume Maximum (%)", "slider", 80.0, min_val=0.0, max_val=100.0)
        self.register_param("idle_vol", "Volume au Ralenti (%)", "slider", 10.0, min_val=0.0, max_val=100.0)
        self.register_param("bass_boost", "Niveau des Basses (%)", "slider", 60.0, min_val=0.0, max_val=100.0)
        self.register_param("tone", "Ouverture Filtre (Hz)", "slider", 3500.0, min_val=1000.0, max_val=6000.0)

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        try:
            self.server = Server(duplex=0).boot()
            self.server.start()

            if os.path.exists(self.audio_path):
                self.player = SfPlayer(self.audio_path, loop=True, speed=1.0, mul=0.6)
                self.raw_synth = LFO(freq=40.0, type=3, mul=0.6)
                self.muffled_synth = Biquad(self.raw_synth, freq=150, type=0)
                self.mixer = Mix([self.player, self.muffled_synth], voices=2)

                # Le filtre master prendra sa valeur dynamique dans la boucle
                self.master_filter = Biquad(self.mixer, freq=3500, type=0)

                # Volume master initié à 0, il montera tout seul
                self.master_volume = Sig(0.0)
                self.output = self.master_filter * self.master_volume
                self.output.out()

                self.set_ok("Active Sound (Propre & Filtré) en ligne.")
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

                # --- LECTURE DES PARAMÈTRES EN DIRECT ---
                max_v = self._params["max_vol"]["value"] / 100.0
                idle_v = self._params["idle_vol"]["value"] / 100.0
                bass_level = self._params["bass_boost"]["value"] / 100.0
                base_tone = self._params["tone"]["value"]

                # --- 1. GESTION DES BASSES ---
                real_hz = (rpm / 60.0) * 3.0
                self.raw_synth.setFreq(real_hz)
                self.muffled_synth.setFreq(150 + (throttle * 150))

                # On applique le multiplicateur de basses choisi par l'utilisateur
                self.raw_synth.setMul((0.2 + (throttle * 0.8)) * bass_level)

                # --- 2. GESTION DU WAV (Texture mécanique) ---
                texture_ratio = 1.0 + ((rpm - self.IDLE_RPM) / 10000.0)
                self.player.setSpeed(texture_ratio)

                # Le plafond master s'ouvre en fonction de la tonalité de base
                self.master_filter.setFreq(base_tone + (texture_ratio * 1000))

                # --- 3. VOLUME MASTER ---
                target_vol = idle_v + (throttle * (max_v - idle_v))
                self.master_volume.setValue(target_vol)

            time.sleep(0.05)

    def stop(self):
        super().stop()
        if self.player:
            self.player.stop()
        if self.server:
            self.server.stop()
            self.server.shutdown()