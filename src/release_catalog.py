"""Catalogue officiel fondé exclusivement sur GitHub Releases."""

from __future__ import annotations

import json
import os
import stat
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from src.release_contract import ReleaseContractError, SemVer, validate_manifest


DEFAULT_REPOSITORY = "Tanchouteur/CliOS"
DEFAULT_CONFIG = "/etc/clios/updater.json"
DEFAULT_CACHE = "/var/lib/clios/catalog-cache.json"


class CatalogError(RuntimeError):
    code = "CATALOG_ERROR"


class CatalogConfigurationError(CatalogError):
    code = "CONFIGURATION"


class CatalogNetworkError(CatalogError):
    code = "NETWORK"


class CatalogRateLimitError(CatalogError):
    code = "RATE_LIMIT"


class CatalogResponseError(CatalogError):
    code = "INVALID_RESPONSE"


class ReleaseCatalog:
    """Résout la meilleure release du dépôt autorisé.

    ``check`` retourne un manifeste normalisé ou ``None``. Les erreurs sont
    séparées par les sous-classes de :class:`CatalogError` et ``last_error``.
    """

    VALID_CHANNELS = {"stable", "beta"}

    def __init__(
        self,
        config_path: str = DEFAULT_CONFIG,
        cache_path: str = DEFAULT_CACHE,
        *,
        opener=None,
        repository: str | None = None,
        enforce_root_config: bool = True,
        api_base: str = "https://api.github.com",
    ):
        self.config_path = Path(config_path)
        self.cache_path = Path(cache_path)
        self.opener = opener or urllib.request.urlopen
        self.api_base = api_base.rstrip("/")
        self.last_error: dict | None = None
        config = self._load_config(enforce_root_config)
        self.repository = repository or str(config.get("repository", DEFAULT_REPOSITORY))
        self._validate_repository(self.repository)

    def check(self, channel: str, current_version: str) -> dict | None:
        self.last_error = None
        if channel not in self.VALID_CHANNELS:
            raise CatalogConfigurationError("canal inconnu")
        try:
            current = SemVer.parse(current_version)
            releases = self._fetch_releases()
            candidates: list[tuple[SemVer, dict, dict]] = []
            for item in releases:
                if not isinstance(item, dict) or item.get("draft"):
                    continue
                try:
                    version = SemVer.parse(str(item.get("tag_name", "")).removeprefix("v"))
                except ReleaseContractError:
                    continue
                github_prerelease = bool(item.get("prerelease"))
                if github_prerelease != bool(version.prerelease):
                    continue
                if channel == "stable" and version.prerelease:
                    continue
                if version <= current:
                    continue
                manifest_asset = self._manifest_asset(item, str(version))
                if manifest_asset:
                    candidates.append((version, item, manifest_asset))
            if not candidates:
                return None
            version, release, asset = max(candidates, key=lambda entry: entry[0])
            self._validate_asset_url(str(asset["browser_download_url"]))
            manifest = self._fetch_json(str(asset["browser_download_url"]), use_cache=False)
            normalized = validate_manifest(manifest)
            if normalized["version"] != str(version):
                raise CatalogResponseError("tag et version du manifeste différents")
            self._validate_asset_url(normalized["archive_url"])
            archive_name = f"clios-{version}-bookworm-arm64.tar.gz"
            release_assets = {
                str(candidate.get("name")): candidate
                for candidate in release.get("assets", []) if isinstance(candidate, dict)
            }
            archive_asset = release_assets.get(archive_name)
            if not archive_asset or archive_asset.get("browser_download_url") != normalized["archive_url"]:
                raise CatalogResponseError("archive manifestée absente de la release GitHub")
            normalized["release_url"] = str(release.get("html_url", ""))
            normalized["published_at"] = str(release.get("published_at", ""))
            normalized["manifest_url"] = str(asset["browser_download_url"])
            return normalized
        except CatalogError as exc:
            self.last_error = {"code": exc.code, "message": str(exc)}
            raise
        except ReleaseContractError as exc:
            wrapped = CatalogResponseError(str(exc))
            self.last_error = {"code": wrapped.code, "message": str(wrapped)}
            raise wrapped from exc

    def find(self, version: str) -> dict:
        """Résout une version exacte sans accepter d'URL venant du client."""
        self.last_error = None
        try:
            target = SemVer.parse(version)
            releases = self._fetch_releases()
            for item in releases:
                if str(item.get("tag_name", "")).removeprefix("v") != version or item.get("draft"):
                    continue
                if bool(item.get("prerelease")) != bool(target.prerelease):
                    break
                asset = self._manifest_asset(item, version)
                if not asset:
                    break
                self._validate_asset_url(str(asset["browser_download_url"]))
                manifest = validate_manifest(self._fetch_json(str(asset["browser_download_url"]), use_cache=False))
                if manifest["version"] != version:
                    break
                self._validate_asset_url(manifest["archive_url"])
                archive_name = f"clios-{version}-bookworm-arm64.tar.gz"
                archive = next((
                    entry for entry in item.get("assets", [])
                    if isinstance(entry, dict) and entry.get("name") == archive_name
                ), None)
                if not archive or archive.get("browser_download_url") != manifest["archive_url"]:
                    break
                return manifest
            raise CatalogResponseError(f"release introuvable: {version}")
        except CatalogError as exc:
            self.last_error = {"code": exc.code, "message": str(exc)}
            raise
        except ReleaseContractError as exc:
            wrapped = CatalogResponseError(str(exc))
            self.last_error = {"code": wrapped.code, "message": str(wrapped)}
            raise wrapped from exc

    def _load_config(self, enforce_root: bool) -> dict:
        if not self.config_path.exists():
            return {"repository": DEFAULT_REPOSITORY}
        try:
            info = self.config_path.stat()
            if enforce_root and (info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
                raise CatalogConfigurationError("updater.json doit appartenir à root et ne pas être modifiable par le groupe")
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogConfigurationError(f"configuration updater invalide: {exc}") from exc
        if not isinstance(payload, dict) or set(payload) - {"schema_version", "repository"}:
            raise CatalogConfigurationError("configuration updater contient des clés interdites")
        if payload.get("schema_version", 1) != 1:
            raise CatalogConfigurationError("schéma updater non pris en charge")
        return payload

    @staticmethod
    def _validate_repository(repository: str) -> None:
        parts = repository.split("/")
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
        if len(parts) != 2 or any(not part or not set(part) <= allowed for part in parts):
            raise CatalogConfigurationError("dépôt GitHub invalide")

    def _fetch_releases(self) -> list:
        url = f"{self.api_base}/repos/{self.repository}/releases?per_page=100"
        payload = self._fetch_json(url, use_cache=True)
        if not isinstance(payload, list):
            raise CatalogResponseError("réponse GitHub Releases invalide")
        return payload

    def _fetch_json(self, url: str, *, use_cache: bool) -> object:
        cache = self._read_cache() if use_cache else {}
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "CliOS-Updater/2"}
        if use_cache and cache.get("url") == url and cache.get("etag"):
            headers["If-None-Match"] = str(cache["etag"])
        request = urllib.request.Request(url, headers=headers)
        try:
            response = self.opener(request, timeout=15)
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            if status == 304 and use_cache and "payload" in cache:
                return cache["payload"]
            raw = response.read()
            payload = json.loads(raw.decode("utf-8"))
            if use_cache:
                self._write_cache({
                    "url": url,
                    "etag": response.headers.get("ETag", ""),
                    "checked_at": int(time.time()),
                    "payload": payload,
                })
            return payload
        except urllib.error.HTTPError as exc:
            if exc.code == 304 and use_cache and "payload" in cache:
                return cache["payload"]
            if exc.code in {403, 429}:
                reset = exc.headers.get("X-RateLimit-Reset", "inconnu") if exc.headers else "inconnu"
                raise CatalogRateLimitError(f"limite API GitHub atteinte (reset {reset})") from exc
            raise CatalogNetworkError(f"GitHub HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # Un cache précédemment validé permet la consultation hors-ligne.
            if use_cache and "payload" in cache:
                return cache["payload"]
            raise CatalogNetworkError(f"GitHub inaccessible: {exc}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CatalogResponseError("réponse GitHub non JSON") from exc

    @staticmethod
    def _manifest_asset(release: dict, version: str) -> dict | None:
        channel = "beta" if SemVer.parse(version).prerelease else "stable"
        expected = f"clios-{version}-{channel}.json"
        for asset in release.get("assets", []):
            if isinstance(asset, dict) and asset.get("name") == expected and asset.get("browser_download_url"):
                return asset
        return None

    def _validate_asset_url(self, url: str) -> None:
        parsed = urlparse(url)
        if self.api_base == "https://api.github.com":
            prefix = f"/{self.repository}/releases/download/"
            if parsed.scheme != "https" or parsed.hostname != "github.com" or not parsed.path.startswith(prefix):
                raise CatalogResponseError("URL d'asset hors du dépôt GitHub autorisé")

    def _read_cache(self) -> dict:
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_cache(self, payload: dict) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, self.cache_path)
        except OSError:
            # Le catalogue reste utilisable dans une session non privilégiée.
            pass
