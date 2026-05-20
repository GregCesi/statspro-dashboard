#!/usr/bin/env python3
# sync_dashboard.py
# Synchronise les résultats d'audit vers data/dashboard.json.
# Whitelist stricte : audit_status, last_updated, audit_duration_s.
# Usage : python3 sync_dashboard.py --audit <path> --dashboard <path> --mapping <path>

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MANAGED_FIELDS = ["audit_status", "last_updated", "audit_duration_s"]

# Hiérarchie OR : validated > validated_slow > unreliable_upstream > bugged_parsing > blocked_no_source
STATUS_HIERARCHY = [
    "validated",
    "validated_slow",
    "unreliable_upstream",
    "bugged_parsing",
    "blocked_no_source",
]

# Traduction statuts audit → statuts dashboard (audit_status valides dans SCHEMA.md)
# Les statuts d'audit non traduisibles (skipped, error) sont ignorés.
AUDIT_STATUS_MAP = {
    "validated": "validated",
    "validated_slow": "validated_slow",
    "bugged_parsing": "bugged_parsing",
    "unreliable_upstream": "unreliable_upstream",
    "blocked_no_source": "blocked_no_source",
    "degraded": "validated_slow",      # audit "degraded" = latence > warn_time → validated_slow
    "blocked": "blocked_no_source",    # audit "blocked" = pas de source → blocked_no_source
}
# Statuts ignorés (ne pas mettre à jour la ligne) : "skipped", "error"


def load_json(path, expected_version=None):
    """Charge un fichier JSON. Vérifie schema_version si attendu."""
    p = Path(path)
    if not p.exists():
        print(f"ERREUR : fichier introuvable : {p}")
        sys.exit(1)
    data = json.loads(p.read_text(encoding="utf-8"))
    if expected_version is not None:
        version = data.get("schema_version")
        if version != expected_version:
            print(
                f"ERREUR : schema_version mismatch dans {p.name} : "
                f"attendu {expected_version!r}, trouvé {version!r}"
            )
            sys.exit(1)
    return data


def build_audit_index(audit_data):
    """Construit un index endpoint_path → {status, elapsed_ms, audited_at}."""
    index = {}
    skipped = []
    for r in audit_data.get("results", []):
        path = r.get("path")
        if not path or path == "/health":
            continue
        raw_status = r.get("status")
        mapped_status = AUDIT_STATUS_MAP.get(raw_status)
        if mapped_status is None:
            skipped.append((path, raw_status))
            continue
        index[path] = {
            "status": mapped_status,
            "elapsed_ms": r.get("elapsed_ms"),
            "audited_at": audit_data.get("run_info", {}).get("timestamp"),
        }
    if skipped:
        print(f"  {len(skipped)} endpoints ignorés (statut non traduisible) :")
        for path, status in skipped:
            print(f"    {path} → {status}")
    return index


def resolve_status(endpoints, audit_index, propagation="or"):
    """Résout le audit_status d'un ID à partir de ses endpoints mappés.

    Retourne (status, duration_s) ou (None, None) si aucun endpoint audité.
    """
    if not endpoints:
        return None, None

    statuses = []
    durations = []
    for ep in endpoints:
        if ep in audit_index:
            info = audit_index[ep]
            statuses.append(info["status"])
            if info["elapsed_ms"] is not None:
                durations.append(info["elapsed_ms"] / 1000.0)

    if not statuses:
        # Aucun endpoint audité dans ce run → ne pas toucher
        return None, None

    if propagation == "and":
        # AND : tous doivent être validated pour que la ligne soit validated
        # Sinon, prendre le pire statut
        rank = {s: i for i, s in enumerate(STATUS_HIERARCHY)}
        worst_idx = max(rank.get(s, len(STATUS_HIERARCHY)) for s in statuses)
        if worst_idx < len(STATUS_HIERARCHY):
            resolved = STATUS_HIERARCHY[worst_idx]
        else:
            resolved = statuses[0]
    else:
        # OR : prendre le meilleur statut (rang le plus bas dans la hiérarchie)
        rank = {s: i for i, s in enumerate(STATUS_HIERARCHY)}
        best_idx = min(rank.get(s, len(STATUS_HIERARCHY)) for s in statuses)
        if best_idx < len(STATUS_HIERARCHY):
            resolved = STATUS_HIERARCHY[best_idx]
        else:
            resolved = statuses[0]

    duration = round(max(durations), 2) if durations else None
    return resolved, duration


def sync(dashboard, mapping_data, audit_index):
    """Applique la sync sur les lignes du dashboard.

    Retourne (updated_count, changes_list).
    """
    mapping = mapping_data.get("mapping", {})
    index = {d["id"]: d for d in dashboard}
    now = datetime.now(timezone.utc).isoformat()

    updated = 0
    changes = []

    for line_id, config in mapping.items():
        if line_id not in index:
            continue

        endpoints = config.get("endpoints", [])
        propagation = config.get("propagation", "or")

        new_status, duration_s = resolve_status(endpoints, audit_index, propagation)

        if new_status is None:
            # Aucun endpoint audité → ne pas toucher
            continue

        row = index[line_id]
        old_status = row.get("audit_status")

        if old_status == new_status and row.get("audit_duration_s") == duration_s:
            # Pas de changement
            continue

        change = {
            "id": line_id,
            "old_audit_status": old_status,
            "new_audit_status": new_status,
        }

        row["audit_status"] = new_status
        row["last_updated"] = now
        if duration_s is not None:
            row["audit_duration_s"] = duration_s

        changes.append(change)
        updated += 1

    return updated, changes


