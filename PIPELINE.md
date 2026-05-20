# PIPELINE.md — Pipeline audit → dashboard

> Workflow opérationnel pour synchroniser les résultats d'audit `statspro-backend` vers le dashboard de pilotage `statspro-dashboard`. Lisible en 5 minutes, utilisable dans 3 mois sans mémoire.

---

## 1. Vue d'ensemble

Le pipeline propage les résultats d'audit produits par `statspro-backend/tools/audit/` vers `data/dashboard.json` dans ce repo. Il écrit automatiquement `audit_status` sur les lignes du dashboard sans toucher aux champs produit (`data_status`, `data_quality`) qui restent sous contrôle manuel. Deux repos impliqués : `statspro-backend` (source des audits) et `statspro-dashboard` (destination). Le lien entre les deux est le fichier `audit_results.json` exporté côté backend et consommé côté dashboard.

## 2. Workflow quotidien

Après chaque campagne d'audit backend, enchaîner ces 4 étapes :

```bash
# 1. Exporter les résultats d'audit en JSON (côté backend)
cd ../statspro-backend
python -m tools.audit export --json --output audit_results.json

# 2. Synchroniser vers le dashboard (côté dashboard)
cd ../statspro-dashboard
python sync_dashboard.py \
  --audit ../statspro-backend/audit_results.json \
  --dashboard ./data/dashboard.json \
  --mapping ./dashboard_mapping.json

# 3. Lire le rapport de cohérence
#    → sync_report_YYYYMMDD_HHMM.md à la racine
#    → arbitrer les incohérences si besoin (endpoints non mappés, IDs orphelins)

# 4. Vérifier, commiter, pousser
git diff data/dashboard.json   # ne doit montrer QUE audit_status, last_updated, audit_duration_s
git add data/dashboard.json
git commit -m "data: sync audit YYYY-MM-DD"
git push
```

La sync est idempotente : N runs consécutifs sur le même `audit_results.json` produisent un `dashboard.json` identique au byte près. Vérifiable par `git diff` après chaque exécution.

## 3. Fichiers du pipeline

| Fichier | Repo | Rôle |
|---------|------|------|
| `tools/audit/` | backend | Module d'audit — teste les endpoints, produit les résultats |
| `audit_results.json` | backend (généré) | Export JSON machine-readable, `schema_version: "1.0"` |
| `data/dashboard.json` | dashboard | Source unique de vérité — 163 lignes, 5 champs PoC par ligne |
| `dashboard_mapping.json` | dashboard | Mapping `id` ↔ endpoints, format flat, édition manuelle |
| `sync_dashboard.py` | dashboard | Script de sync — lit l'audit, écrit `audit_status` dans le dashboard |
| `sync_report_*.md` | dashboard (généré) | Rapport de cohérence daté, non bloquant |
| `scripts/apply_patch.py` | dashboard | Applique les patches manuels (UI) — ne touche jamais `audit_status` |
| `docs/SCHEMA.md` | dashboard | Sémantique gelée des champs et valeurs admises |
| `PIPELINE.md` | dashboard | Ce fichier |
| `CLAUDE.md` | dashboard | Invariants du projet, règles de développement |
| `IMPLEMENTATION.md` | dashboard | Plan d'exécution séquencé (Phases 1-5) |

## 4. Les 3 axes de statut

Les 3 axes sont **disjoints** : chacun a sa propre grille de valeurs, son propre flux d'alimentation, et ne doit jamais être fusionné avec un autre dans un graphique ou un compteur.

| Axe | Nature | Alimentation | Valeurs | Script |
|-----|--------|-------------|---------|--------|
| `audit_status` | Technique | Automatique | `validated`, `validated_slow`, `bugged_parsing`, `unreliable_upstream`, `blocked_no_source`, `null` | `sync_dashboard.py` |
| `data_status` | Produit | Manuelle (UI) | `live`, `degraded`, `not_implemented`, `deferred_v2`, `blocked_no_source` | `apply_patch.py` |
| `data_quality` | Exactitude | Manuelle (UI) | `juste`, `approximatif`, `incomplet`, `unknown` | `apply_patch.py` |

**Exemples concrets (valeurs réelles post-sync 2026-05-19) :**

**ROST-006** (Minutes prévues par joueur) — le cas clean, tout fonctionne :
- `audit_status: validated` — endpoint testé, HTTP 200, latence < 1 s
- `data_status: live` — donnée exploitable en production
- `data_quality: juste` — valeur identique à nba.com

**H2H-007** (Score final des confrontations en playoffs) — dégradation gracieuse, le technique fonctionne mais le produit est limité :
- `audit_status: validated` — endpoint répond correctement
- `data_status: degraded` — donnée exploitable mais non croisée avec source officielle
- `data_quality: incomplet` — couverture partielle des playoffs

**ROST-001** (Statut injury par joueur) — bloqué, pas de source :
- `audit_status: blocked_no_source` — BDL paid plan requis, pas d'alternative gratuite
- `data_status: blocked_no_source` — décision produit de ne pas investir
- `data_quality: unknown` — jamais évalué, pas de donnée à comparer

L'intérêt du modèle 3 axes apparaît sur H2H-007 : l'audit technique passe (`validated`), mais la donnée n'est pas au niveau produit attendu (`degraded`). Un statut unique aurait noyé cette distinction.

## 5. Coexistence `apply_patch.py` ↔ `sync_dashboard.py`

Les deux scripts coexistent, ne s'appellent pas l'un l'autre, n'ont aucune dépendance croisée.

