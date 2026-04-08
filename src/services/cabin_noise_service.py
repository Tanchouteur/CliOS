import threading
import numpy as np
import sounddevice as sd
from src.services.base_service import BaseService


class CabinNoiseService(BaseService):
    """Capte l'audio du micro pour mesurer la pression acoustique brute (SPL)."""

    def __init__(self, api):
        super().__init__("CabinNoise")
        self.api = api
        self._stream = None

        # Le dictionnaire partagé
        self.api._data["cabin_db_spl"] = 0.0

    def start(self, stop_event):
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="Thread-Noise").start()

    def _audio_callback(self, indata, frames, time_info, status):
        """Fonction appelée automatiquement par le micro des dizaines de fois par seconde."""
        # 1. Calcul de l'énergie moyenne (Root Mean Square)
        rms = np.sqrt(np.mean(indata ** 2))

        if rms > 0:
            raw_db = 20 * np.log10(rms)
            db_spl = raw_db + 98.0 # calibrage

            db_text = f"{db_spl:.1f}"
            self.api._data["audio_db_text"] = db_text

    def _run(self, stop_event):
        try:
            # Ouverture du micro par défaut en continu
            self._stream = sd.InputStream(callback=self._audio_callback, channels=1, samplerate=44100)
            self._stream.start()
            self.set_ok("Microphone actif (Mesure SPL Brute)")
            print(f"[INFO] {self.service_name} : Microphone actif, mesure du SPL en cours...")

            while not stop_event.is_set():
                stop_event.wait(0.5)

        except Exception as e:
            self.set_error(f"Erreur d'accès au micro : {e}")
        finally:
            if self._stream:
                self._stream.stop()
                self._stream.close()

    def stop(self):
        print(f"[INFO] {self.service_name} : Coupure du micro.")