def write_dashboard(data, path):
    """Écrit le dashboard en JSON déterministe."""
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def generate_report(audit_index, mapping_data, dashboard, changes):
    """Génère le rapport de cohérence (stdout + fichier .md)."""
    mapping = mapping_data.get("mapping", {})
    dash_ids = {d["id"] for d in dashboard}

    # 1. Endpoints audités non mappés
    mapped_endpoints = set()
    for config in mapping.values():
        mapped_endpoints.update(config.get("endpoints", []))
    unmapped_audit = sorted(set(audit_index.keys()) - mapped_endpoints)

    # 2. IDs mappés vers endpoints absents de l'audit
    missing_audit = []
    for line_id, config in sorted(mapping.items()):
        for ep in config.get("endpoints", []):
            if ep not in audit_index:
                missing_audit.append((line_id, ep))

    # 3. Endpoints présents dans plusieurs IDs
    ep_to_ids = {}
    for line_id, config in mapping.items():
        for ep in config.get("endpoints", []):
            ep_to_ids.setdefault(ep, []).append(line_id)
    shared_endpoints = {ep: ids for ep, ids in sorted(ep_to_ids.items()) if len(ids) > 1}

    # 4. IDs dans le mapping absents du dashboard.json
    orphan_ids = sorted(set(mapping.keys()) - dash_ids)

    # --- Stdout résumé ---
    print(f"\n{'='*60}")
    print(f"Rapport de cohérence")
    print(f"{'='*60}")
    print(f"  Endpoints audités :    {len(audit_index)}")
    print(f"  Endpoints mappés :     {len(mapped_endpoints)}")
    print(f"  Lignes mises à jour :  {len(changes)}")
    print(f"  Incohérences :")
    print(f"    Endpoints non mappés :     {len(unmapped_audit)}")
    print(f"    Endpoints absents audit :  {len(missing_audit)}")
    print(f"    Endpoints partagés :       {len(shared_endpoints)}")
    print(f"    IDs orphelins :            {len(orphan_ids)}")

    # --- Fichier .md ---
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = Path(f"sync_report_{ts}.md")

    lines = []
    lines.append(f"# Rapport de synchronisation — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"- Endpoints audités : {len(audit_index)}")
    lines.append(f"- Endpoints mappés : {len(mapped_endpoints)}")
    lines.append(f"- Lignes mises à jour : {len(changes)}")
    lines.append("")

    if changes:
        lines.append("## Changements appliqués")
        lines.append("")
        for c in changes:
            lines.append(
                f"- `{c['id']}` : {c['old_audit_status']} → **{c['new_audit_status']}**"
            )
        lines.append("")

    lines.append("## 1. Endpoints audités non mappés")
    lines.append("")
    if unmapped_audit:
        for ep in unmapped_audit:
            lines.append(f"- `{ep}`")
    else:
        lines.append("Aucun.")
    lines.append("")

    lines.append("## 2. Endpoints mappés absents de l'audit")
    lines.append("")
    if missing_audit:
        for line_id, ep in missing_audit:
            lines.append(f"- `{line_id}` → `{ep}`")
    else:
        lines.append("Aucun.")
    lines.append("")

    lines.append("## 3. Endpoints partagés entre plusieurs IDs")
    lines.append("")
    if shared_endpoints:
        for ep, ids in shared_endpoints.items():
            lines.append(f"- `{ep}` → {', '.join(f'`{i}`' for i in sorted(ids))}")
    else:
        lines.append("Aucun.")
    lines.append("")

    lines.append("## 4. IDs orphelins (dans le mapping, absents du dashboard)")
    lines.append("")
    if orphan_ids:
        for oid in orphan_ids:
            lines.append(f"- `{oid}`")
    else:
        lines.append("Aucun.")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Rapport écrit : {report_path}")

    return {
        "unmapped_audit": unmapped_audit,
        "missing_audit": missing_audit,
        "shared_endpoints": shared_endpoints,
        "orphan_ids": orphan_ids,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Synchronise audit_results.json → data/dashboard.json"
    )
    parser.add_argument("--audit", required=True, help="Chemin vers audit_results.json")
    parser.add_argument("--dashboard", required=True, help="Chemin vers data/dashboard.json")
    parser.add_argument("--mapping", required=True, help="Chemin vers dashboard_mapping.json")
    args = parser.parse_args()

    # Chargement + validation
    audit_data = load_json(args.audit)
    dashboard = load_json(args.dashboard)
    mapping_data = load_json(args.mapping, expected_version="1.0")

    # Construction index audit
    audit_index = build_audit_index(audit_data)
    print(f"Audit : {len(audit_index)} endpoints chargés")
    print(f"Dashboard : {len(dashboard)} lignes")
    print(f"Mapping : {len(mapping_data.get('mapping', {}))} entrées")

    # Sync
    updated, changes = sync(dashboard, mapping_data, audit_index)
    print(f"\n{updated} lignes mises à jour")

    # Écriture
    write_dashboard(dashboard, args.dashboard)
    print(f"Écrit : {args.dashboard}")

    # Rapport
    generate_report(audit_index, mapping_data, dashboard, changes)


if __name__ == "__main__":
    main()
