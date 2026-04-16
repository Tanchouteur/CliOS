import time
import threading
import numpy as np
import sounddevice as sd
from src.services.base_service import BaseService


class CabinNoiseService(BaseService):
    """Capte l'audio du micro pour mesurer le SPL et la fréquence dominante."""

    def __init__(self, api, storage=None):
        super().__init__("Noise", storage)
        self.api = api
        self._stream = None

        self._last_fft_time = 0

        # --- CORRECTION : Écriture sécurisée de l'initialisation ---
        self.api.update({
            "cabin_db_spl": 0.0,
            "cabin_freq_hz": 0
        })

        # --- DÉCLARATION DES PARAMÈTRES DYNAMIQUES  ---
        self.register_param("calib_offset", "Calibration Micro (dB)", "slider", 87.0, min_val=50.0, max_val=120.0)
        self.register_param("fft_threshold", "Seuil de Silence (dB)", "slider", 40.0, min_val=20.0, max_val=80.0)
        self.register_param("fft_rate", "Rafraîchissement FFT (s)", "slider", 0.25, min_val=0.05, max_val=1.0)

    def start(self, stop_event):
        super().start(stop_event, implemented=True)
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name=self.service_name).start()

    def _audio_callback(self, indata, frames, time_info, status):
        audio_data = indata[:, 0]
        rms = np.sqrt(np.mean(audio_data ** 2))

        if rms > 0:
            calib = self._params["calib_offset"]["value"]
            threshold = self._params["fft_threshold"]["value"]
            rate = self._params["fft_rate"]["value"]

            raw_db = 20 * np.log10(rms)
            db_spl = raw_db + calib

            # --- CORRECTION : Préparation du dictionnaire de mise à jour ---
            updates = {
                "audio_db_text": f"{db_spl:.1f}",
                "cabin_db_spl": db_spl # Au cas où tu as besoin de la valeur numérique ailleurs
            }

            now = time.time()

            if db_spl > threshold and (now - self._last_fft_time) > rate:
                spectre = np.abs(np.fft.rfft(audio_data))
                spectre[0] = 0
                frequences = np.fft.rfftfreq(len(audio_data), d=1 / 44100)
                freq_dominante = frequences[np.argmax(spectre)]

                # On ajoute la fréquence au dictionnaire
                updates["cabin_freq_hz"] = int(freq_dominante)
                self._last_fft_time = now

            # --- CORRECTION : Envoi groupé et verrouillé à l'API ---
            self.api.update(updates)

    def _run(self, stop_event):
        try:
            self._stream = sd.InputStream(callback=self._audio_callback, channels=1, samplerate=44100)
            self._stream.start()
            self.set_ok("Microphone actif")

            while not stop_event.is_set():
                stop_event.wait(0.5)

        except Exception as e:
            self.set_error(f"Erreur d'accès au micro : {e}")
        finally:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                super().stop()