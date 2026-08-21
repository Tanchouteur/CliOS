#!/usr/bin/env python3
"""Render the single authoritative CliOS systemd unit template."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "installation/systemd/clios.service.in"
USER_RE = re.compile(r"^[a-z_][a-z0-9_-]*[$]?$", re.IGNORECASE)


def render_service(user: str, uid: int, install_root: str = "/opt/clios") -> str:
    if not USER_RE.fullmatch(user):
        raise ValueError("utilisateur systemd invalide")
    if uid < 0:
        raise ValueError("UID invalide")
    root = os.path.normpath(install_root)
    if not os.path.isabs(root) or root == "/" or ".." in Path(root).parts:
        raise ValueError("racine d'installation invalide")
    return (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("@USER@", user)
        .replace("@UID@", str(uid))
        .replace("@INSTALL_ROOT@", root)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--uid", required=True, type=int)
    parser.add_argument("--install-root", default="/opt/clios")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.write_text(render_service(args.user, args.uid, args.install_root), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
