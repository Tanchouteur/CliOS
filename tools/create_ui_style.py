"""Crée un paquet de style CliOS à partir du gabarit officiel."""

import argparse
import json
import re
import shutil
from pathlib import Path


STYLE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def main():
    parser = argparse.ArgumentParser(description="Créer un nouveau style CliOS")
    parser.add_argument("style_id", help="Identifiant dossier, ex. racing_blue")
    parser.add_argument("label", help="Libellé affiché, ex. Racing Blue")
    args = parser.parse_args()

    if not STYLE_ID_PATTERN.fullmatch(args.style_id):
        parser.error("style_id doit utiliser uniquement a-z, 0-9 et _, et commencer par une lettre")

    project_root = Path(__file__).resolve().parent.parent
    styles_dir = project_root / "frontend" / "styles"
    target_root = project_root / "frontend" / "dev_styles"
    target_root.mkdir(parents=True, exist_ok=True)
    template_dir = styles_dir / "_template"
    target_dir = target_root / args.style_id
    if target_dir.exists():
        parser.error(f"le style existe déjà: {target_dir}")

    shutil.copytree(template_dir, target_dir)
    manifest_path = target_dir / "style.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["id"] = args.style_id
    manifest["label"] = args.label
    manifest_path.write_text(json.dumps(manifest, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    print(target_dir)


if __name__ == "__main__":
    main()
