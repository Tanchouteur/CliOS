import os
import json
import time
import shutil
import threading
import psutil
from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType


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
        self.usb_history_filename = ".clios_export_history.json"
        self.is_exporting = False
        self._force_reexport_all = False

        # Enregistrement des parametres modifiables depuis l'interface
        self.register_param("scan_interval", "Fréquence de scan (s)", ServiceParamType.SLIDER,
                            10.0, min_val=5.0, max_val=60.0)
        self.register_param("delete_after", "Supprimer après export", ServiceParamType.TOGGLE, False)
        self.register_param("reexport_all", "Ré-exporter tout", ServiceParamType.BUTTON, False, persistent=False)

        # Initialisation du registre interne des fichiers exportes
        self.history_key = f"services.{self.service_name}.history_v2"
        raw_history = self.storage.get(self.history_key, []) if self.storage else []
        self.export_history = self._normalize_history_entries(raw_history)

        # Migration douce depuis l'ancien format (liste de noms de fichiers).
        if self.storage:
            legacy = self.storage.get(f"services.{self.service_name}.history", [])
            if isinstance(legacy, list) and any("|" in str(entry) for entry in legacy):
                self.export_history.update(self._normalize_history_entries(legacy))

    def on_param_changed(self, key: str, value):
        if key == "reexport_all" and bool(value):
            self.request_reexport_all()

    def request_reexport_all(self):
        self._force_reexport_all = True
        self.print_message("Ré-export complet demandé pour le prochain cycle USB.")
        self.bridge.send_notification("INFO", "Re-export total programme", 3000)

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

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            target_folder = config.get("target_folder", "ClOS_Exports")
            export_dest = self._resolve_export_destination(mountpoint, target_folder)
            os.makedirs(export_dest, exist_ok=True)
            usb_history = self._load_usb_history(export_dest)

            exported_count = 0
            pending_files = []

            if os.path.exists(self.data_dir):
                for filename in os.listdir(self.data_dir):
                    if not filename.endswith(".json"):
                        continue

                    src = os.path.join(self.data_dir, filename)
                    if not os.path.isfile(src):
                        continue

                    signature = self._build_signature(src, filename)
                    if not self._force_reexport_all:
                        if signature in self.export_history:
                            continue
                        if signature in usb_history:
                            continue

                    tmp_dst = os.path.join(export_dest, filename + ".tmp")
                    final_dst = os.path.join(export_dest, filename)
                    pending_files.append((filename, src, tmp_dst, final_dst, signature))

            if not pending_files:
                self.set_ok("Aucun nouveau fichier a exporter.")
                return

            self.set_warning("Processus d'exportation actif.")
            mode_label = " (mode re-export total)" if self._force_reexport_all else ""
            self.bridge.send_notification("INFO", f"Debut de l'exportation USB{mode_label}", 3000)

            for filename, src, tmp_dst, final_dst, signature in pending_files:
                # Copie atomique
                shutil.copy2(src, tmp_dst)
                os.replace(tmp_dst, final_dst)

                # Mise a jour du registre
                self.export_history.add(signature)
                usb_history.add(signature)
                exported_count += 1

                # Suppression optionnelle
                if self._params["delete_after"]["value"]:
                    os.remove(src)

            # Persistance du registre
            if self.storage:
                self.storage.set(self.history_key, sorted(self.export_history))
            self._save_usb_history(export_dest, usb_history)

            msg = f"Export terminé : {exported_count} fichiers."
            self.set_ok(msg)
            self.bridge.send_notification("OK", msg, 5000)
            self._force_reexport_all = False

        except Exception as e:
            self.set_error(f"Echec du transfert : {e}")
            self.bridge.send_notification("ERROR", "Échec de l'exportation", 5000)
        finally:
            self.is_exporting = False

    def _build_signature(self, src: str, filename: str) -> str:
        st = os.stat(src)
        return f"{filename}|{st.st_size}|{st.st_mtime_ns}"

    def _load_usb_history(self, export_dest: str) -> set:
        history_path = os.path.join(export_dest, self.usb_history_filename)
        if not os.path.exists(history_path):
            return set()

        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list):
                return self._normalize_history_entries(data)
            if isinstance(data, dict):
                entries = data.get("entries", [])
                if isinstance(entries, list):
                    return self._normalize_history_entries(entries)
        except Exception:
            pass
        return set()

    def _save_usb_history(self, export_dest: str, history: set):
        history_path = os.path.join(export_dest, self.usb_history_filename)
        tmp_path = history_path + ".tmp"
        payload = {
            "version": 2,
            "updated_at": int(time.time()),
            "entries": sorted(history),
        }
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, history_path)

    def _normalize_history_entries(self, entries) -> set:
        if not isinstance(entries, list):
            return set()
        normalized = set()
        for entry in entries:
            val = str(entry)
            if "|" in val:
                normalized.add(val)
        return normalized

    def _resolve_export_destination(self, mountpoint: str, target_folder: str) -> str:
        folder = str(target_folder or "ClOS_Exports").strip()
        if not folder:
            folder = "ClOS_Exports"

        # Refuse les chemins absolus ou traversées de répertoire.
        candidate = os.path.normpath(folder)
        if os.path.isabs(candidate) or candidate.startswith("..") or "/.." in candidate:
            raise ValueError("target_folder invalide dans clos_export.json")

        export_dest = os.path.normpath(os.path.join(mountpoint, candidate))
        mount_abs = os.path.abspath(mountpoint)
        dest_abs = os.path.abspath(export_dest)
        if not (dest_abs == mount_abs or dest_abs.startswith(mount_abs + os.sep)):
            raise ValueError("target_folder sort du point de montage")
        return export_dest

