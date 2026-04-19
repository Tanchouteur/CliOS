import os
import json
import time
import shutil
import threading
import psutil
from src.services.base_service import BaseService, ServiceStatus


class ExportService(BaseService):
    """
    Service gérant l'exportation autonome des données vers des supports physiques ou distants.
    Intègre une vérification périodique et une journalisation des fichiers traités.
    """

    def __init__(self, bridge, storage, data_dir: str):
        super().__init__("Export", storage)
        self.bridge = bridge
        self.data_dir = data_dir
        self.config_filename = "clos_export.json"
        self.is_exporting = False

        # Enregistrement des parametres modifiables depuis l'interface
        self.register_param("scan_interval", "Fréquence de scan (s)", "slider", 10.0, min_val=5.0, max_val=60.0)
        self.register_param("delete_after", "Supprimer après export", "toggle", False)

        # Initialisation du registre interne des fichiers exportes
        self.history_key = f"services.{self.service_name}.history"
        self.export_history = set(self.storage.get(self.history_key, [])) if self.storage else set()

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name=self.service_name).start()

    def _run(self, stop_event: threading.Event):
        """Boucle principale orchestrant la detection."""
        # Attente initiale pour ne pas surcharger le demarrage du systeme
        time.sleep(5.0)

        while not stop_event.is_set():
            if not self.is_exporting:
                self._check_usb_drives()

            # Recuperation dynamique du delai d'attente
            sleep_time = self._params["scan_interval"]["value"]
            stop_event.wait(sleep_time)

    def _check_usb_drives(self):
        """Recherche le fichier de configuration sur les partitions externes."""
        try:
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                if p.mountpoint.startswith(('/snap', '/boot', '/efi', '/dev')):
                    continue

                config_path = os.path.join(p.mountpoint, self.config_filename)

                if os.path.exists(config_path):
                    self._process_usb_export(p.mountpoint, config_path)
                    break

        except Exception as e:
            self.set_error(f"Erreur d'analyse des partitions : {e}")

    def _process_usb_export(self, mountpoint: str, config_path: str):
        """Execute le transfert de donnees de maniere securisee."""
        self.is_exporting = True
        self.set_warning("Processus d'exportation actif.")
        self.bridge.send_notification("INFO", "Début de l'exportation USB", 3000)

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            target_folder = config.get("target_folder", "ClOS_Exports")
            export_dest = os.path.join(mountpoint, target_folder)
            os.makedirs(export_dest, exist_ok=True)

            exported_count = 0

            if os.path.exists(self.data_dir):
                for filename in os.listdir(self.data_dir):
                    if not filename.endswith(".json"):
                        continue

                    # Verification dans le registre
                    if filename in self.export_history:
                        continue

                    src = os.path.join(self.data_dir, filename)
                    tmp_dst = os.path.join(export_dest, filename + ".tmp")
                    final_dst = os.path.join(export_dest, filename)

                    # Copie atomique
                    shutil.copy2(src, tmp_dst)
                    os.rename(tmp_dst, final_dst)

                    # Mise a jour du registre
                    self.export_history.add(filename)
                    exported_count += 1

                    # Suppression optionnelle
                    if self._params["delete_after"]["value"]:
                        os.remove(src)

            # Persistance du registre
            if self.storage:
                self.storage.set(self.history_key, list(self.export_history))

            # Neutralisation du declencheur
            os.rename(config_path, config_path + ".done")

            msg = f"Export terminé : {exported_count} fichiers."
            self.set_ok(msg)
            self.bridge.send_notification("OK", msg, 5000)

        except Exception as e:
            self.set_error(f"Echec du transfert : {e}")
            self.bridge.send_notification("ERROR", "Échec de l'exportation", 5000)
        finally:
            self.is_exporting = False