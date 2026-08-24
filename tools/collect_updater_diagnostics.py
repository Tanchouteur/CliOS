#!/usr/bin/env python3
"""Collect a read-only CliOS updater report on a Raspberry Pi."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.updater_diagnostics import collect_updater_diagnostics  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostic updater CliOS (lecture seule)")
    parser.add_argument("--install-root", default="/opt/clios")
    parser.add_argument("--state-root", default="/var/lib/clios")
    parser.add_argument("--service", default="clios-updater.service")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = collect_updater_diagnostics(args.install_root, args.state_root, args.service)
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
