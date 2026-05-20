#!/usr/bin/env python3
# scripts/migrate_add_ids.py
# Ajoute un champ `id: "CAT-NNN"` à chaque entrée de data/dashboard.json.
# Idempotent : ne touche pas aux id existants conformes au préfixe de la catégorie.
# Usage : python3 scripts/migrate_add_ids.py

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "dashboard.json"

# Mapping catégorie → préfixe
CATEGORY_PREFIX = {
    "Roster & Disponibilité": "ROST",
    "Résultats & Matchs": "RES",
    "Classement & Standings": "CLAS",
    "Rythme & Pace": "PACE",
    "Confrontations directes (H2H)": "H2H",
    "Fatigue & Voyage": "FAT",
    "Style de jeu & Coach": "STYL",
    "Défense individuelle": "DEF",
    "Stats Joueur": "STAT",
    "Live": "LIVE",
    "Arbitres": "ARB",
    "Paris & Cotes": "BET",
}


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    print(f"Lecture : {DATA_PATH} ({len(data)} lignes)")

    # Compteur séquentiel par catégorie
    counters: dict[str, int] = {}
    changed = 0

    for row in data:
        cat = row["categorie"]
        prefix = CATEGORY_PREFIX.get(cat)
        if prefix is None:
            print(f"  ERREUR : catégorie inconnue '{cat}' (num={row['num']})")
            raise SystemExit(1)

        counters[prefix] = counters.get(prefix, 0) + 1
        expected_id = f"{prefix}-{counters[prefix]:03d}"

        existing_id = row.get("id")
        if existing_id and existing_id.startswith(prefix + "-"):
            # ID existant conforme au préfixe — ne pas écraser
            continue

        row["id"] = expected_id
        changed += 1

    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"  {changed} id ajoutés/corrigés, {len(data) - changed} déjà conformes")
    print(f"Écrit : {DATA_PATH}")


if __name__ == "__main__":
    main()