| Champ | `sync_dashboard.py` | `apply_patch.py` |
|-------|---------------------|------------------|
| `audit_status` | **écrit** | refuse silencieusement (warning) |
| `audit_duration_s` | **écrit** | — |
| `data_status` | — | **écrit** |
| `data_quality` | — | **écrit** |
| `validation_note` | — | **écrit** |
| `last_updated` | **écrit** | **écrit** |

Seul `last_updated` est écrit par les deux — le dernier qui parle gagne, c'est intentionnel. L'ordre d'exécution (sync avant ou après patch) n'a pas d'importance pour la cohérence des données : chaque script ne touche que ses champs.

## 6. Ajouter une donnée nouvelle

1. **Ajouter la ligne** dans `data/dashboard.json` avec tous les champs du schéma. Attribuer un `num` (suivant le dernier) et un `id` conforme au format `CAT-NNN` (voir les 12 préfixes dans `docs/SCHEMA.md`). Initialiser `audit_status: null`, `data_status: "not_implemented"`, `data_quality: "unknown"`.

2. **Mapper dans `dashboard_mapping.json`** si un endpoint backend existe. Ajouter une entrée `"CAT-NNN": { "endpoints": ["/nba-stats/..."] }`. Si pas d'endpoint, ne pas créer d'entrée — la ligne restera `audit_status: null`.

3. **Lancer la sync** (`python sync_dashboard.py ...`). La nouvelle ligne sera alimentée si son endpoint est présent dans l'audit.

4. **Vérifier le rapport** (`sync_report_*.md`). Si l'endpoint est absent de l'audit, il apparaîtra dans la section "Endpoints mappés absents de l'audit" — c'est attendu tant que l'audit n'a pas été relancé.

5. **Vérifier `docs/SCHEMA.md`** si la nouvelle donnée nécessite une valeur de statut qui n'existe pas encore. La sémantique est gelée dans ce fichier — toute nouvelle valeur de `audit_status`, `data_status` ou `data_quality` doit y être définie avant d'être utilisée dans le JSON ou le code. Sans ça, la sémantique dérive silencieusement.

## 7. Patcher le mapping

Le fichier `dashboard_mapping.json` est édité manuellement. Format flat :

```json
{
  "schema_version": "1.0",
  "mapping": {
    "STAT-001": { "endpoints": ["/nba-stats/player/stats/basic"] },
    "LIVE-008": { "endpoints": ["/combined/coach/h2h"] }
  }
}
```

**Règle de propagation** : par défaut, la règle est `or` (implicite, ne pas écrire le champ). Quand un `id` est mappé vers plusieurs endpoints, la hiérarchie OR s'applique : le meilleur statut parmi les endpoints l'emporte. Hiérarchie : `validated` > `validated_slow` > `unreliable_upstream` > `bugged_parsing` > `blocked_no_source`.

Pour les rares cas où **tous** les endpoints doivent être OK pour que la ligne soit considérée validée, ajouter `"propagation": "and"` :

```json
"H2H-002": {
  "endpoints": ["/nba-stats/h2h/quarter-scores", "/nba-stats/h2h/totals"],
  "propagation": "and"
}
```

Aucun cas `"and"` n'existe dans le mapping au 2026-05-20. Le mécanisme est implémenté dans `sync_dashboard.py` (`resolve_status`) et prêt à l'emploi.

## 8. Cas ambigus et décisions d'arbitrage

Convention : chaque cas est daté pour traçabilité. Les futurs cas s'ajoutent à la suite.

### 2026-05-20 — `blocked_no_source` vs `bugged_parsing`

Lors de la migration `poc_status → audit_status` (Phase 2), les lignes anciennement `bloqué` devaient être départagées entre `blocked_no_source` (pas de source gratuite) et `bugged_parsing` (endpoint existe mais le parsing échoue). L'arbitrage a été fait manuellement ligne par ligne. L'heuristique automatique du script de migration (`classify_bloque` dans `scripts/migrate_split_status.py`) utilise des signaux comme `cout="freemium"`, `"$"` dans les notes, ou `fournisseur` contenant `"scraping"` / `"balldontlie"`. Cette heuristique est **fragile** — le signal stable serait de chercher `fournisseur` contenant "scraping NBA Injury Report" ou "BallDontLie injuries" plutôt que des mots-clés monétaires dans les notes. À retenir pour de futurs scripts de migration ou d'arbitrage automatique.

### 2026-05-20 — Endpoints `/combined/*` traités comme `degraded` by-design

Les ~10 lignes mappées vers des endpoints `/combined/*` produisent des données agrégées sans double-validation côté source officielle. Décision produit : `data_status: degraded` même si l'audit technique passe (`audit_status: validated`). Ce n'est pas un bug — c'est la distinction que le modèle 3 axes est conçu pour capturer.

### 2026-05-20 — Heuristique `cout` + `$` pour arbitrage automatique

Le script `migrate_split_status.py` utilise `cout ∈ {freemium, payant}` et la présence de `$`, `9.99`, `paid`, `plan` dans les notes pour classifier automatiquement un `bloqué` en `blocked_no_source`. Ce signal monétaire est un proxy indirect — un endpoint peut être gratuit mais bloqué pour d'autres raisons, ou payant mais fonctionnel en free tier. Le signal structurel (`fournisseur` = BDL injuries, scraping hors BBRef) est plus fiable. Les deux coexistent dans le script actuel ; en cas de refactoring, privilégier le signal structurel.
