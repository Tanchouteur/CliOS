import os
import threading
import time
from pyo import Server, SfPlayer, Mix, LFO, Biquad, Sig
from src.services.base_service import BaseService


class EngineSoundService(BaseService):
    IDLE_RPM = 800.0
    BASE_VOL = 0.1
    MAX_VOL = 0.8

    def __init__(self, api, audio_path="assets/sounds/v6_idle.wav"):
        super().__init__("SOUND")
        self.api = api
        self.audio_path = audio_path
        self.server = None
        self.player = None

        # Nouveaux composants
        self.exhaust_synth = None
        self.mixer = None

    def start(self, stop_event: threading.Event):
        try:
            self.server = Server(duplex=0).boot()
            self.server.start()

            if os.path.exists(self.audio_path):
                # 1. WAV : La mécanique (Volume fixe, la pédale gérera le volume master)
                self.player = SfPlayer(self.audio_path, loop=True, speed=1.0, mul=0.6)

                # 2. SYNTHÉTISEUR : Onde Triangle (type=3), beaucoup plus douce que la dent de scie
                self.raw_synth = LFO(freq=40.0, type=3, mul=0.6)

                # 3. LE SILENCIEUX (Filtre Biquad type=0 pour LowPass)
                # Coupe net les harmoniques du synthétiseur pour garder que les "boum boum"
                self.muffled_synth = Biquad(self.raw_synth, freq=150, type=0)

                # 4. MIXEUR : On mélange le WAV et les basses
                self.mixer = Mix([self.player, self.muffled_synth], voices=2)

                # 5. LE PLAFOND MASTER (Coupe-Haut)
                # On bloque tout ce qui dépasse 4000 Hz (adieu les sifflements aigus du WAV)
                self.master_filter = Biquad(self.mixer, freq=3500, type=0)

                # 6. CONTRÔLE DU VOLUME GLOBAL (Sans distorsion)
                # Sig permet de changer le volume sans faire de "clic" audio
                self.master_volume = Sig(self.BASE_VOL)
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

                # --- 1. GESTION DES BASSES ---
                real_hz = (rpm / 60.0) * 3.0
                self.raw_synth.setFreq(real_hz)

                # Le pot s'ouvre légèrement avec l'accélérateur
                self.muffled_synth.setFreq(150 + (throttle * 150))
                # Le synthé tape plus fort quand on accélère
                self.raw_synth.setMul(0.3 + (throttle * 0.7))

                # --- 2. GESTION DU WAV (Texture mécanique) ---
                # Ratio d'accélération très écrasé
                texture_ratio = 1.0 + ((rpm - self.IDLE_RPM) / 10000.0)
                self.player.setSpeed(texture_ratio)

                # Quand le moteur monte dans les tours, on ouvre un peu le Plafond Master
                # pour laisser passer le bruit métallique du V6
                self.master_filter.setFreq(3000 + (texture_ratio * 1000))

                # --- 3. VOLUME MASTER ---
                target_vol = self.BASE_VOL + (throttle * (self.MAX_VOL - self.BASE_VOL))
                self.master_volume.setValue(target_vol)

            time.sleep(0.05)

    def stop(self):
        print(f"[INFO] {self.service_name} : Extinction du V6 virtuel...")
        if self.player:
            self.player.stop()
        if self.server:
            self.server.stop()
            self.server.shutdown()