#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.release_manager import ReleaseManager, ReleaseError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Gestionnaire de releases CliOS")
    parser.add_argument("--install-root", default="/opt/clios")
    parser.add_argument("--state-root", default="/var/lib/clios")
    sub = parser.add_subparsers(dest="operation", required=True)
    check = sub.add_parser("check"); check.add_argument("feed"); check.add_argument("--channel", choices=["stable", "beta"], default="stable")
    stage = sub.add_parser("stage"); stage.add_argument("manifest")
    activate = sub.add_parser("activate"); activate.add_argument("version")
    sub.add_parser("rollback")
    args = parser.parse_args()
    manager = ReleaseManager(args.install_root, args.state_root)
    try:
        if args.operation == "check": result = manager.check(args.feed, args.channel)
        elif args.operation == "stage": result = str(manager.stage(args.manifest))
        elif args.operation == "activate": result = str(manager.activate(args.version))
        else: result = str(manager.rollback())
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ReleaseError as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
