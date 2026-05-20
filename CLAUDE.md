# CLAUDE.md — statspro-dashboard

## Contexte projet

Outil de pilotage projet versionné dérivé du dashboard de cadrage StatsPro : 163 données NBA candidates à filtrer, suivre (`audit_status`, `data_status`, `data_quality`) et exporter à chaque cycle de PoC. **Contrainte forte structurante** : l'outil doit survivre à plusieurs cycles de PoC sans dériver du réel, sans empiler de stack lourd qui le transformerait en deuxième projet à maintenir.

Depuis le 2026-05-20, le repo héberge également le **pipeline de synchronisation audit → dashboard** (script `sync_dashboard.py` + mapping `dashboard_mapping.json`), qui automatise la propagation des résultats d'audit produits par `statspro-backend/tools/audit/` vers `data/dashboard.json`.

## Stack imposée

- **HTML / CSS / JS vanilla** — pas de framework JS, pas de TypeScript
- **Chart.js 4.4.1** (CDN) — charts existants à préserver tels quels
- **Python 3.11+** — scripts de migration jetables (`scripts/migrate.py`, `scripts/apply_patch.py`), script de sync (`sync_dashboard.py`). Stdlib uniquement pour la sync (pas de dépendance externe).
- **Git** — versionnement obligatoire, tag de snapshot à chaque fin de cycle PoC

Pas de Node en runtime, pas de build step, pas de DB.

## Règles de développement

### Format & stack
- **Pas de framework JS.** React, Vue, Next, Svelte interdits en V1. Si un besoin émerge, il passe par un nouveau PROSIT.
- **Pas de build step.** L'outil s'ouvre par `python -m http.server` (ou équivalent static) sans étape de compilation.
- **Pas de runtime serveur en V1.** Tout est statique. Aucune API consommée en runtime.
- **JSON pur pour les données.** Pas de SQLite, pas de XML, pas de YAML. Diff Git lisible non négociable.

