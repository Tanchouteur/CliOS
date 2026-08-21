"""Gestion atomique des releases CliOS avec staging et rollback N-1."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path


class ReleaseError(RuntimeError):
    pass


class ReleaseManager:
    VALID_CHANNELS = {"stable", "beta"}

    def __init__(self, install_root: str = "/opt/clios", state_root: str = "/var/lib/clios",
                 downloader=None):
        self.install_root = Path(install_root)
        self.releases_dir = self.install_root / "releases"
        self.current_link = self.install_root / "current"
        self.state_root = Path(state_root)
        self.state_path = self.state_root / "release-state.json"
        self.downloader = downloader or urllib.request.urlretrieve

    @staticmethod
    def _read_json(path_or_url: str) -> dict:
        if path_or_url.startswith(("https://", "http://")):
            with urllib.request.urlopen(path_or_url, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        with open(path_or_url, encoding="utf-8") as stream:
            return json.load(stream)

    def get_channel(self) -> str:
        """Retourne le canal persistant, avec repli sûr sur stable."""
        channel = self._load_state().get("channel", "stable")
        return channel if channel in self.VALID_CHANNELS else "stable"

    def set_channel(self, channel: str) -> str:
        """Enregistre le canal utilisé par les prochaines recherches de release."""
        if channel not in self.VALID_CHANNELS:
            raise ReleaseError("canal inconnu")
        state = self._load_state()
        state["channel"] = channel
        self._write_json_atomic(self.state_path, state)
        return channel

    def check(self, feed: str, channel: str | None = None) -> dict | None:
        channel = channel or self.get_channel()
        if channel not in self.VALID_CHANNELS:
            raise ReleaseError("canal inconnu")
        payload = self._read_json(feed)
        releases = payload.get("releases", [])
        candidates = [item for item in releases if item.get("channel", "stable") == channel]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: self._version_tuple(item.get("version", "0.0.0")))[-1]

    def stage(self, manifest_source: str) -> Path:
        manifest = self._read_json(manifest_source)
        version = self._validate_manifest(manifest)
        target = self.releases_dir / version
        if target.exists():
            raise ReleaseError(f"release déjà préparée: {version}")
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        self.state_root.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix=f"clios-{version}-", dir=str(self.releases_dir)))
        archive_part = work / "release.tar.part"
        try:
            self.downloader(manifest["archive_url"], str(archive_part))
            if self.sha256(archive_part) != manifest["archive_sha256"].lower():
                raise ReleaseError("SHA-256 de l'archive incorrect")
            unpacked = work / "unpacked"
            unpacked.mkdir()
            self._safe_extract(archive_part, unpacked)
            release_root = self._single_root(unpacked)
            self._verify_files(release_root, manifest.get("files", {}))
            self._install_environment(release_root)
            self.self_check(release_root)
            os.replace(release_root, target)
            self._write_json_atomic(target / "release-manifest.json", manifest)
            return target
        except Exception:
            shutil.rmtree(work, ignore_errors=True)
            raise
        finally:
            if work.exists():
                shutil.rmtree(work, ignore_errors=True)

    def activate(self, version: str) -> Path:
        target = self.releases_dir / version
        if not target.is_dir():
            raise ReleaseError(f"release non préparée: {version}")
        previous = self.current_link.resolve() if self.current_link.is_symlink() else None
        self._atomic_symlink(target, self.current_link)
        state = self._load_state()
        last_stable = state.get("last_stable")
        if self._channel(target) == "stable":
            last_stable = version
        elif not last_stable and previous and self._channel(previous) == "stable":
            # L'installation initiale peut précéder release-state.json.
            last_stable = previous.name
        state.update({
            "active": version,
            "previous": previous.name if previous else state.get("active"),
            "pending_health": version,
            "last_stable": last_stable,
        })
        self._write_json_atomic(self.state_path, state)
        self.cleanup()
        return target

    def rollback(self, stable_only: bool = False) -> Path:
        state = self._load_state()
        previous = state.get("last_stable") if stable_only else state.get("previous") or state.get("last_stable")
        if not previous:
            message = "aucune release stable connue" if stable_only else "aucune release précédente"
            raise ReleaseError(message)
        target = self.releases_dir / previous
        if not target.is_dir():
            raise ReleaseError(f"release précédente absente: {previous}")
        active = state.get("active")
        self._atomic_symlink(target, self.current_link)
        state.update({"active": previous, "previous": active, "pending_health": None})
        self._write_json_atomic(self.state_path, state)
        return target

    def mark_healthy(self, version: str) -> None:
        state = self._load_state()
        if state.get("pending_health") == version:
            state["pending_health"] = None
            state["healthy"] = version
            self._write_json_atomic(self.state_path, state)

    def cleanup(self, keep: int = 2) -> list[str]:
        state = self._load_state()
        protected = {state.get("active"), state.get("previous"), state.get("last_stable")}
        releases = sorted((p for p in self.releases_dir.glob("*") if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
        kept = 0
        removed = []
        for release in releases:
            if release.name in protected or kept < keep:
                kept += 1
                continue
            shutil.rmtree(release)
            removed.append(release.name)
        return removed

    @staticmethod
    def self_check(release_root: Path) -> None:
        required = ("main.py", "VERSION", "frontend/main.qml", "data/config/profiles.json")
        missing = [name for name in required if not (release_root / name).exists()]
        if missing:
            raise ReleaseError("self-check: fichiers manquants: " + ", ".join(missing))
        result = subprocess.run(
            [os.environ.get("PYTHON", "python3"), "-m", "compileall", "-q", "main.py", "src", "tools"],
            cwd=release_root, capture_output=True, text=True, timeout=60,
        )
        if result.returncode:
            raise ReleaseError("self-check Python: " + (result.stderr or result.stdout))
        validator = release_root / "tools/validate_data.py"
        if validator.exists():
            result = subprocess.run(
                [str(release_root / ".venv/bin/python3") if (release_root / ".venv/bin/python3").exists() else os.environ.get("PYTHON", "python3"),
                 str(validator), "--all"],
                cwd=release_root, capture_output=True, text=True, timeout=60,
            )
            if result.returncode:
                raise ReleaseError("self-check données: " + (result.stderr or result.stdout))
        smoke = release_root / "tools/qml_smoke.py"
        if smoke.exists() and (release_root / ".venv/bin/python3").exists():
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
            result = subprocess.run(
                [str(release_root / ".venv/bin/python3"), str(smoke)], cwd=release_root,
                env=env, capture_output=True, text=True, timeout=120,
            )
            if result.returncode:
                raise ReleaseError("self-check QML: " + (result.stderr or result.stdout))

    @staticmethod
    def _install_environment(release_root: Path) -> None:
        lock = release_root / "requirements-bookworm-arm64.lock"
        wheels = release_root / "wheels"
        if not lock.exists():
            return
        python = shutil.which("python3.11") or shutil.which("python3")
        if not python:
            raise ReleaseError("Python 3.11 indisponible")
        subprocess.run([python, "-m", "venv", str(release_root / ".venv")], check=True, timeout=90)
        command = [str(release_root / ".venv/bin/pip"), "install"]
        if wheels.is_dir():
            command.extend(["--no-index", "--find-links", str(wheels)])
        command.extend(["-r", str(lock)])
        result = subprocess.run(command, cwd=release_root, capture_output=True, text=True, timeout=600)
        if result.returncode:
            raise ReleaseError("installation de l'environnement: " + (result.stderr or result.stdout))

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _safe_extract(archive: Path, destination: Path) -> None:
        with tarfile.open(archive, "r:*") as bundle:
            root = destination.resolve()
            for member in bundle.getmembers():
                member_path = (destination / member.name).resolve()
                if root != member_path and root not in member_path.parents:
                    raise ReleaseError("archive contenant un chemin non sûr")
            bundle.extractall(destination, filter="data")

    @staticmethod
    def _single_root(unpacked: Path) -> Path:
        entries = [entry for entry in unpacked.iterdir() if entry.name != "__MACOSX"]
        if len(entries) == 1 and entries[0].is_dir():
            return entries[0]
        return unpacked

    @staticmethod
    def _verify_files(root: Path, files: dict) -> None:
        for relative, expected in files.items():
            candidate = (root / relative).resolve()
            if root.resolve() not in candidate.parents or not candidate.is_file():
                raise ReleaseError(f"fichier manifesté absent ou non sûr: {relative}")
            if ReleaseManager.sha256(candidate) != str(expected).lower():
                raise ReleaseError(f"SHA-256 incorrect: {relative}")

    @staticmethod
    def _validate_manifest(manifest: dict) -> str:
        for key in ("version", "channel", "archive_url", "archive_sha256"):
            if not manifest.get(key):
                raise ReleaseError(f"manifeste incomplet: {key}")
        ReleaseManager._version_tuple(manifest["version"])
        if manifest["channel"] not in ReleaseManager.VALID_CHANNELS:
            raise ReleaseError("canal invalide")
        if len(manifest["archive_sha256"]) != 64:
            raise ReleaseError("SHA-256 invalide")
        return manifest["version"]

    @staticmethod
    def _version_tuple(value: str) -> tuple[int, int, int]:
        try:
            parts = tuple(int(part) for part in str(value).split("."))
        except ValueError as exc:
            raise ReleaseError(f"version invalide: {value}") from exc
        if len(parts) != 3:
            raise ReleaseError(f"version invalide: {value}")
        return parts

    def _channel(self, release: Path) -> str:
        try:
            return self._read_json(str(release / "release-manifest.json")).get("channel", "stable")
        except (OSError, json.JSONDecodeError):
            return "stable"

    def _load_state(self) -> dict:
        try:
            return self._read_json(str(self.state_path))
        except (OSError, json.JSONDecodeError):
            return {"channel": "stable"}

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        with open(temporary, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    @staticmethod
    def _atomic_symlink(target: Path, link: Path) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        temporary = link.with_name(link.name + ".next")
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        temporary.symlink_to(target)
        os.replace(temporary, link)
