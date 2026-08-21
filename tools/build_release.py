#!/usr/bin/env python3
"""Construit l'archive CliOS et son manifeste SHA-256."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".idea"}
EXCLUDED_PREFIXES = {
    "data/dash_save", "data/logs", "data/trips", "data/trips_mock",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def release_files(root: Path) -> list[Path]:
    selected = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts):
            continue
        if relative == ".DS_Store" or path.name == ".DS_Store":
            continue
        if any(relative == prefix or relative.startswith(prefix + "/") for prefix in EXCLUDED_PREFIXES):
            continue
        selected.append(path)
    return selected


def build(output: Path, channel: str, base_url: str) -> tuple[Path, Path]:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"clios-{version}-bookworm-arm64.tar.gz"
    files = release_files(ROOT)
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as bundle:
        for path in files:
            relative = path.relative_to(ROOT)
            info = bundle.gettarinfo(str(path), arcname=f"clios-{version}/{relative.as_posix()}")
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = 0
            with open(path, "rb") as stream:
                bundle.addfile(info, stream)
    manifest = {
        "version": version,
        "channel": channel,
        "platform": "raspberry-pi-os-bookworm-arm64",
        "archive_url": base_url.rstrip("/") + "/" + archive.name if base_url else archive.name,
        "archive_sha256": digest(archive),
        "files": {path.relative_to(ROOT).as_posix(): digest(path) for path in files},
    }
    manifest_path = output / f"clios-{version}-{channel}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return archive, manifest_path


def ensure_clean_worktree() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    if result.stdout.strip():
        raise RuntimeError("la construction d'une release exige un arbre Git propre")


def main() -> int:
    parser = argparse.ArgumentParser(description="Construire une release CliOS")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--channel", choices=["stable", "beta"], default="stable")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--allow-dirty", action="store_true", help="réservé aux vérifications locales")
    args = parser.parse_args()
    if not args.allow_dirty:
        ensure_clean_worktree()
    archive, manifest = build(args.output, args.channel, args.base_url)
    print(archive)
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