### Données
- **Source unique de vérité : `data/dashboard.json`.** 163 lignes externalisées hors du HTML.
- **5 champs PoC sur chaque ligne** (depuis V2 dashboard, 2026-05-20) : `audit_status`, `data_status`, `data_quality`, `validation_note`, `last_updated`. Le champ historique `poc_status` est **supprimé** (éclaté entre `audit_status` et `data_status`).
- **Identifiant stable `id: "CAT-NNN"`** sur chaque ligne, en plus du `num` historique (1-163). 9 préfixes : `STAT`, `RES`, `PACE`, `LIVE`, `ROST`, `CLAS`, `H2H`, `STYL`, `FAT`. Numérotation séquentielle dans la catégorie, ordre d'apparition dans le JSON.
- **Sémantique gelée dans `docs/SCHEMA.md`.** Toute modification de valeur admise passe par ce fichier, jamais par le code.
- **Performance technique (latence, taux d'erreur) explicitement hors V1.** Si le besoin émerge, c'est du monitoring backend, pas un champ du JSON.

### 3 axes de statut — disjoints, jamais fusionnés

- **`audit_status`** — technique, EN, 5 valeurs : `validated`, `validated_slow`, `bugged_parsing`, `unreliable_upstream`, `blocked_no_source` (+ `null` pour les non audités). **Alimenté UNIQUEMENT par `sync_dashboard.py`** — non éditable via l'UI.
- **`data_status`** — produit, 5 valeurs : `live`, `degraded`, `not_implemented`, `deferred_v2`, `blocked_no_source`. **Alimenté manuellement** via l'édition inline du dashboard (mode édition + export JSON patch + `apply_patch.py`).
- **`data_quality`** — exactitude vs source externe, valeurs : `juste`, `approximatif`, `incomplet`, `unknown`. **Alimenté manuellement**. Champ pré-existant V1, comportement inchangé.

Anti-pattern : afficher un seul des trois champs et oublier les deux autres dans un graphique ou un compteur. Les 3 axes doivent toujours coexister visuellement, même si l'usage routine se focalise sur 1 ou 2.

### Workflow d'édition manuelle (préservé V1)
- **Édition inline dans le dashboard.** Pas d'éditeur externe.
- **localStorage tampon** entre modifs et export JSON patch. Pas de persistance directe vers le fichier.
- **Indicateur visuel "N modifs non exportées" obligatoire** dans le header — c'est le principal garde-fou anti-dérive.
- **Auto-fill du `last_updated`** par le frontend à chaque modif. Jamais à la main.
- **Édition autorisée uniquement sur `data_status`, `data_quality`, `validation_note`.** `audit_status` reste **non éditable via l'UI** (alimenté uniquement par le script de sync).

### Workflow de sync automatique (V2 dashboard, ajouté 2026-05-20)
- **`sync_dashboard.py` à la racine du repo.** Tourne en CLI manuelle après chaque audit `statspro-backend`.
- **Idempotence absolue.** N runs consécutifs sur même input → output identique au byte près. Vérification par `git diff` après chaque exécution.
- **Whitelist stricte des champs gérés** : `audit_status`, `last_updated`, `audit_duration_s`. Aucun autre champ ne doit être touché par le script. Toute violation = bug critique.
- **Tolérance aux trous.** Endpoint mappé mais absent du run d'audit → ne pas toucher `audit_status` existant. Ligne sans mapping → `audit_status` reste `null` ou inchangé. Jamais de crash.
- **Sortie JSON déterministe** : `json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)`. Diff Git lisible obligatoire.
- **Rapport de cohérence** produit à chaque run (`sync_report_YYYYMMDD_HHMM.md` à la racine) : endpoints audités non mappés, IDs mappés vers endpoints absents de l'audit, doublons, IDs orphelins. Non bloquant.

### Coexistence `apply_patch.py` ↔ `sync_dashboard.py`
- **`apply_patch.py`** applique des patches issus de **l'édition manuelle** via l'UI. Touche `data_status`, `data_quality`, `validation_note`, `last_updated`. **Ne touche jamais `audit_status`.**
- **`sync_dashboard.py`** applique des résultats d'audit **automatiques**. Touche `audit_status`, `last_updated`, `audit_duration_s`. **Ne touche jamais `data_status` ou `data_quality`.**
- **Pas de chevauchement de champs**, sauf `last_updated` qui est écrit par les deux (dernier qui parle gagne — c'est OK).
- **Les deux scripts coexistent**, ne s'appellent pas l'un l'autre, n'ont pas de dépendance croisée.

### Mapping endpoint ↔ donnée
- **Source de vérité unique** : `dashboard_mapping.json` à la racine. Format flat :
  ```json
  {
    "schema_version": "1.0",
    "mapping": { "STAT-001": { "endpoints": ["/nba-stats/foo"] } }
  }
  ```
- **Règle de propagation `or` par défaut implicite** : champ `propagation` absent = `or`. Seuls les rares cas explicites portent `"propagation": "and"`. Ne pas polluer les 163 entrées avec `"propagation": "or"`.
- **Édition manuelle**, validation de cohérence non bloquante par le rapport de sync.
- **Hiérarchie OR** : `validated` > `validated_slow` > `unreliable_upstream` > `bugged_parsing` > `blocked_no_source`. Au moins un endpoint au statut le plus haut → ligne au même statut.

### Versioning de schéma JSON
- **`schema_version` obligatoire** en tête de `audit_results.json` et `dashboard_mapping.json`. Le script de sync vérifie la compatibilité au démarrage et refuse de tourner si mismatch.
- Bump explicite à chaque changement breaking.

### Préservation de l'existant
- **Le code dashboard actuel marche** : charts, filtres combinables, KPIs, matrice coût×effort, export CSV, localStorage de filtres, édition inline, export JSON patch. Ne pas réécrire, **étendre**.
- **Aucune régression visuelle acceptable** lors de patches HTML. Test de référence : avant et après côte à côte affichent les mêmes données pour les champs inchangés.
- **`str_replace` ciblé** sur les blocs concernés du HTML, pas de réécriture complète du fichier.

### Garde-fous projet
- **Time-box : quelques jours, pas des semaines.** Si une étape déborde > 1.5× son estimation, stop — c'est du sur-engineering, simplifier le scope.
- **Édition d'une ligne < 30 sec en usage réel.** Si on dépasse au test end-to-end, on revoit l'UX, on n'empile pas du polish.
- **Aucune nouvelle feature non listée dans IMPLEMENTATION.md** sans repasser par le PROSIT.
- **Simplicité > élégance.** Toute abstraction qui rend l'édition manuelle du JSON plus lourde est suspecte.

### Workflow Claude Code
- **Une étape à la fois.** Validation systématique entre chaque étape. Jamais d'enchaînement multi-étapes sans confirmation explicite.
- **Édition ciblée.** `str_replace` sur les blocs concernés, pas de réécriture complète des fichiers.
- **Pas de préambule, pas de postambule.** Le résultat parle de lui-même.
- **Préserver à l'identique** tout champ non explicitement géré dans `data/dashboard.json` (héritage V1, futurs ajouts).

## Référence d'exécution

Plan d'exécution V1 dashboard archivé dans `docs/archive/IMPLEMENTATION-v1.md` (trace historique, 15/15 livrables, V1 close au 2026-05-20).

Plan d'exécution courant (pipeline audit → dashboard, V2 dashboard) : `IMPLEMENTATION.md` à la racine.

Sémantique des champs et valeurs admises : `docs/SCHEMA.md`.
