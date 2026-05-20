# statspro-dashboard

Outil de pilotage PoC NBA : filtrage, suivi et export des 163 données candidates du dashboard StatsPro.
Conçu pour survivre à plusieurs cycles de PoC sans dériver du réel ni nécessiter une stack lourde.

Voir CLAUDE.md et IMPLEMENTATION.md à la racine pour les invariants et le plan d'exécution.

## Pipeline audit → dashboard

Depuis V2 (2026-05-20), un pipeline automatise la propagation des résultats d'audit `statspro-backend` vers `data/dashboard.json`. Le script `sync_dashboard.py` écrit `audit_status` sans toucher aux champs produit manuels (`data_status`, `data_quality`). ~117 endpoints connus du pipeline au 2026-05-20.

Workflow complet, fichiers, mapping des 3 axes de statut, cas d'usage : voir **[PIPELINE.md](PIPELINE.md)**.

## Ouvrir en local

```bash
python3 -m http.server 8000
```

Puis ouvrir [http://localhost:8000](http://localhost:8000) (GitHub Pages) ou [http://localhost:8000/index.html](http://localhost:8000/index.html).

## Workflow type d'une session de test

1. **Filtrer** les lignes à tester (ex: `data_status = not_implemented` + `fournisseur = NBA Stats`)
2. **Tester** l'endpoint contre nba.com
3. **Éditer** la ligne dans le dashboard : clic sur la ligne → ✎ Éditer → remplir `data_status`, `data_quality`, `validation_note` → Enregistrer (`audit_status` est non éditable, alimenté par le pipeline)
4. **Exporter** : clic sur le badge rouge dans le header → "Exporter JSON patch" → télécharge `patch_YYYYMMDD.json`
5. **Appliquer** le patch dans `data/dashboard.json` :

```bash
python3 scripts/apply_patch.py exports/patch_YYYYMMDD.json
```

Ou manuellement : ouvrir `data/dashboard.json`, retrouver les lignes par `num`, coller les champs modifiés.

6. **Commiter** :

```bash
git add data/dashboard.json
git commit -m "data: patch PoC session YYYY-MM-DD"
```

7. **Réinitialiser** les modifs locales dans le dashboard (badge → "Réinitialiser") après le commit.

## Export pour IA

Filtrer une sélection (ex: `data_status = blocked_no_source`), cliquer **"Exporter pour IA (markdown)"** dans la sidebar.
Coller le contenu du `.md` dans Claude — le prompt est inclus en tête du fichier.

## Tag de snapshot en fin de cycle PoC

```bash
git tag poc-1-final
# ou pour la V1 officielle :
git tag v1.0
```

## Structure

```
statspro-dashboard/
├── data/dashboard.json        # source unique de vérité — 163 lignes
├── dashboard_mapping.json     # mapping id ↔ endpoints (pipeline)
├── sync_dashboard.py          # sync audit → dashboard (pipeline)
├── scripts/apply_patch.py     # applique les patches manuels (UI)
├── scripts/migrate.py         # migration one-shot HTML → JSON
├── scripts/bdl_patch_table.py # table des patches BDL auditée
├── docs/SCHEMA.md             # sémantique gelée des champs
├── exports/                   # patches JSON et exports markdown (gitignorés)
├── index.html                 # le dashboard (HTML/CSS/JS vanilla)
├── PIPELINE.md                # doc pipeline audit → dashboard
├── CLAUDE.md                  # invariants du projet
└── IMPLEMENTATION.md          # plan d'exécution
```
