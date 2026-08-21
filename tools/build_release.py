#!/usr/bin/env python3
"""Construit l'archive CliOS et son manifeste SHA-256."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.release_contract import ReleaseContractError, channel_for_version, validate_manifest  # noqa: E402
from src.release_platform import PLATFORMS_BY_TARGET, get_target_platform  # noqa: E402
from tools.verify_wheelhouse import locked_names, wheel_names  # noqa: E402

EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".idea", ".pytest_cache", ".portfolio", "dist", "wheelhouses"}
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
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True,
    ).stdout.decode("utf-8").split("\0")
    candidates = [root / relative for relative in tracked if relative]
    selected = []
    for path in sorted(set(candidates)):
        relative = path.relative_to(root).as_posix()
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts):
            continue
        if relative == ".DS_Store" or path.name == ".DS_Store":
            continue
        if any(relative == prefix or relative.startswith(prefix + "/") for prefix in EXCLUDED_PREFIXES):
            continue
        selected.append(path)
    return selected


def build(
    output: Path,
    channel: str,
    base_url: str,
    *,
    target: str = "bookworm-arm64",
    require_wheelhouse: bool = True,
) -> tuple[Path, Path, Path]:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    release_platform = get_target_platform(target)
    expected_channel = channel_for_version(version)
    if channel != expected_channel:
        raise ReleaseContractError(
            f"VERSION {version} impose le canal {expected_channel}, pas {channel}"
        )
    if require_wheelhouse:
        locked = locked_names(ROOT / f"requirements-{target}.lock")
        wheels = wheel_names(ROOT / "wheelhouses" / target)
        if wheels != locked:
            missing = ", ".join(sorted(locked - wheels)) or "aucune"
            extra = ", ".join(sorted(wheels - locked)) or "aucune"
            raise RuntimeError(f"wheelhouse incomplet (absentes: {missing}; non verrouillées: {extra})")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"clios-{version}-{target}.tar.gz"
    files = release_files(ROOT)
    entries = [(path, path.relative_to(ROOT).as_posix()) for path in files]
    entries.extend(
        (path, f"wheels/{path.name}")
        for path in sorted((ROOT / "wheelhouses" / target).glob("*.whl"))
    )
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as bundle:
        for path, relative in entries:
            info = bundle.gettarinfo(str(path), arcname=f"clios-{version}/{relative}")
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = 0
            with open(path, "rb") as stream:
                bundle.addfile(info, stream)
    manifest = {
        "schema_version": 1,
        "version": version,
        "channel": channel,
        "platform": release_platform.identifier,
        "archive_url": base_url.rstrip("/") + "/" + archive.name if base_url else archive.name,
        "archive_sha256": digest(archive),
        "files": {relative: digest(path) for path, relative in entries},
    }
    validate_manifest(manifest, require_https=bool(base_url))
    manifest_path = output / f"clios-{version}-{target}-{channel}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sums_path = output / f"SHA256SUMS-{target}"
    sums_path.write_text(
        "".join(f"{digest(path)}  {path.name}\n" for path in (archive, manifest_path)),
        encoding="utf-8",
    )
    return archive, manifest_path, sums_path


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
    parser.add_argument("--target", choices=sorted(PLATFORMS_BY_TARGET), default="bookworm-arm64")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--allow-dirty", action="store_true", help="réservé aux vérifications locales")
    parser.add_argument("--skip-wheelhouse-check", action="store_true", help="réservé aux vérifications locales sans publication")
    args = parser.parse_args()
    if not args.allow_dirty:
        ensure_clean_worktree()
    if args.skip_wheelhouse_check and not args.allow_dirty:
        parser.error("--skip-wheelhouse-check exige --allow-dirty")
    archive, manifest, sums = build(
        args.output, args.channel, args.base_url, target=args.target,
        require_wheelhouse=not args.skip_wheelhouse_check,
    )
    print(archive)
    print(manifest)
    print(sums)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
