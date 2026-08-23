"""Release discovery and updater operations delegated by DashboardBridge."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from src.release_catalog import CatalogError, ReleaseCatalog
from src.release_manager import ReleaseManager
from src.updater_client import UpdaterClient, UpdaterClientError


class UpdaterController:
    def __init__(self, target):
        self.target = target

    def poll_status(self) -> None:
        target = self.target
        if target._updater_poll_running:
            return
        target._updater_poll_running = True

        def task() -> None:
            try:
                response = UpdaterClient(timeout=2).status()
                status = response.get("result", response)
                state = str(status.get("state", "IDLE"))
                signature = (
                    state, int(status.get("progress", 0) or 0),
                    str(status.get("phase", "")), str(status.get("message", "")),
                )
                if signature != target._last_updater_status_signature:
                    target._last_updater_status_signature = signature
                    target.logger.info(
                        "Updater %s %d%% [%s]: %s",
                        signature[0], signature[1], signature[2] or "-", signature[3] or "-",
                        extra={"error_code": "UPDATER_PROGRESS"},
                    )
                current_state = str(target._updater_state.get("state", "IDLE"))
                updated_at = float(status.get("updated_at", 0) or 0)
                operation_started = float(target._updater_operation_started_at or 0)
                status_version = str(status.get("version", "") or "")
                selected_version = str(target._updater_state.get("available_version", "") or "")
                fresh_for_operation = (
                    operation_started <= 0
                    or updated_at >= operation_started - 1.0
                ) and (not selected_version or not status_version or status_version == selected_version)

                previous = str(status.get("previous", "") or "")
                last_stable = str(status.get("last_stable", "") or "")
                rollback_target = last_stable if self.channel() == "beta" else (previous or last_stable)
                metadata = {
                    "can_rollback": bool(rollback_target),
                    "rollback_target": rollback_target,
                    "helper_error": status.get("error") or {},
                }
                target._set_updater_state(**metadata)

                # Une erreur ancienne du helper ne doit jamais écraser une
                # release que le catalogue vient de rendre disponible.
                accept_state = state in {"DOWNLOADING", "STAGED", "ACTIVATING"}
                if state == "ERROR":
                    accept_state = (
                        current_state in {"DOWNLOADING", "ACTIVATING"}
                        and fresh_for_operation
                    ) or str((status.get("error") or {}).get("code", "")) == "UPDATE_INTERRUPTED"
                if accept_state and (state not in {"DOWNLOADING", "ACTIVATING"} or fresh_for_operation):
                    target._set_updater_state(
                        state=state,
                        available_version=status_version or selected_version,
                        progress=int(status.get("progress", 0) or 0),
                        message=str(status.get("message", "")),
                        detail=str(status.get("detail", "")),
                        phase=str(status.get("phase", "")),
                        can_activate=state == "STAGED",
                        last_manifest=status.get("last_manifest", target._updater_state.get("last_manifest", {})),
                        error=status.get("error") or {},
                        started_at=int(status.get("started_at", 0) or 0),
                        updated_at=int(updated_at),
                    )
            except UpdaterClientError as exc:
                target.logger.debug(
                    "Statut updater indisponible: %s", exc,
                    extra={"error_code": "UPDATER_STATUS_UNAVAILABLE"},
                )
            finally:
                target._updater_poll_running = False

        threading.Thread(target=task, daemon=True, name="UpdaterStatusThread").start()

    def channel(self) -> str:
        channel = str(self.target._config.get("updates", {}).get("channel", "stable"))
        return channel if channel in ReleaseManager.VALID_CHANNELS else "stable"

    def set_channel(self, channel: str) -> bool:
        target = self.target
        if channel not in ReleaseManager.VALID_CHANNELS:
            target.send_notification("ERROR", "Canal de mise à jour inconnu", 3500)
            return False
        target.save_setting("updates.channel", channel)
        target._set_updater_state(channel=channel)
        try:
            ReleaseManager().set_channel(channel)
        except OSError as exc:
            target.logger.warning(
                "Canal non synchronisé avec le gestionnaire système: %s", exc,
                extra={"error_code": "RELEASE_CHANNEL_STATE_WARNING"},
            )
        label = "Bêta" if channel == "beta" else "Stable"
        target.logger.info(
            "Canal de mise à jour sélectionné: %s", channel,
            extra={"error_code": "RELEASE_CHANNEL_CHANGED"},
        )
        target.send_notification("WARNING" if channel == "beta" else "SUCCESS", f"Canal {label} sélectionné", 3500)
        return True

    def check(self, force: bool) -> None:
        target = self.target
        channel = self.channel()
        if target._updater_state.get("state") in {"CHECKING", "DOWNLOADING", "ACTIVATING"}:
            return
        target._set_updater_state(
            state="CHECKING", progress=0, phase="catalog", message="Recherche sur GitHub…",
            detail="Connexion à l'API GitHub et lecture du catalogue des releases",
            started_at=int(time.time()), updated_at=int(time.time()), error={},
        )

        def task() -> None:
            try:
                release = ReleaseCatalog().check(channel, target._clios_version_text)
                if release:
                    target._set_updater_state(
                        state="AVAILABLE", available_version=release["version"], progress=0,
                        message=f"CliOS {release['version']} est disponible", can_activate=False,
                        detail="La release est prête à être téléchargée et vérifiée",
                        phase="available", last_manifest=release, error={},
                    )
                    target.send_notification("INFO", f"Release {release['version']} disponible", 5000)
                else:
                    target._set_updater_state(
                        state="UP_TO_DATE", available_version="", progress=100,
                        message="CliOS est à jour", detail="Aucune release plus récente sur ce canal",
                        phase="complete", can_activate=False, error={},
                    )
                    target.send_notification("SUCCESS", "CliOS est à jour", 3500)
                target.save_setting("updates.last_success_epoch", str(int(time.time())))
            except (CatalogError, OSError, ValueError) as exc:
                code = getattr(exc, "code", "NETWORK")
                target._set_updater_state(
                    state="ERROR", progress=0, message=str(exc), can_activate=False,
                    error={"code": code, "message": str(exc)},
                )
                target.logger.error(
                    "Recherche de release impossible: %s", exc,
                    extra={"error_code": "RELEASE_CHECK_ERROR"},
                )
                target.send_notification("ERROR", f"Recherche impossible: {str(exc)[:70]}", 5000)

        threading.Thread(target=task, daemon=True, name="ReleaseCheckThread").start()

    def stage(self, speed_kmh: float) -> None:
        target = self.target
        version = str(target._updater_state.get("available_version", ""))
        if not version:
            target.send_notification("WARNING", "Aucune mise à jour sélectionnée", 3500)
            return
        target.logger.info(
            "Staging de %s demandé à %.1f km/h", version, speed_kmh,
            extra={"error_code": "UPDATE_STAGE_REQUEST", "speed_kmh": speed_kmh, "version": version},
        )
        target._updater_operation_started_at = time.time()
        target._set_updater_state(
            state="DOWNLOADING", progress=0, phase="request",
            message="Préparation du téléchargement…",
            detail="La demande a été transmise au helper système",
            started_at=int(target._updater_operation_started_at),
            updated_at=int(target._updater_operation_started_at), error={},
        )
        self._run(lambda client: client.stage(version), "STAGED", version)

    def activate(self, speed_kmh: float) -> None:
        target = self.target
        version = str(target._updater_state.get("available_version", ""))
        target.logger.warning(
            "Activation de %s confirmée à %.1f km/h", version, speed_kmh,
            extra={"error_code": "UPDATE_ACTIVATE_CONFIRMED", "speed_kmh": speed_kmh, "version": version},
        )
        target._updater_operation_started_at = time.time()
        target._set_updater_state(state="ACTIVATING", progress=100, message="Activation en cours", error={})
        self._run(lambda client: client.activate(version), "ACTIVATING", version)

    def rollback(self, speed_kmh: float, stable_only: bool) -> None:
        target = self.target
        if not target._updater_state.get("can_rollback", False):
            target.send_notification("INFO", "Aucune version précédente disponible", 4000)
            return
        target.logger.warning(
            "Rollback confirmé à %.1f km/h (stable=%s)", speed_kmh, stable_only,
            extra={"error_code": "UPDATE_ROLLBACK_CONFIRMED", "speed_kmh": speed_kmh, "stable_only": stable_only},
        )
        target._updater_operation_started_at = time.time()
        target._set_updater_state(state="ACTIVATING", progress=100, message="Rollback en cours", error={})
        self._run(lambda client: client.rollback(stable_only), "ACTIVATING", "")

    def _run(self, operation: Callable[[UpdaterClient], object], success_state: str, version: str) -> None:
        target = self.target

        def task() -> None:
            try:
                operation(UpdaterClient(timeout=900))
                target._set_updater_state(
                    state=success_state, available_version=version, progress=100,
                    message="Release préparée" if success_state == "STAGED" else "Redémarrage en cours",
                    can_activate=success_state == "STAGED", error={},
                )
                target._updater_operation_started_at = 0.0
            except UpdaterClientError as exc:
                message = str(exc)
                lowered = message.lower()
                if getattr(exc, "code", "") not in {"", "UPDATER_CLIENT", "UPDATE_ERROR"}:
                    code = exc.code
                elif "sha-256" in lowered or "sha256" in lowered:
                    code = "SHA256"
                elif "espace disque" in lowered or "no space" in lowered:
                    code = "DISK_SPACE"
                elif "self-check" in lowered:
                    code = "SELF_CHECK"
                elif "permission" in lowered or "privil" in lowered or "indisponible" in lowered:
                    code = "PRIVILEGE"
                elif "réseau" in lowered or "github" in lowered:
                    code = "NETWORK"
                else:
                    code = "UPDATE_ERROR"
                target._set_updater_state(
                    state="ERROR", message=message, can_activate=False,
                    error={"code": code, "message": message},
                )
                target.logger.error(message, extra={"error_code": "UPDATER_HELPER_ERROR"})
                target.send_notification("ERROR", message[:90], 6000)
                target._updater_operation_started_at = 0.0

        threading.Thread(target=task, daemon=True, name="UpdaterOperationThread").start()
