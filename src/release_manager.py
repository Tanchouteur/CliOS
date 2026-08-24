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


class ReleaseDependencyError(ReleaseError):
    """A runtime required by a release is not installed or packaged."""

    code = "DEPENDENCY_MISSING"


class ReleaseCommandError(ReleaseError):
    """A bounded internal command failed with machine-readable diagnostics."""

    def __init__(self, context: str, command: list[str], *, returncode: int | None = None,
                 stderr: str = "", code: str = "SUBPROCESS_FAILED"):
        raw_detail = stderr.strip()
        detail = raw_detail[:2048] + ("…" if len(raw_detail) > 2048 else "")
        detail = detail or (f"code retour {returncode}" if returncode is not None else "échec de lancement")
        super().__init__(f"{context}: {detail}")
        self.code = code
        self.command = list(command)
        self.returncode = returncode
        self.stderr = stderr


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
        self.downloader = downloader or self._download_url
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

    @staticmethod
    def _download_url(source: str, destination: str, reporthook=None):
        """Télécharge avec un timeout d'inactivité borné et une progression fiable."""
        request = urllib.request.Request(source, headers={"User-Agent": "CliOS-Updater/2"})
        with urllib.request.urlopen(request, timeout=30) as response, open(destination, "wb") as stream:
            total_size = int(response.headers.get("Content-Length", 0) or 0)
            block_size = 256 * 1024
            blocks = 0
            if reporthook:
                reporthook(0, block_size, total_size)
            while True:
                block = response.read(block_size)
                if not block:
                    break
                stream.write(block)
                blocks += 1
                if reporthook:
                    reporthook(blocks, block_size, total_size)
        return destination, response.headers

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
        self._progress("DOWNLOADING", 5, "Validation du manifeste de release", phase="manifest")
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
            self._progress(
                "DOWNLOADING", 7, "Vérification des métadonnées signées",
                phase="signature", indeterminate=True,
            )
            signed_hashes = self._verify_signed_metadata(manifest, manifest_location)
        target = self.releases_dir / version
        if target.exists():
            if self._prepared_release_is_valid(target, manifest):
                self._progress(
                    "STAGED", 100, f"Release {version} déjà préparée et revalidée",
                    phase="complete", reused=True,
                )
                return target
            raise ReleaseError(f"release déjà préparée mais invalide: {version}")
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        self.state_root.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix=f"clios-{version}-", dir=str(self.releases_dir)))
        # tempfile impose 0700. Le self-check est volontairement exécuté avec
        # l'utilisateur système ``clios`` : le groupe du service doit donc
        # pouvoir traverser le staging sans pour autant le rendre public.
        work.chmod(0o750)
        archive_part = work / "release.tar.part"
        try:
            self._progress(
                "DOWNLOADING", 10, "Téléchargement de l'archive (connexion)",
                phase="archive", indeterminate=True, bytes_received=0,
                bytes_total=int(manifest.get("archive_size", 0) or 0),
            )
            required = int(manifest.get("archive_size", 0) or 0)
            if required:
                free = shutil.disk_usage(self.releases_dir).free
                if free < required * 2:
                    raise ReleaseError("espace disque insuffisant pour le staging")
            if self._default_downloader:
                def reporthook(blocks: int, block_size: int, total_size: int) -> None:
                    received = blocks * block_size
                    if total_size > 0:
                        received = min(received, total_size)
                        archive_pct = min(100, int(received * 100 / total_size))
                        overall_pct = 10 + int(archive_pct * 0.5)
                        self._progress(
                            "DOWNLOADING", overall_pct,
                            f"Téléchargement de l'archive — {archive_pct}%",
                            phase="archive", indeterminate=False,
                            bytes_received=received, bytes_total=total_size,
                        )
                    else:
                        self._progress(
                            "DOWNLOADING", 10, "Téléchargement de l'archive",
                            phase="archive", indeterminate=True,
                            bytes_received=received, bytes_total=0,
                        )
                self.downloader(manifest["archive_url"], str(archive_part), reporthook=reporthook)
            else:
                self.downloader(manifest["archive_url"], str(archive_part))
            archive_size = archive_part.stat().st_size
            self._progress(
                "DOWNLOADING", 60, "Archive téléchargée", phase="archive",
                bytes_received=archive_size, bytes_total=archive_size, indeterminate=False,
            )
            if shutil.disk_usage(self.releases_dir).free < archive_part.stat().st_size * 2:
                raise ReleaseError("espace disque insuffisant pour extraire la release")
            self._progress(
                "DOWNLOADING", 64, "Vérification SHA-256 de l'archive",
                phase="hash", indeterminate=True,
            )
            archive_sha256 = self.sha256(archive_part)
            if archive_sha256 != manifest["archive_sha256"].lower():
                raise ReleaseError("SHA-256 de l'archive incorrect")
            if signed_hashes is not None:
                self._progress(
                    "DOWNLOADING", 67, "Comparaison avec les sommes signées",
                    phase="signature", indeterminate=True,
                )
                archive_name = Path(str(manifest["archive_url"])).name
                if archive_sha256 != signed_hashes[archive_name]:
                    raise ReleaseError("hash signé de l'archive incorrect")
            self._progress(
                "DOWNLOADING", 70, "Extraction sécurisée de la release",
                phase="extract", indeterminate=True,
            )
            unpacked = work / "unpacked"
            unpacked.mkdir()
            self._safe_extract(archive_part, unpacked)
            release_root = self._single_root(unpacked)
            self._progress(
                "DOWNLOADING", 75, "Vérification des fichiers manifestés",
                phase="hash", indeterminate=True,
            )
            self._verify_files(release_root, manifest.get("files", {}))
            self._progress(
                "DOWNLOADING", 80, "Création de l'environnement Python",
                phase="environment", indeterminate=True,
            )
            self._install_environment(release_root, str(manifest.get("platform", "")))
            self._progress(
                "DOWNLOADING", 94, "Self-check Python, données et interface QML",
                phase="self_check", indeterminate=True,
            )
            self.self_check(release_root, run_as=self.self_check_user)
            self._progress(
                "DOWNLOADING", 98, "Précompilation du runtime Python",
                phase="precompile", indeterminate=True,
            )
            self._precompile_runtime(release_root)
            os.replace(release_root, target)
            self._write_json_atomic(target / "release-manifest.json", manifest)
            self._progress(
                "STAGED", 100, f"Release {version} préparée",
                phase="complete", indeterminate=False,
            )
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
            command = [
                "openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(key_path),
                "-rawin", "-in", str(sums_path), "-sigfile", str(signature_path),
            ]
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=10, check=False,
                )
            except FileNotFoundError as exc:
                raise ReleaseDependencyError("openssl absent pour la vérification Ed25519") from exc
            except subprocess.TimeoutExpired as exc:
                raise ReleaseCommandError(
                    "vérification Ed25519 expirée", command, stderr=str(exc), code="SUBPROCESS_TIMEOUT",
                ) from exc
            except OSError:
                raise
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

    def _prepared_release_is_valid(self, target: Path, expected_manifest: dict) -> bool:
        """Accept a previous staging only when its immutable contract still matches."""
        try:
            stored = self._read_json(str(target / "release-manifest.json"))
            for field in ("version", "channel", "platform", "archive_sha256"):
                if field in expected_manifest and stored.get(field) != expected_manifest.get(field):
                    return False
            self._verify_files(target, expected_manifest.get("files", {}))
            required = ("main.py", "VERSION", "frontend/main.qml", "data/config/profiles.json")
            return all((target / name).is_file() for name in required)
        except (OSError, json.JSONDecodeError, ReleaseError, TypeError):
            return False

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
        ReleaseManager._run_checked(
            [python, "-m", "compileall", "-q", "main.py", "src", "tools"],
            "self-check Python", cwd=release_root, env=check_env, timeout=60, **run_options,
        )
        if release_python.exists():
            ReleaseManager._run_checked(
                [python, "-c", "import PySide6, numpy, psutil, can, serial, pyudev, bleak, sounddevice, pyo, aifc, audioop"],
                "self-check dépendances", cwd=release_root, env=check_env, timeout=60,
                **run_options,
            )
        validator = release_root / "tools/validate_data.py"
        if validator.exists():
            ReleaseManager._run_checked(
                [python, str(validator), "--all"],
                "self-check données", cwd=release_root, env=check_env, timeout=60,
                **run_options,
            )
        smoke = release_root / "tools/qml_smoke.py"
        if smoke.exists() and (release_root / ".venv/bin/python3").exists():
            env = dict(check_env, QT_QPA_PLATFORM="offscreen")
            ReleaseManager._run_checked(
                [python, str(smoke)], "self-check QML", cwd=release_root,
                env=env, timeout=120,
                **run_options,
            )

    @staticmethod
    def _precompile_runtime(release_root: Path) -> None:
        """Persist target-version bytecode so the first cockpit boot stays light."""
        python = release_root / ".venv/bin/python3"
        if not python.exists():
            return
        ReleaseManager._run_checked(
            [str(python), "-m", "compileall", "-q", "main.py", "src", "tools"],
            "précompilation Python", cwd=release_root, timeout=120,
        )

    def _install_environment(self, release_root: Path, platform_id: str = "") -> None:
        if not platform_id:
            return
        try:
            release_platform = get_release_platform(platform_id)
        except ReleasePlatformError as exc:
            raise ReleaseError(str(exc)) from exc
        lock = release_root / f"requirements-{release_platform.target}.lock"
        wheels = release_root / "wheels"
        if not lock.exists():
            raise ReleaseDependencyError(f"lock absent pour {release_platform.target}")
        python = shutil.which(f"python{release_platform.python_minor}")
        if not python:
            raise ReleaseDependencyError(f"Python {release_platform.python_minor} indisponible")
        self._run_checked(
            [python, "-m", "venv", str(release_root / ".venv")],
            "création de l'environnement Python", timeout=90,
        )
        pip = str(release_root / ".venv/bin/pip")
        wheel_files = sorted(wheels.glob("*.whl")) if wheels.is_dir() else []
        if wheel_files:
            self._progress(
                "DOWNLOADING", 84, f"Installation du wheelhouse ({len(wheel_files)} paquets)",
                phase="environment", indeterminate=True,
            )
            # Les wheels ont déjà été contrôlées par le manifeste de release.
            self._run_checked(
                [pip, "install", "--no-index", "--no-deps", *map(str, wheel_files)],
                "installation du wheelhouse", cwd=release_root, timeout=600,
            )
        # Les paquets déjà présents sont conservés. Une éventuelle dépendance
        # absente peut venir de PyPI uniquement si son artefact correspond à un
        # hash du lock.
        self._progress(
            "DOWNLOADING", 88, "Vérification et installation des dépendances verrouillées",
            phase="environment", indeterminate=True,
        )
        command = [pip, "install", "--require-hashes", "-r", str(lock)]
        self._run_checked(command, "installation de l'environnement", cwd=release_root, timeout=600)

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
                # Python 3.11 (Bookworm) has no ``filter='data'``. Releases do
                # not need links or special files, so enforce the portable,
                # stricter subset explicitly on every supported Python.
                if not (member.isdir() or member.isfile()):
                    raise ReleaseError(f"archive contenant un type de fichier interdit: {member.name}")
            for member in bundle.getmembers():
                options = {"filter": "fully_trusted"} if hasattr(tarfile, "fully_trusted_filter") else {}
                bundle.extract(member, destination, set_attrs=False, **options)
                extracted = destination / member.name
                mode = member.mode & 0o777
                if member.isdir():
                    extracted.chmod(mode or 0o755)
                else:
                    extracted.chmod(mode or 0o644)

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

    def _progress(self, state: str, progress: int, message: str, **details) -> None:
        if self.progress_callback:
            self.progress_callback(state, progress, message, **details)

    @staticmethod
    def _run_checked(command: list[str], context: str, **options):
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=False, **options,
            )
        except FileNotFoundError as exc:
            raise ReleaseDependencyError(f"commande absente pour {context}: {command[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            stderr = str(exc.stderr or exc.stdout or exc)
            raise ReleaseCommandError(
                f"{context} expiré", command, stderr=stderr, code="SUBPROCESS_TIMEOUT",
            ) from exc
        if result.returncode:
            raise ReleaseCommandError(
                context, command, returncode=result.returncode,
                stderr=str(result.stderr or result.stdout or ""),
            )
        return result

    @staticmethod
    def _run_as_options(username: str | None) -> dict:
        if not username or os.geteuid() != 0:
            return {}
        import pwd
        try:
            account = pwd.getpwnam(username)
        except KeyError as exc:
            raise ReleaseError(f"utilisateur de self-check absent: {username}") from exc

        # Le service systemd tourne déjà avec Group=clios. Dans ce cas, ne pas
        # redemander setgid(2): certains noyaux/profils durcis le refusent avec
        # EPERM malgré une transition vers le même GID. setuid(2) suffit.
        options = {"user": account.pw_uid}
        if os.getgid() != account.pw_gid:
            options["group"] = account.pw_gid
        return options

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
