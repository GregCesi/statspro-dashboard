#!/usr/bin/env python3
# scripts/migrate_split_status.py
# Éclate poc_status en audit_status + data_status.
# DRY-RUN par défaut : liste les cas ambigus, ne modifie rien.
# Usage : python3 scripts/migrate_split_status.py [--apply]

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "dashboard.json"

# --- Table de migration ---
# Cas clairs : poc_status → (audit_status, data_status)
CLEAR_MAPPING = {
    "validated_slow": ("validated_slow", "live"),
    "dégradé":        ("validated", "degraded"),
    "non_testé":      (None, "not_implemented"),
    "out_of_scope":   (None, "deferred_v2"),
}

# Valeurs admises (vérification de cohérence)
VALID_AUDIT = {None, "validated", "validated_slow", "bugged_parsing", "unreliable_upstream", "blocked_no_source"}
VALID_DATA = {"live", "degraded", "not_implemented", "deferred_v2", "blocked_no_source"}


def classify_bloque(row):
    """Tente de classifier un 'bloqué'. Retourne (audit, data) ou None si ambigu."""
    notes = (row.get("notes") or "").lower()
    endpoint = (row.get("endpoint") or "").lower()
    cout = (row.get("cout") or "").lower()

    # Heuristique : si le coût est freemium/payant, ou notes mentionnent "paid", "plan",
    # "payant", "$" → blocked_no_source (pas de source gratuite)
    paid_signals = ["paid", "plan", "payant", "$", "9.99", "scrambled", "free trial"]
    if cout in ("freemium", "payant") or any(s in notes for s in paid_signals):
        return "blocked_no_source", "blocked_no_source", "auto: source payante détectée"

    # Signal structurel : fournisseur BDL injuries / scraping non-BBRef → pas de source
    # backend disponible en gratuit (scraping NBA Injury Report hors scope V1,
    # BDL injuries paywallé). Plus robuste que le mot-clé "$".
    fournisseur = (row.get("fournisseur") or "").lower()
    structural_signals = ["balldontlie", "scraping"]
    if any(s in fournisseur for s in structural_signals) or any(s in endpoint for s in structural_signals):
        return "blocked_no_source", "blocked_no_source", "auto: source non implémentée (scraping/BDL paywallé)"

    # Sinon → ambigu, besoin d'arbitrage
    return None


def classify_valide(row):
    """Tente de classifier un 'validé'. Retourne (audit, data) ou None si ambigu."""
    endpoint = (row.get("endpoint") or "").lower()

    # /combined/ avec dégradation BDL → validated + degraded
    if "/combined/" in endpoint:
        return "validated", "degraded", "auto: endpoint /combined/ détecté"

    # Cas standard → validated + live
    return "validated", "live", None


def main():
    apply_mode = "--apply" in sys.argv
    mode_label = "APPLY" if apply_mode else "DRY-RUN"
    print(f"=== migrate_split_status.py [{mode_label}] ===\n")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    print(f"Lecture : {DATA_PATH} ({len(data)} lignes)\n")

    # Vérifier que poc_status existe encore
    has_poc = sum(1 for d in data if "poc_status" in d)
    if has_poc == 0:
        print("Aucun champ poc_status trouvé — migration déjà effectuée ?")
        return

    migrations = []   # (row, audit_status, data_status, note)
    ambiguous = []     # (row, reason)

    for row in data:
        poc = row.get("poc_status")
        if poc is None:
            continue

        row_id = row.get("id", f"num={row['num']}")

        if poc in CLEAR_MAPPING:
            audit, data_s = CLEAR_MAPPING[poc]
            migrations.append((row, audit, data_s, None))

        elif poc == "bloqué":
            result = classify_bloque(row)
            if result is None:
                ambiguous.append((row, f"'bloqué' ambigu : source payante ou bug parsing ?"))
            else:
                audit, data_s, note = result
                migrations.append((row, audit, data_s, note))

        elif poc == "validé":
            result = classify_valide(row)
            if result is None:
                ambiguous.append((row, f"'validé' ambigu : live ou degraded ?"))
            else:
                audit, data_s, note = result
                migrations.append((row, audit, data_s, note))

        else:
            ambiguous.append((row, f"poc_status inconnu : '{poc}'"))

    # --- Rapport ---
    print(f"Migrations claires : {len(migrations)}")
    print(f"Cas ambigus :        {len(ambiguous)}\n")

    # Résumé par type
    from collections import Counter
    summary = Counter()
    for _, audit, data_s, _ in migrations:
        summary[(audit, data_s)] += 1
    print("Résumé des migrations :")
    for (a, d), count in sorted(summary.items(), key=lambda x: -x[1]):
        print(f"  {str(a):20s} + {d:20s} : {count:3d} lignes")
    print()

    # Détail auto-classifiés avec note
    auto_classified = [(r, a, d, n) for r, a, d, n in migrations if n]
    if auto_classified:
        print(f"Auto-classifiés avec heuristique ({len(auto_classified)}) :")
        for row, audit, data_s, note in auto_classified:
            row_id = row.get("id", f"num={row['num']}")
            print(f"  {row_id:8s} | {row['poc_status']:15s} → {str(audit):20s} + {data_s:20s} | {note}")
        print()

    # Cas ambigus
    if ambiguous:
        print(f"CAS AMBIGUS À ARBITRER ({len(ambiguous)}) :")
        for row, reason in ambiguous:
            row_id = row.get("id", f"num={row['num']}")
            print(f"  {row_id:8s} num={row['num']:3d} | {row['donnee'][:50]}")
            print(f"           poc_status: {row['poc_status']}")
            print(f"           endpoint:   {row.get('endpoint', '')[:70]}")
            print(f"           raison:     {reason}")
            print()

        if len(ambiguous) > 5:
            print(f"⚠️  {len(ambiguous)} cas ambigus (> 5) — STOP, arbitrage requis avant --apply.")

        if apply_mode:
            print("ERREUR : --apply impossible avec des cas ambigus non résolus.")
            raise SystemExit(1)
    else:
        print("Aucun cas ambigu — migration 100% automatique possible.\n")

    # --- Application ---
    if not apply_mode:
        print(f"[DRY-RUN] Aucune modification. Relancer avec --apply pour écrire.")
        return

    print("Application de la migration...")
    for row, audit, data_s, _ in migrations:
        row["audit_status"] = audit
        row["data_status"] = data_s
        del row["poc_status"]

    # Vérification de cohérence
    for row in data:
        if "poc_status" in row:
            print(f"  ERREUR : poc_status résiduel sur {row.get('id', row['num'])}")
            raise SystemExit(1)
        if row.get("audit_status") not in VALID_AUDIT:
            print(f"  ERREUR : audit_status invalide '{row['audit_status']}' sur {row.get('id')}")
            raise SystemExit(1)
        if row.get("data_status") not in VALID_DATA:
            print(f"  ERREUR : data_status invalide '{row['data_status']}' sur {row.get('id')}")
            raise SystemExit(1)

    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\n{len(migrations)} lignes migrées. poc_status supprimé.")
    print(f"Écrit : {DATA_PATH}")


if __name__ == "__main__":
    main()
