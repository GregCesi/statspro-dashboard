# statspro-dashboard

Outil de pilotage PoC NBA : filtrage, suivi et export des 163 données candidates du dashboard StatsPro.
Conçu pour survivre à plusieurs cycles de PoC sans dériver du réel ni nécessiter une stack lourde.

Voir CLAUDE.md et IMPLEMENTATION.md à la racine pour les invariants et le plan d'exécution.

## Ouvrir en local

```bash
python3 -m http.server 8000
```

Puis ouvrir [http://localhost:8000/dashboard_statspro.html](http://localhost:8000/dashboard_statspro.html).

## Workflow type d'une session de test

1. **Filtrer** les lignes à tester (ex: `poc_status = non_testé` + `fournisseur = NBA Stats`)
2. **Tester** l'endpoint contre nba.com
3. **Éditer** la ligne dans le dashboard : clic sur la ligne → ✎ Éditer → remplir `poc_status`, `data_quality`, `validation_note` → Enregistrer
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

Filtrer une sélection (ex: `poc_status = bloqué`), cliquer **"Exporter pour IA (markdown)"** dans la sidebar.
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
├── data/dashboard.json       # source unique de vérité — 163 lignes
├── docs/SCHEMA.md            # sémantique gelée des champs PoC
├── scripts/migrate.py        # migration one-shot HTML → JSON
├── scripts/bdl_patch_table.py# table des patches BDL auditée
├── exports/                  # patches JSON et exports markdown (gitignorés)
├── dashboard_statspro.html   # le dashboard (HTML/CSS/JS vanilla)
├── CLAUDE.md                 # invariants du projet
└── IMPLEMENTATION.md         # plan d'exécution
```
