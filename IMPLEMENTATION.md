# IMPLEMENTATION.md — statspro-dashboard V2 (pipeline audit → dashboard)

> Plan d'exécution séquencé du pipeline audit → dashboard. Évolue au fil de l'implémentation.
> Pour les invariants (stack, archi, règles permanentes), voir `CLAUDE.md`.
> Plan V1 dashboard archivé en `docs/archive/IMPLEMENTATION-v1.md` (15/15 livrables, V1 close au 2026-05-20).

---

## Contexte de la phase

V1 dashboard close (édition inline + export JSON patch + `apply_patch.py` opérationnels, ~117 endpoints backend implémentés au 2026-05-20). Le patch manuel après chaque audit devient insoutenable avec la cadence d'audits V2 phase 1 sous-phase 1.2.

**Objectif V2 dashboard** : automatiser la synchronisation `audit.tool` → `dashboard.json` sans casser le workflow d'édition manuelle existant. Coexistence propre des deux flux (manuel via `apply_patch.py`, auto via `sync_dashboard.py`).

**Chantier cross-repo** : Phase 1 touche `statspro-backend` (fix bugs export `audit.tool` + ajout export JSON). Phases 2-5 vivent dans ce repo (`statspro-dashboard`). Le livrable backend est aussi listé dans l'IMPLEMENTATION.md V2 phase 1 de `statspro-backend` (sous-phase 1.4, livrable 18) pour traçabilité.

---

## Schémas cibles

> Schémas exacts à affiner au moment du Livrable correspondant — base de travail, pas contrat figé.

### `DashboardLine` cible (post-migration V2)

```ts
type DashboardLine = {
  // === Identifiants ===
  num: number;              // 1..163, identifiant V1 préservé
  id: string;               // "CAT-NNN", identifiant stable V2 (ex: "STAT-001")

  // === Champs descriptifs (inchangés depuis V1) ===
  categorie: string;
  donnee: string;
  type: "Pre-match" | "Live";
  scope: "Joueur" | "Match" | "Équipe" | "Ligue";
  faisabilite: "Une seule API" | "Combinaison" | "Aucune";
  fournisseur: string;
  endpoint: string;
  cout: "gratuit" | "freemium" | "payant" | "indéterminé";
  effort: "trivial" | "modéré" | "lourd" | "indéterminé";
  vague: "V1" | "V2" | "V3" | "V4";
  notes: string;
  api_source: string;

  // === 3 axes de statut (poc_status SUPPRIMÉ, éclaté) ===
  audit_status:             // alimenté UNIQUEMENT par sync_dashboard.py
    | "validated"
    | "validated_slow"
    | "bugged_parsing"
    | "unreliable_upstream"
    | "blocked_no_source"
    | null;                 // pas encore audité

  data_status:              // alimenté manuellement via UI + apply_patch.py
    | "live"
    | "degraded"
    | "not_implemented"
    | "deferred_v2"
    | "blocked_no_source";

  data_quality:             // inchangé V1, manuel
    | "juste"
    | "approximatif"
    | "incomplet"
    | "unknown";

  validation_note: string;  // ≤200 char, manuel

  // === Métadonnées ===
  last_updated: string | null;        // ISO 8601, écrit par UI ET par sync
  audit_duration_s?: number;          // optionnel, écrit par sync uniquement
};
```

### `audit_results.json` (produit par `audit.tool export --json`, livrable 3)

```json
{
  "schema_version": "1.0",
  "audited_at": "2026-05-19T14:07:15.739Z",
  "endpoints": [
    {
      "endpoint_path": "/nba-stats/classement/home-record",
      "audit_status": "validated",
      "latency_s": 0.42,
      "audited_at": "2026-05-19T14:07:15.739Z",
      "passes": [
        { "pass_number": 1, "http_status": 200, "elapsed_ms": 420, "error": null }
      ],
      "error_signature": null
    }
  ]
}
```

### `dashboard_mapping.json` (livrable 6)

```json
{
  "schema_version": "1.0",
  "mapping": {
    "STAT-001": { "endpoints": ["/nba-stats/foo"] },
    "LIVE-008": { "endpoints": ["/combined/coach/h2h"] },
    "H2H-002": { "endpoints": ["/a", "/b"], "propagation": "and" }
  }
}
```

