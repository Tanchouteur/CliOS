#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.release_manager import ReleaseManager, ReleaseError  # noqa: E402
from src.release_catalog import CatalogError, ReleaseCatalog  # noqa: E402
from src.updater_client import UpdaterClient, UpdaterClientError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Gestionnaire de releases CliOS")
    parser.add_argument("--install-root", default="/opt/clios")
    parser.add_argument("--state-root", default="/var/lib/clios")
    sub = parser.add_subparsers(dest="operation", required=True)
    check = sub.add_parser("check")
    check.add_argument("--current-version", default=(ROOT / "VERSION").read_text(encoding="utf-8").strip())
    check.add_argument("--channel", choices=["stable", "beta"], help="surcharge ponctuelle du canal enregistré")
    channel = sub.add_parser("channel")
    channel.add_argument("value", nargs="?", choices=["stable", "beta"])
    stage = sub.add_parser("stage")
    stage.add_argument("version")
    activate = sub.add_parser("activate")
    activate.add_argument("version")
    rollback = sub.add_parser("rollback")
    rollback.add_argument("--stable", action="store_true", help="revenir à la dernière release stable")
    args = parser.parse_args()
    manager = ReleaseManager(args.install_root, args.state_root)
    try:
        if args.operation == "check":
            result = ReleaseCatalog().check(args.channel or manager.get_channel(), args.current_version)
        elif args.operation == "channel":
            result = manager.set_channel(args.value) if args.value else manager.get_channel()
        elif args.operation == "stage":
            result = UpdaterClient(timeout=900).stage(args.version)
        elif args.operation == "activate":
            result = UpdaterClient(timeout=60).activate(args.version)
        else:
            result = UpdaterClient(timeout=60).rollback(stable_only=args.stable)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ReleaseError, CatalogError, UpdaterClientError) as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
