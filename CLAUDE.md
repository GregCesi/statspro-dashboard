# CLAUDE.md — statspro-dashboard

## Contexte projet

Outil de pilotage projet versionné dérivé du dashboard de cadrage StatsPro : 163 données NBA candidates à filtrer, suivre (`poc_status`, `data_quality`) et exporter à chaque cycle de PoC. **Contrainte forte structurante** : l'outil doit survivre à plusieurs cycles de PoC sans dériver du réel, sans empiler de stack lourd qui le transformerait en deuxième projet à maintenir.

## Stack imposée

- **HTML / CSS / JS vanilla** — pas de framework JS, pas de TypeScript
- **Chart.js 4.4.1** (CDN) — charts existants à préserver tels quels
- **Python 3.11+** — uniquement pour le script de migration one-shot (`scripts/migrate.py`)
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
- **3 champs PoC ajoutés à chaque ligne** : `poc_status`, `data_quality`, `validation_note`. Plus un `last_updated`.
- **Sémantique gelée dans `docs/SCHEMA.md`.** Toute modification de valeur admise passe par ce fichier, jamais par le code.
- **Performance technique (latence, taux d'erreur) explicitement hors V1.** Si le besoin émerge, c'est du monitoring backend, pas un champ du JSON.

### Workflow d'édition
- **Édition inline dans le dashboard.** Pas d'éditeur externe en V1.
- **localStorage tampon** entre modifs et export JSON patch. Pas de persistance directe vers le fichier.
- **Indicateur visuel "N modifs non exportées" obligatoire** dans le header — c'est le principal garde-fou anti-dérive.
- **Auto-fill du `last_updated`** par le frontend à chaque modif. Jamais à la main.

### Préservation de l'existant
- **Le code dashboard actuel marche** : charts, filtres combinables, KPIs, matrice coût×effort, export CSV, localStorage de filtres. Ne pas réécrire, **étendre**.
- **Aucune régression visuelle acceptable** lors du passage HTML inline → JSON externe. Test de référence : ancien et nouveau dashboard côte à côte affichent la même chose.
- **`str_replace` ciblé** sur les blocs concernés du HTML, pas de réécriture complète du fichier.

### Garde-fous projet
- **Time-box : quelques jours, pas des semaines.** Si une étape déborde > 1.5× son estimation, stop — c'est du sur-engineering, simplifier le scope.
- **Édition d'une ligne < 30 sec en usage réel.** Si on dépasse au test end-to-end, on revoit l'UX, on n'empile pas du polish.
- **Aucune nouvelle feature non listée dans IMPLEMENTATION.md** sans repasser par le PROSIT.
- **Simplicité > élégance.** Tout abstraction qui rend l'édition manuelle du JSON plus lourde est suspecte.

### Workflow Claude Code
- **Une étape à la fois.** Validation systématique entre chaque étape. Jamais d'enchaînement multi-étapes sans confirmation explicite.
- **Édition ciblée.** `str_replace` sur les blocs concernés, pas de réécriture complète des fichiers.
- **Pas de préambule, pas de postambule.** Le résultat parle de lui-même.

## Référence d'exécution

Pour le plan d'exécution, les schémas cibles, les phases et les critères de validation : voir `IMPLEMENTATION.md` à la racine.
