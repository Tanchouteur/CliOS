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

from src.release_contract import ReleaseContractError, SemVer, validate_manifest
from src.release_platform import (
    ReleasePlatformError,
    detect_release_platform,
    get_release_platform,
)


class ReleaseError(RuntimeError):
    pass


class ReleaseManager:
    VALID_CHANNELS = {"stable", "beta"}

    def __init__(self, install_root: str = "/opt/clios", state_root: str = "/var/lib/clios",
                 downloader=None, progress_callback=None, self_check_user: str | None = None,
                 platform_id: str | None = None):
        self.install_root = Path(install_root)
        self.releases_dir = self.install_root / "releases"
        self.current_link = self.install_root / "current"
        self.state_root = Path(state_root)
        self.state_path = self.state_root / "release-state.json"
        self._default_downloader = downloader is None
        self.downloader = downloader or urllib.request.urlretrieve
        self.progress_callback = progress_callback
        self.self_check_user = self_check_user
        self.platform = get_release_platform(platform_id) if platform_id else None

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

    def stage(self, manifest_source: str | dict, *, strict: bool = False) -> Path:
        manifest = manifest_source if isinstance(manifest_source, dict) else self._read_json(manifest_source)
        version = self._validate_manifest(manifest, strict=strict)
        target = self.releases_dir / version
        if target.exists():
            raise ReleaseError(f"release déjà préparée: {version}")
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        self.state_root.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix=f"clios-{version}-", dir=str(self.releases_dir)))
        archive_part = work / "release.tar.part"
        try:
            self._progress("DOWNLOADING", 0, "Téléchargement de l'archive")
            required = int(manifest.get("archive_size", 0) or 0)
            if required:
                free = shutil.disk_usage(self.releases_dir).free
                if free < required * 2:
                    raise ReleaseError("espace disque insuffisant pour le staging")
            if self._default_downloader:
                def reporthook(blocks: int, block_size: int, total_size: int) -> None:
                    if total_size > 0:
                        self._progress("DOWNLOADING", min(99, int(blocks * block_size * 100 / total_size)), "Téléchargement de l'archive")
                self.downloader(manifest["archive_url"], str(archive_part), reporthook=reporthook)
            else:
                self.downloader(manifest["archive_url"], str(archive_part))
            self._progress("DOWNLOADING", 100, "Archive téléchargée")
            if shutil.disk_usage(self.releases_dir).free < archive_part.stat().st_size * 2:
                raise ReleaseError("espace disque insuffisant pour extraire la release")
            if self.sha256(archive_part) != manifest["archive_sha256"].lower():
                raise ReleaseError("SHA-256 de l'archive incorrect")
            unpacked = work / "unpacked"
            unpacked.mkdir()
            self._safe_extract(archive_part, unpacked)
            release_root = self._single_root(unpacked)
            self._verify_files(release_root, manifest.get("files", {}))
            self._progress("DOWNLOADING", 100, "Installation de l'environnement")
            self._install_environment(release_root, str(manifest.get("platform", "")))
            self.self_check(release_root, run_as=self.self_check_user)
            os.replace(release_root, target)
            self._write_json_atomic(target / "release-manifest.json", manifest)
            self._progress("STAGED", 100, f"Release {version} préparée")
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
    def self_check(release_root: Path, run_as: str | None = None) -> None:
        required = ("main.py", "VERSION", "frontend/main.qml", "data/config/profiles.json")
        missing = [name for name in required if not (release_root / name).exists()]
        if missing:
            raise ReleaseError("self-check: fichiers manquants: " + ", ".join(missing))
        run_options = ReleaseManager._run_as_options(run_as)
        pycache = tempfile.mkdtemp(prefix="clios-selfcheck-pyc-")
        os.chmod(pycache, 0o777)
        check_env = dict(os.environ, PYTHONPYCACHEPREFIX=pycache)
        release_python = release_root / ".venv/bin/python3"
        python = str(release_python) if release_python.exists() else os.environ.get("PYTHON", "python3")
        result = subprocess.run(
            [python, "-m", "compileall", "-q", "main.py", "src", "tools"],
            cwd=release_root, env=check_env, capture_output=True, text=True, timeout=60, **run_options,
        )
        if result.returncode:
            raise ReleaseError("self-check Python: " + (result.stderr or result.stdout))
        if release_python.exists():
            result = subprocess.run(
                [python, "-c", "import PySide6, numpy, psutil, can, serial, pyudev, bleak, sounddevice, pyo, aifc, audioop"],
                cwd=release_root, env=check_env, capture_output=True, text=True, timeout=60,
                **run_options,
            )
            if result.returncode:
                raise ReleaseError("self-check dépendances: " + (result.stderr or result.stdout))
        validator = release_root / "tools/validate_data.py"
        if validator.exists():
            result = subprocess.run(
                [python, str(validator), "--all"],
                cwd=release_root, env=check_env, capture_output=True, text=True, timeout=60,
                **run_options,
            )
            if result.returncode:
                raise ReleaseError("self-check données: " + (result.stderr or result.stdout))
        smoke = release_root / "tools/qml_smoke.py"
        if smoke.exists() and (release_root / ".venv/bin/python3").exists():
            env = dict(check_env, QT_QPA_PLATFORM="offscreen")
            result = subprocess.run(
                [python, str(smoke)], cwd=release_root,
                env=env, capture_output=True, text=True, timeout=120,
                **run_options,
            )
            if result.returncode:
                raise ReleaseError("self-check QML: " + (result.stderr or result.stdout))

    @staticmethod
    def _install_environment(release_root: Path, platform_id: str = "") -> None:
        if not platform_id:
            return
        try:
            release_platform = get_release_platform(platform_id)
        except ReleasePlatformError as exc:
            raise ReleaseError(str(exc)) from exc
        lock = release_root / f"requirements-{release_platform.target}.lock"
        wheels = release_root / "wheels"
        if not lock.exists():
            raise ReleaseError(f"lock absent pour {release_platform.target}")
        python = shutil.which(f"python{release_platform.python_minor}")
        if not python:
            raise ReleaseError(f"Python {release_platform.python_minor} indisponible")
        subprocess.run([python, "-m", "venv", str(release_root / ".venv")], check=True, timeout=90)
        pip = str(release_root / ".venv/bin/pip")
        wheel_files = sorted(wheels.glob("*.whl")) if wheels.is_dir() else []
        if wheel_files:
            # Les wheels ont déjà été contrôlées par le manifeste de release.
            result = subprocess.run(
                [pip, "install", "--no-index", "--no-deps", *map(str, wheel_files)],
                cwd=release_root, capture_output=True, text=True, timeout=600,
            )
            if result.returncode:
                raise ReleaseError("installation du wheelhouse: " + (result.stderr or result.stdout))
        # Les paquets déjà présents sont conservés. Une éventuelle dépendance
        # absente peut venir de PyPI uniquement si son artefact correspond à un
        # hash du lock.
        command = [pip, "install", "--require-hashes", "-r", str(lock)]
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

    def _validate_manifest(self, manifest: dict, *, strict: bool = False) -> str:
        if strict or "schema_version" in manifest:
            try:
                normalized = validate_manifest(manifest, require_https=strict)
                expected = self.platform or detect_release_platform()
                if normalized["platform"] != expected.identifier:
                    raise ReleaseError(
                        f"release {normalized['platform']} incompatible avec {expected.identifier}"
                    )
                return normalized["version"]
            except (ReleaseContractError, ReleasePlatformError) as exc:
                raise ReleaseError(str(exc)) from exc
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
    def _version_tuple(value: str) -> SemVer:
        try:
            return SemVer.parse(value)
        except ReleaseContractError as exc:
            raise ReleaseError(f"version invalide: {value}") from exc

    def _progress(self, state: str, progress: int, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(state, progress, message)

    @staticmethod
    def _run_as_options(username: str | None) -> dict:
        if not username or os.geteuid() != 0:
            return {}
        import pwd
        try:
            account = pwd.getpwnam(username)
        except KeyError as exc:
            raise ReleaseError(f"utilisateur de self-check absent: {username}") from exc

        return {"user": account.pw_uid, "group": account.pw_gid, "extra_groups": []}

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
