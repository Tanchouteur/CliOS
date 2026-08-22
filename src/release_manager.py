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
import re
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
    SIGNATURE_BOOTSTRAP_VERSION = SemVer.parse("2.0.1-rc.4")

    def __init__(self, install_root: str = "/opt/clios", state_root: str = "/var/lib/clios",
                 downloader=None, progress_callback=None, self_check_user: str | None = None,
                 platform_id: str | None = None, trusted_keys_path: str | None = None):
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
        packaged_keys = Path(__file__).resolve().parent.parent / "installation/etc/clios/release-keys.json"
        system_keys = Path("/etc/clios/release-keys.json")
        self.trusted_keys_path = Path(trusted_keys_path) if trusted_keys_path else (
            system_keys if system_keys.exists() else packaged_keys
        )

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
        manifest_location = None
        if isinstance(manifest_source, dict):
            manifest = dict(manifest_source)
            manifest_location = manifest.pop("_manifest_url", None)
        else:
            manifest_location = str(manifest_source)
            manifest = self._read_json(manifest_location)
        version = self._validate_manifest(manifest, strict=strict)
        signed_hashes = None
        if strict and SemVer.parse(version) > self.SIGNATURE_BOOTSTRAP_VERSION:
            signed_hashes = self._verify_signed_metadata(manifest, manifest_location)
        target = self.releases_dir / version
        if target.exists():
            raise ReleaseError(f"release déjà préparée: {version}")
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        self.state_root.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix=f"clios-{version}-", dir=str(self.releases_dir)))
        # tempfile impose 0700. Le self-check est volontairement exécuté avec
        # l'utilisateur système ``clios`` : le groupe du service doit donc
        # pouvoir traverser le staging sans pour autant le rendre public.
        work.chmod(0o750)
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
            if signed_hashes is not None:
                archive_name = Path(str(manifest["archive_url"])).name
                if self.sha256(archive_part) != signed_hashes[archive_name]:
                    raise ReleaseError("hash signé de l'archive incorrect")
            unpacked = work / "unpacked"
            unpacked.mkdir()
            self._safe_extract(archive_part, unpacked)
            release_root = self._single_root(unpacked)
            self._verify_files(release_root, manifest.get("files", {}))
            self._progress("DOWNLOADING", 100, "Installation de l'environnement")
            self._install_environment(release_root, str(manifest.get("platform", "")))
            self.self_check(release_root, run_as=self.self_check_user)
            self._precompile_runtime(release_root)
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

    def _verify_signed_metadata(self, manifest: dict, manifest_location: str | None) -> dict[str, str]:
        """Verify SHA256SUMS before trusting a future manifest or archive."""
        version = str(manifest["version"])
        platform = str(manifest["platform"]).removeprefix("raspberry-pi-os-")
        manifest_name = f"clios-{version}-{platform}-{manifest['channel']}.json"
        archive_name = Path(str(manifest["archive_url"])).name
        base = str(manifest_location or manifest["archive_url"]).rsplit("/", 1)[0]
        manifest_ref = str(manifest_location or f"{base}/{manifest_name}")
        sums_ref = f"{base}/SHA256SUMS"
        signature_ref = f"{base}/SHA256SUMS.sig"

        with tempfile.TemporaryDirectory(prefix="clios-signature-") as temp_dir:
            temp = Path(temp_dir)
            sums_path, signature_path, manifest_path = temp / "SHA256SUMS", temp / "SHA256SUMS.sig", temp / manifest_name
            self._download(sums_ref, sums_path)
            self._download(signature_ref, signature_path)
            self._download(manifest_ref, manifest_path)
            self._verify_ed25519(sums_path, signature_path)
            signed = self._parse_sha256sums(sums_path)
            for required in (manifest_name, archive_name):
                if required not in signed:
                    raise ReleaseError(f"artefact absent du manifeste signé: {required}")
            if self.sha256(manifest_path) != signed[manifest_name]:
                raise ReleaseError("hash signé du manifeste incorrect")
            try:
                downloaded = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
                current = validate_manifest(manifest)
            except (OSError, json.JSONDecodeError, ReleaseContractError) as exc:
                raise ReleaseError(f"manifeste signé invalide: {exc}") from exc
            if downloaded != current:
                raise ReleaseError("le manifeste résolu diffère du manifeste signé")
            if signed[archive_name] != str(manifest["archive_sha256"]).lower():
                raise ReleaseError("hash d'archive contradictoire dans le manifeste signé")
            return signed

    def _download(self, source: str, destination: Path) -> None:
        if self._default_downloader:
            self.downloader(source, str(destination))
        else:
            self.downloader(source, str(destination))

    def _verify_ed25519(self, sums_path: Path, signature_path: Path) -> None:
        try:
            keyring = json.loads(self.trusted_keys_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReleaseError(f"trousseau de publication indisponible: {exc}") from exc
        keys = keyring.get("keys") if isinstance(keyring, dict) else None
        if keyring.get("schema_version") != 1 or not isinstance(keys, list) or not keys:
            raise ReleaseError("trousseau de publication invalide")
        for index, entry in enumerate(keys):
            if not isinstance(entry, dict) or not isinstance(entry.get("public_key"), str):
                continue
            key_path = sums_path.parent / f"release-key-{index}.pem"
            key_path.write_text(entry["public_key"], encoding="utf-8")
            try:
                result = subprocess.run(
                    ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(key_path),
                     "-rawin", "-in", str(sums_path), "-sigfile", str(signature_path)],
                    capture_output=True, text=True, timeout=10, check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise ReleaseError(f"vérification Ed25519 impossible: {exc}") from exc
            if result.returncode == 0:
                return
        raise ReleaseError("signature Ed25519 de SHA256SUMS invalide")

    @staticmethod
    def _parse_sha256sums(path: Path) -> dict[str, str]:
        entries = {}
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.fullmatch(r"([0-9a-fA-F]{64})  ([A-Za-z0-9][A-Za-z0-9_.-]*)", line)
            if not match:
                raise ReleaseError(f"SHA256SUMS invalide à la ligne {line_number}")
            name = match.group(2)
            if name in entries:
                raise ReleaseError(f"artefact dupliqué dans SHA256SUMS: {name}")
            entries[name] = match.group(1).lower()
        if not entries:
            raise ReleaseError("SHA256SUMS vide")
        return entries

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
    def _precompile_runtime(release_root: Path) -> None:
        """Persist target-version bytecode so the first cockpit boot stays light."""
        python = release_root / ".venv/bin/python3"
        if not python.exists():
            return
        result = subprocess.run(
            [str(python), "-m", "compileall", "-q", "main.py", "src", "tools"],
            cwd=release_root, capture_output=True, text=True, timeout=120,
        )
        if result.returncode:
            raise ReleaseError("précompilation Python: " + (result.stderr or result.stdout))

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

        # Ne pas passer extra_groups=[] ici. Python appellerait setgroups(2),
        # opération refusée par certains profils systemd durcis (EPERM), alors
        # que changer l'UID/GID primaire suffit pour ce self-check en lecture.
        return {"user": account.pw_uid, "group": account.pw_gid}

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
