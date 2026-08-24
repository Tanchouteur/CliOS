#!/usr/bin/env python3
"""Create tiny signed A/B/C releases for the updater qualification lab."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path


PLATFORM = "raspberry-pi-os-bookworm-arm64"
TARGET = "bookworm-arm64"
RELEASES = (
    ("A", "2.0.0", "stable", False),
    ("B", "2.0.1-rc.13", "beta", False),
    ("C", "2.0.1-rc.14", "beta", True),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_release(output: Path, label: str, version: str, channel: str, broken: bool) -> tuple[Path, Path]:
    with tempfile.TemporaryDirectory(prefix=f"clios-fixture-{label}-") as directory:
        root = Path(directory) / f"clios-{version}"
        (root / "frontend").mkdir(parents=True)
        (root / "data/config").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "tools").mkdir()
        (root / "main.py").write_text(f"print('fixture {label}')\n", encoding="utf-8")
        (root / "VERSION").write_text(version + "\n", encoding="utf-8")
        (root / "data/config/profiles.json").write_text("{}\n", encoding="utf-8")
        if not broken:
            (root / "frontend/main.qml").write_text("import QtQuick\nItem {}\n", encoding="utf-8")
        archive = output / f"clios-{version}-{TARGET}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(root, arcname=root.name)
        manifested = ("main.py", "VERSION", "data/config/profiles.json")
        if not broken:
            manifested += ("frontend/main.qml",)
        manifest = {
            "schema_version": 1,
            "version": version,
            "channel": channel,
            "platform": PLATFORM,
            "archive_url": f"https://fixtures.invalid/{archive.name}",
            "archive_sha256": sha256(archive),
            "files": {name: sha256(root / name) for name in manifested},
        }
        manifest_path = output / f"clios-{version}-{TARGET}-{channel}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return archive, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère les fixtures signées A/B/C de l'updater")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for release in RELEASES:
        artifacts.extend(create_release(args.output, *release))
    sums = args.output / "SHA256SUMS"
    sums.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in sorted(artifacts)),
        encoding="utf-8",
    )
    private_key = args.output / "fixture-private.pem"
    public_key = args.output / "fixture-public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private_key)], check=True)
    subprocess.run(["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)], check=True)
    subprocess.run([
        "openssl", "pkeyutl", "-sign", "-inkey", str(private_key), "-rawin",
        "-in", str(sums), "-out", str(args.output / "SHA256SUMS.sig"),
    ], check=True)
    keyring = {"schema_version": 1, "keys": [{"id": "updater-lab", "public_key": public_key.read_text()}]}
    (args.output / "release-keys.json").write_text(json.dumps(keyring, indent=2) + "\n", encoding="utf-8")
    private_key.unlink()
    print(f"fixtures A/B/C créées dans {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
