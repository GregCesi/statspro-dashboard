#!/usr/bin/env python3
# scripts/migrate.py
# Extrait le const DATA du HTML, applique les patches BDL, initialise les
# champs statut V2 (audit_status, data_status, data_quality), écrit data/dashboard.json.
# Usage : python3 scripts/migrate.py

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HTML_PATH = ROOT / "dashboard_statspro.html"
OUTPUT_PATH = ROOT / "data" / "dashboard.json"

# Import de la table de patch (même dossier)
sys.path.insert(0, str(Path(__file__).parent))
from bdl_patch_table import INJURY_BLOCKED, FOURNISSEUR_PATCHES


def extract_data(html_path: Path) -> list:
    text = html_path.read_text(encoding="utf-8")
    m = re.search(r"const DATA\s*=\s*(\[.*?\]);", text, re.DOTALL)
    if not m:
        raise ValueError("const DATA introuvable dans le HTML")
    return json.loads(m.group(1))


def apply_patches(data: list) -> list:
    patched = []
    for row in data:
        num = row["num"]

        # Patch fournisseur
        if num in FOURNISSEUR_PATCHES:
            p = FOURNISSEUR_PATCHES[num]
            if row["fournisseur"] != p["fournisseur_old"]:
                print(f"  WARN ligne {num}: fournisseur attendu {p['fournisseur_old']!r}, "
                      f"trouvé {row['fournisseur']!r} — patch appliqué quand même")
            row["fournisseur"] = p["fournisseur_new"]

        # Champs statut V2 — initialisation
        if num in INJURY_BLOCKED:
            row["audit_status"] = "blocked_no_source"
            row["data_status"] = "blocked_no_source"
        else:
            row["audit_status"] = None
            row["data_status"] = "not_implemented"
        row["data_quality"] = "unknown"
        row["validation_note"] = ""
        row["last_updated"] = None

        patched.append(row)

    return patched


def main():
    print(f"Lecture : {HTML_PATH}")
    data = extract_data(HTML_PATH)
    print(f"  {len(data)} lignes extraites")

    print("Application des patches...")
    data = apply_patches(data)

    injury_count = sum(1 for r in data if r["audit_status"] == "blocked_no_source")
    patch_count = len(FOURNISSEUR_PATCHES)
    print(f"  {patch_count} fournisseurs patchés, {injury_count} lignes blocked_no_source")

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Écrit : {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
