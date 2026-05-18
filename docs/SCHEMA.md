# SCHEMA.md — Sémantique des champs PoC

> Référence figée. Toute modification de valeur admise passe par ce fichier, jamais par le code.

---

## `poc_status`

État de la donnée dans le cycle de PoC courant.

| Valeur | Définition |
|--------|-----------|
| `non_testé` | **Défaut.** Jamais touché, aucun test effectué. |
| `validé` | Testé et confirmé OK contre la source de vérité (nba.com ou équivalent). |
| `dégradé` | Exploitable mais sans double-validation : donnée probablement juste, pas confirmée. |
| `bloqué` | Non fournissable en gratuit — endpoint payant ou inexistant. |
| `out_of_scope` | Retiré du périmètre du PoC courant, délibérément. |
| `skipped` | Test non exécuté pour cause technique (fixture manquante, environnement indisponible). Rerun nécessaire. |
| `reporté_V2` | Fonctionnalité retirée du scope V1 par décision archi, à reprendre en V2. |

**Exemples :**
- Ligne 15 (Score final) testée contre nba.com, écart 0% → `validé`
- Ligne 1 (Statut injury) : BDL paid plan requis, pas d'alternative gratuite → `bloqué`
- Ligne 96 (+/- par match) : valeur récupérée mais non croisée avec source officielle → `dégradé`

---

## `data_quality`

Qualité de la donnée observée lors du test.

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

## `validation_note`

Texte libre ≤ 200 caractères. Contexte minimal pour reproduire ou comprendre le test.

**Format recommandé :** `game_id=XXXXXXXXX, écart X%, vs nba.com` ou `endpoint non dispo en free tier`.

**Exemples :**
- `"game_id=0022400123, écart 0%, vs nba.com"`
- `"BDL /player_injuries = ALL-STAR plan uniquement (9.99$/mo)"`
- `"USG% arrondi à 2 décimales vs 1 sur nba.com"`

---

## `last_updated`

Format ISO 8601, auto-rempli par le frontend à chaque modification. Ne jamais renseigner à la main.

**Exemple :** `"2025-11-03T14:32:00.000Z"`

Valeur initiale : `null` (jamais touché).
