# SCHEMA.md — Sémantique des champs dashboard

> Référence figée. Toute modification de valeur admise passe par ce fichier, jamais par le code.

---

## Note de transition V1 → V2

Le champ unique `poc_status` (V1) est **supprimé** et éclaté en deux axes disjoints :

- **`audit_status`** — résultat technique de l'audit automatique (alimenté par `sync_dashboard.py`).
- **`data_status`** — état produit de la donnée (alimenté manuellement via l'UI + `apply_patch.py`).

Le troisième axe **`data_quality`** est inchangé depuis V1.

**Raison** : `poc_status` mélangeait deux informations orthogonales — "l'endpoint marche-t-il techniquement ?" et "la donnée est-elle exploitable côté produit ?". L'éclatement permet de synchroniser automatiquement les résultats d'audit sans écraser les décisions produit manuelles.

Table de migration `poc_status` → (`audit_status`, `data_status`) : voir `IMPLEMENTATION.md`, section "Schémas cibles".

L'ancienne sémantique `poc_status` est archivée en fin de document (section "Historique V1").

---

## 3 axes de statut

Les 3 axes sont **disjoints** : chacun a sa propre grille de valeurs, son propre flux d'alimentation, et ne doit jamais être fusionné avec un autre dans un graphique ou un compteur.

### `audit_status`

Résultat technique de l'audit automatique. Langue : **anglais** (cohérent avec les valeurs produites par `audit.tool`). Alimenté **uniquement** par `sync_dashboard.py` — non éditable via l'UI.

| Valeur | Définition |
|--------|-----------|
| `null` | **Défaut.** Endpoint pas encore audité. |
| `validated` | Endpoint testé, HTTP 200, données parsées correctement, latence acceptable (< 5 s). |
| `validated_slow` | Endpoint fonctionnel, assertions OK, mais latence > 5 s. Cache long requis en relais. |
| `bugged_parsing` | Endpoint répond (HTTP 200) mais le parsing échoue ou produit des données incohérentes. Bug à fixer côté backend. |
| `unreliable_upstream` | Endpoint parfois OK, parfois en erreur (timeout, 5xx intermittent). Source amont instable. |
| `blocked_no_source` | Aucune source gratuite disponible pour cet endpoint. Endpoint payant ou inexistant. |

**Exemples :**
- Ligne 6 (Minutes prévues par joueur) — audit OK, HTTP 200, latence < 1 s → `validated`
- Ligne 74 (Historique coach vs coach) — fonctionnel mais ~9 s de latence warm → `validated_slow`
- Ligne 1 (Statut injury) — BDL paid plan requis, pas d'alternative gratuite → `blocked_no_source`

### `data_status`

État produit de la donnée. Langue : **anglais**. Alimenté **manuellement** via l'édition inline du dashboard + `apply_patch.py`. Jamais touché par `sync_dashboard.py`.

| Valeur | Définition |
|--------|-----------|
| `not_implemented` | **Défaut.** Endpoint pas encore codé ou pas encore testé côté produit. |
| `live` | Donnée exploitable en production. Endpoint codé, testé, résultat conforme aux attentes produit. |
| `degraded` | Donnée exploitable mais avec limitations connues (pas de double-validation, couverture partielle, source unique non croisée). |
| `deferred_v2` | Retiré du périmètre V1 par décision produit. À reprendre en V2. |
| `blocked_no_source` | Non fournissable — aucune source gratuite disponible. Décision produit de ne pas investir. |

**Exemples :**
- Ligne 7 (Rotation du coach) — endpoint codé, validé, exploitable → `live`
- Ligne 60 (Score H2H playoffs) — valeur récupérée mais non croisée avec source officielle → `degraded`
- Ligne 1 (Statut injury) — BDL paid plan, pas d'alternative → `blocked_no_source`

### `data_quality`

Qualité de la donnée observée lors du test. Inchangé depuis V1.

| Valeur | Définition |
|--------|-----------|
| `unknown` | **Défaut.** Pas encore évalué. |
| `juste` | Donnée identique à nba.com (écart 0%). |
| `approximatif` | Donnée proche mais pas identique à la source de vérité (arrondi, délai, etc.). |
| `incomplet` | Donnée partielle : champs manquants, couverture incomplète. |

**Exemples :**
- Score final récupéré = score nba.com → `juste`
- Stat avancée avec arrondi différent de nba.com → `approximatif`
- Boxscore sans les OT → `incomplet`

---

## `vague`

Vague de livraison de la donnée. Détermine le cycle de PoC dans lequel la ligne sera traitée.

| Valeur | Définition |
|--------|-----------|
| `V1` | **Périmètre initial.** Données fondamentales validées et livrées au premier cycle de PoC. |
| `V2` | **Deuxième cycle.** Données complémentaires intégrées après la clôture de V1. |
| `V3` | **Troisième cycle.** Données avancées ou nécessitant des sources additionnelles. |
| `V4` | **Quatrième cycle.** Données à coût ou complexité élevée, repoussées des cycles précédents. |
| `V5` | **Phase payante.** Données dont l'accès gratuit est confirmé impossible. Réservées pour une phase commerciale ultérieure. Peuvent être repoussées en V6 si une donnée gratuite manquante émerge lors de l'intégration UI. |

---

## ID stables `CAT-NNN`

Identifiant stable et lisible attribué à chaque ligne du dashboard. Introduit en V2 à côté du `num` historique (1-163) qui est préservé.

**Format** : `{PREFIXE}-{NNN}` — préfixe catégorie (2-4 lettres majuscules) + numéro séquentiel 3 chiffres zéro-padded.

**Numérotation** : séquentielle dans chaque catégorie, par ordre d'apparition dans `data/dashboard.json`. Première ligne d'une catégorie = `001`.

### 12 préfixes

| Préfixe | Catégorie | Lignes |
|---------|-----------|--------|
| `ROST` | Roster & Disponibilité | 14 |
| `RES` | Résultats & Matchs | 12 |
| `CLAS` | Classement & Standings | 13 |
| `PACE` | Rythme & Pace | 14 |
| `H2H` | Confrontations directes (H2H) | 10 |
| `FAT` | Fatigue & Voyage | 8 |
| `STYL` | Style de jeu & Coach | 15 |
| `DEF` | Défense individuelle | 5 |
| `STAT` | Stats Joueur | 41 |
| `LIVE` | Live | 17 |
| `ARB` | Arbitres | 4 |
| `BET` | Paris & Cotes | 10 |

**Exemples** : `ROST-001` (Statut injury), `STAT-012` (PER par joueur), `LIVE-005` (Score live en cours).

---

## `validation_note`

Texte libre ≤ 200 caractères. Contexte minimal pour reproduire ou comprendre le test.

**Format recommandé :** `game_id=XXXXXXXXX, écart X%, vs nba.com` ou `endpoint non dispo en free tier`.

**Exemples :**
- `"game_id=0022400123, écart 0%, vs nba.com"`
- `"BDL /player_injuries = ALL-STAR plan uniquement (9.99$/mo)"`
- `"USG% arrondi à 2 décimales vs 1 sur nba.com"`

---

## `last_updated`

Format ISO 8601, auto-rempli par le frontend à chaque modification et par `sync_dashboard.py` à chaque sync. Ne jamais renseigner à la main.

**Exemple :** `"2026-05-12T08:11:18.832954+00:00"`

Valeur initiale : `null` (jamais touché).

---

## Historique V1 — `poc_status` (supprimé)

> Champ supprimé en V2. Conservé ici pour traçabilité. Ne plus utiliser dans le code.

État de la donnée dans le cycle de PoC V1. Éclaté en `audit_status` + `data_status` en V2.

| Valeur | Définition |
|--------|-----------|
| `non_testé` | **Défaut.** Jamais touché, aucun test effectué. |
| `validé` | Testé et confirmé OK contre la source de vérité (nba.com ou équivalent). |
| `validated_slow` | Fonctionnel, toutes assertions passent, mais latence > 5 s. Cache long requis en relais. |
| `dégradé` | Exploitable mais sans double-validation : donnée probablement juste, pas confirmée. |
| `bloqué` | Non fournissable en gratuit — endpoint payant ou inexistant. |
| `out_of_scope` | Retiré du périmètre du PoC courant, délibérément. |
| `skipped` | Test non exécuté pour cause technique (fixture manquante, environnement indisponible). Rerun nécessaire. |
| `reporté_V2` | Fonctionnalité retirée du scope V1 par décision archi, à reprendre en V2. |