### Table de migration `poc_status` → (`audit_status`, `data_status`)

| `poc_status` actuel | → `audit_status` | → `data_status` | Notes |
|---|---|---|---|
| `validé` (source unique) | `validated` | `live` | cas standard V1/V2 phase 1 |
| `validé` (`/combined/*` dégradé BDL) | `validated` | `degraded` | les 10 lignes `/combined/*` |
| `validated_slow` | `validated_slow` | `live` | #74 coach H2H (~9s warm) |
| `dégradé` | `validated` | `degraded` | si V1 existe encore ce statut |
| `bloqué` (pas de source gratuite) | `blocked_no_source` | `blocked_no_source` | lignes injuries V3 |
| `bloqué` (bug parsing à fixer) | `bugged_parsing` | `live` (cible) | **à arbitrer ligne par ligne** |
| `non_testé` | `null` | `not_implemented` | endpoint pas codé |
| `out_of_scope` | `null` | `deferred_v2` | décision produit |

---

## Phases

### Phase 1 — Fondation backend (1 session, repo `statspro-backend`)

> Préparer `audit.tool` pour produire un export JSON exploitable + fixer les 2 bugs export connus. Travail dans `statspro-backend/tools/audit/`, repo distinct, mais nécessaire au pipeline.

- [ ] Livrable 1 — Fix bug filtre export `audit.tool`
- [ ] Livrable 2 — Fix bug titre export `audit.tool`
- [ ] Livrable 3 — Commande `audit.tool export --json`

**Note de traçabilité** : ces 3 livrables sont aussi listés dans `statspro-backend/IMPLEMENTATION.md` sous-phase 1.4 (clôture V2 phase 1), livrable 18 "Outillage pipeline audit → dashboard". Une seule source de vérité du **plan d'exécution** : ce document. Le backend ne fait que tracer le rattachement.

✅ **Point de validation 1** : lancer `audit.tool export --json` sur les ~117 endpoints actuels, parser le JSON manuellement, vérifier `schema_version: "1.0"`, tous les endpoints avec `audit_status` ∈ grille EN, le filtre `--filter` produit bien un sous-ensemble du sans-filtre, le titre markdown reflète le compte filtré.

### Phase 2 — Sémantique + migration du modèle dashboard (1-2 sessions, ce repo)

> Patcher `docs/SCHEMA.md` (source de vérité sémantique) **AVANT** tout patch code. Puis ajouter les `id` stables et éclater `poc_status` en `audit_status` + `data_status` sur les 163 lignes.

- [ ] Livrable 4 — Patch `docs/SCHEMA.md` (3 axes statut + ID stables)
- [ ] Livrable 5 — Script `scripts/migrate_add_ids.py` (ajout champ `id: "CAT-NNN"`)
- [ ] Livrable 6 — Script `scripts/migrate_split_status.py` (éclatement `poc_status` → `audit_status` + `data_status`)
- [ ] Livrable 7 — Patch `scripts/migrate.py` (script de migration initial V1, mettre à jour pour initialiser les nouveaux champs sur de futures regen)
- [ ] Livrable 8 — Patch `scripts/apply_patch.py` (accepter les nouveaux champs `data_status` + refuser `audit_status` dans un patch manuel)

✅ **Point de validation 2** : `docs/SCHEMA.md` à jour, `data/dashboard.json` parseable, 163 lignes avec `id` unique conforme au préfixe, plus aucun `poc_status`, `audit_status` + `data_status` cohérents sur les ~117 lignes implémentées, cas ambigus arbitrés manuellement. Préservation vérifiée : `data_quality`, `validation_note`, `last_updated`, tous les autres champs intacts. `apply_patch.py` refuse silencieusement tout patch contenant `audit_status`.

### Phase 3 — Mapping + sync (1-2 sessions, ce repo)

> Câbler le mapping initial, écrire le script de sync idempotent avec rapport de cohérence intégré.

- [ ] Livrable 9 — Fichier `dashboard_mapping.json` initial à la racine
- [ ] Livrable 10 — Script `sync_dashboard.py` à la racine
- [ ] Livrable 11 — Module rapport de cohérence (intégré dans `sync_dashboard.py`)

