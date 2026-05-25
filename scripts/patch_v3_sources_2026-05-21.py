#!/usr/bin/env python3
"""Patch V3 sources : remplace BDL par sources gratuites identifiées (6 lignes).
Champs touchés : fournisseur, endpoint, api_source, cout, notes, audit_status.
Aucun autre champ modifié."""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "dashboard.json"

PATCHES = {
    "ROST-001": {
        "audit_status": None,
        "fournisseur": "NBA officiel (PDF)",
        "endpoint": "NBA Injury Report PDF via package nbainjuries",
        "api_source": "NBA Injury Report PDF officiel parsé via package Python nbainjuries (PyPI 1.1.1)",
        "cout": "gratuit",
        "notes": "NBA Injury Report PDF officiel publié 17h ET veille + maj H-1, parsé via package nbainjuries (PyPI 1.1.1, fév 2026, MIT, actif). Dépendance Java JRE/JDK ≥ 8 (tabula-py). Implémenté V3 phase 2 sous-phase 2.1. Fallback possible : Balldontlie ALL-STAR 9.99$/mo via feature flag (non implémenté).",
    },
    "ROST-002": {
        "audit_status": None,
        "fournisseur": "RotoWire + NBA CDN",
        "endpoint": "RotoWire scraping HTML + NBA CDN boxscore.json",
        "api_source": "RotoWire scraping HTML (expected H-24/H-30) + NBA CDN boxscore.json (confirmed T-30+) → posture expected vs confirmed",
        "cout": "gratuit",
        "notes": "Pas de source officielle pre-game gratuite garantie (la NBA n'impose pas de soumission du starting five pre-tip). Approche \"expected vs confirmed\" actée : RotoWire scraping pour l'expected H-24/H-30, NBA CDN boxscore.json champ `starter: 1` pour le confirmed T-30+ (souvent post-tip). Scraping RotoWire conservateur (rate 1 req/5min, cache 4h, UA explicite, pas de compte créé). Lineups.com éliminé (403 Cloudflare). Implémentation prévue V3 phase 2 sous-phase 2.2.",
    },
    "ROST-003": {
        "audit_status": None,
        "fournisseur": "NBA officiel (PDF)",
        "endpoint": "Dérivé de ROST-001 (filtre status=Out)",
        "api_source": "Dérivé de ROST-001 par filtre status == 'Out'",
        "cout": "gratuit",
        "notes": "Pas de source dédiée. Dérivé de ROST-001 par filtre `status == Out` sur le payload InjuryReport. Implémenté V3 phase 2 sous-phase 2.1.",
    },
    "ROST-004": {
        "audit_status": None,
        "fournisseur": "NBA officiel (PDF)",
        "endpoint": "Dérivé de ROST-001 (filtre status in {Q, D, P})",
        "api_source": "Dérivé de ROST-001 par filtre status in {Questionable, Doubtful, Probable}",
        "cout": "gratuit",
        "notes": "Pas de source dédiée. Dérivé de ROST-001 par filtre `status in {Questionable, Doubtful, Probable}` sur le payload InjuryReport. Implémenté V3 phase 2 sous-phase 2.1.",
    },
    "ROST-005": {
        "audit_status": None,
        "fournisseur": "NBA officiel (PDF) + NBA Stats",
        "endpoint": "NBA Stats commonteamroster MOINS dérivés de ROST-001 (status=Out)",
        "api_source": "Calcul croisé NBA Stats CommonTeamRoster + NBA Injury Report (filtre status != Out)",
        "cout": "gratuit",
        "notes": "Calcul : CommonTeamRoster (NBA Stats) MOINS joueurs OUT du NBA Injury Report (= ROST-003). Implémenté V3 phase 2 sous-phase 2.1.",
    },
    "STAT-033": {
        "audit_status": None,
        "fournisseur": "ProSportsTransactions + NBA Stats",
        "endpoint": "pro_sports_transactions (PST via Unflare) + nba_api PlayerGameLogs",
        "api_source": "ProSportsTransactions via package pro_sports_transactions (PyPI 1.1.2) + nba_api PlayerGameLogs pour stats au retour",
        "cout": "gratuit",
        "notes": "ProSportsTransactions via package pro_sports_transactions (PyPI 1.1.2, fév 2026, MIT, support Python 3.11-3.14, historique depuis 1946 toutes ligues). Container Unflare obligatoire (bypass Cloudflare, co-déployé via docker-compose). Stats au retour reconstituées en joignant les dates de retour avec nba_api.PlayerGameLogs. Basketball-Reference Transactions en source secondaire de corroboration (déjà intégré au backend). Backfill batch one-shot 2014-2026 + delta quotidien faible. Implémentation prévue V3 phase 2 sous-phase 2.3.",
    },
}

ALLOWED_FIELDS = {"fournisseur", "endpoint", "api_source", "cout", "notes", "audit_status"}


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    index = {d["id"]: d for d in data}

    for row_id, patch in PATCHES.items():
        if row_id not in index:
            print(f"  WARN {row_id} introuvable — ignoré")
            continue
        row = index[row_id]
        for field, value in patch.items():
            assert field in ALLOWED_FIELDS, f"Champ interdit : {field}"
            row[field] = value
        print(f"  OK {row_id} — {row['donnee'][:50]}")

    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n6 lignes patchées dans {DATA_PATH}")


if __name__ == "__main__":
    main()
