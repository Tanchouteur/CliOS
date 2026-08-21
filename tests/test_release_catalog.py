import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

from src.release_catalog import CatalogNetworkError, CatalogRateLimitError, CatalogResponseError, ReleaseCatalog


class Response:
    def __init__(self, payload, status=200, etag='"catalog-v1"'):
        self.data = json.dumps(payload).encode("utf-8")
        self.status = status
        self.headers = {"ETag": etag}

    def read(self):
        return self.data

    def getcode(self):
        return self.status


class FixtureOpener:
    def __init__(self, releases, manifests):
        self.releases = releases
        self.manifests = manifests
        self.requests = []

    def __call__(self, request, timeout=0):
        self.requests.append(request)
        if "/releases?" in request.full_url:
            return Response(self.releases)
        return Response(self.manifests[request.full_url])


def manifest(version, channel):
    archive = f"https://fixtures/Tanchouteur/CliOS/releases/download/v{version}/clios-{version}-bookworm-arm64.tar.gz"
    return {
        "schema_version": 1, "version": version, "channel": channel,
        "platform": "raspberry-pi-os-bookworm-arm64", "archive_url": archive,
        "archive_sha256": "a" * 64, "files": {"main.py": "b" * 64},
    }


def release(version, prerelease=False, draft=False):
    channel = "beta" if prerelease else "stable"
    base = f"https://fixtures/Tanchouteur/CliOS/releases/download/v{version}"
    return {
        "tag_name": f"v{version}", "draft": draft, "prerelease": prerelease,
        "html_url": base, "published_at": "2026-01-01T00:00:00Z",
        "assets": [
            {"name": f"clios-{version}-{channel}.json", "browser_download_url": f"{base}/clios-{version}-{channel}.json"},
            {"name": f"clios-{version}-bookworm-arm64.tar.gz", "browser_download_url": f"{base}/clios-{version}-bookworm-arm64.tar.gz"},
        ],
    }


class ReleaseCatalogTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cache = str(Path(self.temp.name) / "cache.json")

    def tearDown(self):
        self.temp.cleanup()

    def catalog(self, releases):
        manifests = {}
        for item in releases:
            version = item["tag_name"].removeprefix("v")
            channel = "beta" if item["prerelease"] else "stable"
            manifests[item["assets"][0]["browser_download_url"]] = manifest(version, channel)
        opener = FixtureOpener(releases, manifests)
        return ReleaseCatalog(cache_path=self.cache, opener=opener, api_base="https://fixtures"), opener

    def test_stable_ignores_drafts_and_prereleases(self):
        catalog, _ = self.catalog([
            release("2.0.1"), release("2.0.2-rc.1", prerelease=True), release("9.0.0", draft=True),
        ])
        self.assertEqual(catalog.check("stable", "2.0.0")["version"], "2.0.1")

    def test_beta_chooses_newest_semver_and_never_proposes_current(self):
        catalog, _ = self.catalog([release("2.0.1"), release("2.1.0-rc.1", prerelease=True)])
        self.assertEqual(catalog.check("beta", "2.0.0")["version"], "2.1.0-rc.1")
        self.assertIsNone(catalog.check("beta", "2.1.0-rc.1"))

    def test_etag_cache_is_used_offline(self):
        catalog, opener = self.catalog([release("2.0.1")])
        self.assertEqual(catalog.check("stable", "2.0.0")["version"], "2.0.1")
        self.assertEqual(catalog.check("stable", "2.0.0")["version"], "2.0.1")
        release_requests = [request for request in opener.requests if "/releases?" in request.full_url]
        self.assertEqual(release_requests[-1].get_header("If-none-match"), '"catalog-v1"')

        def offline(_request, timeout=0):
            raise urllib.error.URLError("offline")

        cached = ReleaseCatalog(cache_path=self.cache, opener=offline, api_base="https://fixtures")
        # Le catalogue est disponible depuis le cache; le manifeste ne l'est pas.
        with self.assertRaises(CatalogNetworkError):
            cached.check("stable", "2.0.0")

    def test_rate_limit_and_invalid_github_payload_are_explicit(self):
        def limited(request, timeout=0):
            raise urllib.error.HTTPError(request.full_url, 403, "limited", {"X-RateLimit-Reset": "123"}, io.BytesIO())

        catalog = ReleaseCatalog(cache_path=self.cache, opener=limited, api_base="https://fixtures")
        with self.assertRaises(CatalogRateLimitError):
            catalog.check("stable", "2.0.0")
        self.assertEqual(catalog.last_error["code"], "RATE_LIMIT")

        invalid = ReleaseCatalog(cache_path=self.cache + "-invalid", opener=lambda request, timeout=0: Response({}), api_base="https://fixtures")
        with self.assertRaises(CatalogResponseError):
            invalid.check("stable", "2.0.0")


if __name__ == "__main__":
    unittest.main()