✅ **Point de validation 3** : lancer `python sync_dashboard.py --audit ../statspro-backend/audit_results.json --dashboard ./data/dashboard.json --mapping ./dashboard_mapping.json` sur le run d'audit du 2026-05-19 16:07 (ou un run plus récent), vérifier que les lignes correspondantes récupèrent leur `audit_status` correctement, que `data_status` et `data_quality` sont intacts (`git diff` ne montre QUE des changements sur les champs de la whitelist), le rapport de cohérence signale les endpoints du run non encore mappés. Lancer 3 fois de suite → `dashboard.json` identique au byte près (idempotence).

### Phase 4 — Adaptation HTML (1 session, ce repo)

> Patcher `index.html` pour afficher et filtrer sur les 3 axes statut. Préserver l'édition inline existante.

- [ ] Livrable 12 — Patch `index.html` — filtres latéraux 3 axes
- [ ] Livrable 13 — Patch `index.html` — colonnes tableau + pills + KPIs sidebar
- [ ] Livrable 14 — Patch `index.html` — édition inline restreinte (`audit_status` non éditable)

✅ **Point de validation 4** : ouvrir le dashboard en local (`python -m http.server` à la racine), vérifier que les 3 filtres latéraux fonctionnent (Statut audit / Statut produit / Qualité donnée), que les compteurs sidebar reflètent la nouvelle grille, que les charts existants rendent (Faisabilité, Fournisseur, Matrice Coût×Effort, Catégorie×Faisabilité), que l'export JSON patch existant reste opérationnel, que `audit_status` n'apparaît pas comme champ éditable dans le mode édition inline. Aucune erreur console.

### Phase 5 — Documentation et clôture (½ session, ce repo)

> Documenter le pipeline pour relecture dans 3 mois + tag git de snapshot V2.

