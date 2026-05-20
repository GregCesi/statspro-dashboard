#!/usr/bin/env python3
# scripts/apply_patch.py
# Applique un fichier patch JSON sur data/dashboard.json.
# Champs patchables : data_status, data_quality, validation_note.
# audit_status est refusé silencieusement (réservé à sync_dashboard.py).
# Usage : python3 scripts/apply_patch.py <chemin_patch.json>

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "dashboard.json"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/apply_patch.py <patch.json>")
        sys.exit(1)

    patch_path = Path(sys.argv[1])
    if not patch_path.exists():
        print(f"Fichier introuvable : {patch_path}")
        sys.exit(1)

    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    patches = patch.get("patches", patch) if isinstance(patch, dict) else patch
    if isinstance(patches, dict):
        patches = [{"num": int(k), **v} for k, v in patches.items()]

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    index = {d["num"]: d for d in data}

    applied = 0
    for p in patches:
        num = p.get("num")
        if num not in index:
            print(f"  WARN num={num} introuvable dans dashboard.json — ignoré")
            continue
        row = index[num]
        # audit_status est réservé à sync_dashboard.py — refus silencieux avec warning
        if "audit_status" in p:
            print(f"  WARN num={num} : audit_status ignoré (réservé à sync_dashboard.py)")
        for field in ("data_status", "data_quality", "validation_note"):
            if field in p:
                row[field] = p[field]
        row["last_updated"] = p.get("last_updated") or datetime.now(timezone.utc).isoformat()
        applied += 1

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{applied} lignes mises à jour dans {DATA_PATH}")


if __name__ == "__main__":
    main()
