#!/usr/bin/env python3
"""Small isolated staging probe run under the production systemd restrictions."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.release_manager import ReleaseManager  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/run/clios-updater-lab"))
    args = parser.parse_args()
    install = args.root / "opt/clios"
    state = args.root / "var/lib/clios"
    source = args.root / "source"
    for path in (source / "frontend", source / "data/config", source / "src", source / "tools"):
        path.mkdir(parents=True, exist_ok=True)
    files = {
        "main.py": "print('systemd probe')\n", "VERSION": "2.0.0\n",
        "frontend/main.qml": "import QtQuick\nItem {}\n", "data/config/profiles.json": "{}\n",
    }
    for relative, content in files.items():
        (source / relative).write_text(content, encoding="utf-8")
    archive = args.root / "probe.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(source, arcname="clios-2.0.0")

    def copy_download(_source, destination):
        Path(destination).write_bytes(archive.read_bytes())

    manager = ReleaseManager(
        str(install), str(state), downloader=copy_download, self_check_user="clios",
    )
    manifest = {
        "version": "2.0.0", "channel": "stable", "archive_url": "fixture://probe",
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    prepared = manager.stage(manifest)
    if prepared.name != "2.0.0" or os.path.lexists(manager.current_link):
        raise RuntimeError("le staging systemd a modifié current ou produit une cible incorrecte")
    print("probe updater systemd: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