- [ ] Livrable 15 — `PIPELINE.md` à la racine (workflow d'usage)
- [ ] Livrable 16 — Patch `README.md` (mention du pipeline + lien vers PIPELINE.md)
- [ ] **Tag Git `v2.0` + snapshot `poc-pipeline-final`**

✅ **Point de validation 5** : Greg relit `PIPELINE.md` dans 1 semaine et comprend sans aller chercher dans la mémoire — workflow, ordre des commandes, où vit chaque fichier, comment ajouter une donnée nouvelle, comment patcher le mapping, mapping des 3 axes statut. Tag `v2.0` poussé.

---

## Livrables détaillés

1. **Fix bug filtre export `audit.tool`** — le flag `--filter` exporte effectivement les seuls endpoints correspondants. Test : run avec filtre + sans filtre, comptes distincts. `XS` *(repo backend)*
2. **Fix bug titre export `audit.tool`** — le titre du markdown reflète le compte filtré, pas le total. `XS` *(repo backend)*
3. **Commande `audit.tool export --json`** — produit `audit_results.json` machine-readable, `schema_version: "1.0"`, champs `endpoint_path` / `audit_status` / `latency_s` / `audited_at` / `passes` / `error_signature`. Mêmes flags de filtrage que l'export markdown. `S` *(repo backend)*
4. **Patch `docs/SCHEMA.md`** — section "3 axes de statut" avec définitions et exemples concrets, section "ID stables CAT-NNN" avec les 9 préfixes, note de transition expliquant la suppression de `poc_status`. `S`
5. **Script `scripts/migrate_add_ids.py`** — ajoute `id: "CAT-NNN"` à côté du `num` existant. Idempotent. Numérotation 3 chiffres avec zéro-padding. `XS`
6. **Script `scripts/migrate_split_status.py`** — éclate `poc_status` en `audit_status` + `data_status` selon la table de migration. Mode DRY-RUN par défaut, mode WRITE explicite. Liste les cas ambigus à arbitrer avant écriture. `M`
7. **Patch `scripts/migrate.py`** — la regen initiale doit produire les nouveaux champs (`audit_status: null`, `data_status: "not_implemented"`, etc.) au lieu de `poc_status: "non_testé"`. `XS`
8. **Patch `scripts/apply_patch.py`** — `PatchEntry` accepte `data_status`, refuse silencieusement `audit_status` avec warning. `XS`
9. **`dashboard_mapping.json` initial** — câblage des ~117 endpoints backend connus (V1 + V2 phase 1) vers leurs `id`. Reste laissé vide (`endpoints: []`). `M`
10. **Script `sync_dashboard.py`** — CLI Python, stdlib uniquement, whitelist `MANAGED_FIELDS = ["audit_status", "last_updated", "audit_duration_s"]`, règle propagation `or` par défaut, sortie JSON triée stable, idempotent. `L`
11. **Module rapport de cohérence** — intégré dans `sync_dashboard.py`, produit `sync_report_YYYYMMDD_HHMM.md` daté + stdout. Listes : endpoints audités non mappés, IDs mappés vers endpoints absents, doublons, IDs absents du `dashboard.json`. Non bloquant. `S`
12. **Patch `index.html` — filtres latéraux 3 axes** — renommer "Statut PoC" → "Statut audit", ajouter "Statut produit", préserver "Qualité donnée". Traduction EN→FR côté JS pour `audit_status`. `M`
13. **Patch `index.html` — colonnes tableau + pills + KPIs** — 3 colonnes au lieu d'1, pills colorées par axe, KPIs sidebar adaptés à la nouvelle grille, charts existants vérifiés (et patchés si référence à `poc_status`). `M`
14. **Patch `index.html` — édition inline restreinte** — le mode édition expose `data_status`, `data_quality`, `validation_note`. **Pas** `audit_status`. Auto-fill `last_updated`. `S`
15. **`PIPELINE.md`** — doc 1 page à la racine : workflow d'usage, ordre des commandes, fichiers du pipeline, mapping des 3 axes, ajouter une donnée nouvelle, patcher le mapping, cas ambigus connus. `S`
16. **Patch `README.md`** — section "Pipeline audit → dashboard" courte, lien vers `PIPELINE.md`, mise à jour du tableau de couverture. `XS`

---

## Dépendances critiques

- **Livrable 3 bloque Livrable 10** : sans `audit.tool export --json`, le script de sync n'a rien à lire.
- **Livrable 4 (SCHEMA.md) bloque Livrables 5, 6, 7, 8** : la sémantique doit être figée par écrit avant tout patch code. Règle du repo, pas négociable.
- **Livrables 5, 6 bloquent Livrable 9** : sans `id` figés sur les 163 lignes, le `dashboard_mapping.json` n'a pas de clés stables à référencer.
- **Livrables 5, 6 bloquent Livrables 12, 13, 14** : sans `audit_status` + `data_status` dans `dashboard.json`, le patch HTML n'a rien à afficher.
- **Livrable 10 est le pivot** : il porte toute la logique d'idempotence + propagation. Ne pas bâcler. Tests dédiés sur mini-fixture avant de tourner sur le vrai run.

---

## Garde-fous

- **Si la table de migration `poc_status` → (audit_status, data_status) révèle plus de 5 cas ambigus** non résolubles automatiquement → stop, arbitrer en séance avant de poursuivre. Ne pas trancher à la légère.
- **Si Phase 1 dépasse 1 session** → suspecter un problème de structure de `tools/audit/exporter.py`. Re-lire le code avant d'empiler les patches.
- **Si Phase 3 dépasse 2 sessions** → suspecter une dérive scope (ex: ajout de mode strict, gestion d'historique, etc. hors PROSIT). Recadrer sur la whitelist + idempotence + rapport, point.
- **Phase 4 ne doit jamais précéder Phase 2** : patcher le HTML avant que les champs existent dans le JSON = HTML qui crash silencieusement.
- **Si pendant la Phase 3 on découvre un cas où `or` ne suffit pas** → l'acter dans le mapping de la ligne concernée (`"propagation": "and"`), mais ne pas généraliser. Le 99% reste implicite `or`.
- **Si après Phase 4 un graphique ne rend plus** → rollback HTML, investiguer, ne pas patcher en aveugle. Le `dashboard.json` reste la source de vérité, le HTML doit s'y adapter.
- **Aucun framework JS, aucun build step, aucun runtime serveur** introduits en V2 dashboard, même si tentant pour le pipeline. Cohérent avec les invariants V1 préservés dans `CLAUDE.md`.
- **`apply_patch.py` et `sync_dashboard.py` ne doivent jamais s'appeler l'un l'autre.** Cohabitation propre, scripts indépendants.

---

## État d'avancement

Phase 1 : ⬜
Phase 2 : ⬜
Phase 3 : ⬜
Phase 4 : ⬜
Phase 5 : ⬜
