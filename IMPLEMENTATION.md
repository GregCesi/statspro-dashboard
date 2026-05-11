# IMPLEMENTATION.md — statspro-dashboard

> Plan d'exécution séquencé. Évolue au fil de l'implémentation.
> Pour les invariants (stack, règles permanentes), voir `CLAUDE.md`.

---

## Schémas cibles

> Schémas exacts à affiner au moment du Livrable correspondant — base de travail, pas contrat figé.

### `DashboardLine` (une entrée de `data/dashboard.json`)

```ts
type DashboardLine = {
  // === Champs existants (inchangés, issus du HTML actuel) ===
  num: number;              // 1..163, identifiant stable
  categorie: string;        // ex: "Stats Joueur", "Live"
  donnee: string;           // description courte
  type: "Pre-match" | "Live";
  scope: "Joueur" | "Match" | "Équipe" | "Ligue";
  faisabilite: "Une seule API" | "Combinaison" | "Aucune";
  fournisseur: string;      // ex: "NBA Stats", "BallDontLie + Scraping"
  endpoint: string;         // endpoint(s) exact(s)
  cout: "gratuit" | "freemium" | "payant" | "indéterminé";
  effort: "trivial" | "modéré" | "lourd" | "indéterminé";
  vague: "V1" | "V2" | "V3" | "V4";
  notes: string;            // notes détaillées
  api_source: string;       // texte récapitulatif

  // === 3 nouveaux champs PoC ===
  poc_status:
    | "non_testé"           // défaut, jamais touché
    | "validé"              // testé OK contre la source de vérité
    | "dégradé"             // exploitable mais sans double validation prévue initialement
    | "bloqué"              // identifié comme non-fournissable en gratuit
    | "out_of_scope";       // retiré du périmètre

  data_quality:
    | "juste"               // donnée = nba.com (écart 0%)
    | "approximatif"        // donnée proche mais pas identique
    | "incomplet"           // donnée partielle (champs manquants)
    | "unknown";            // pas encore évalué

  validation_note: string;  // texte court ≤200 char, ex: "game_id=022400123, écart 0%, vs nba.com"

  // === Champ de traçabilité ===
  last_updated: string | null;  // ISO 8601, auto-rempli au frontend
};
```

### `PatchEntry` (forme du JSON patch exporté)

```ts
type PatchEntry = {
  num: number;                          // référence stable de la ligne
  poc_status?: DashboardLine["poc_status"];
  data_quality?: DashboardLine["data_quality"];
  validation_note?: string;
  last_updated: string;                 // ISO 8601, toujours présent
};

type PatchFile = {
  exported_at: string;                  // ISO 8601
  count: number;
  patches: PatchEntry[];
};
```

---

## Phases

### Phase 1 — Fondations (séquentiel, bloquant)
> Poser le repo, la sémantique gelée, et la table de patch BDL auditée avant tout scripting.

- [ ] Livrable 1 — Setup repo
- [ ] Livrable 3 — Table de patch BDL auditée
- [ ] Livrable 14 — `docs/SCHEMA.md`

✅ **Point de validation 1 :** la table patch BDL est complète (les ~22 lignes BDL à rebasculer + 6 injuries à passer en `bloqué` listées explicitement, validée contre `MEMORY.md`) **ET** la sémantique des 3 nouveaux champs est figée par écrit dans `docs/SCHEMA.md`. Si flou ici, tout l'aval dérive.

---

### Phase 2 — Migration des données (séquentiel)
> Produire `data/dashboard.json` à partir du `const DATA` actuel + patch BDL + champs PoC initialisés.

- [ ] Livrable 2 — Script `scripts/migrate.py`
- [ ] Livrable 4 — `data/dashboard.json` produit

✅ **Point de validation 2 :** ouverture manuelle du JSON, spot-check sur 10 lignes choisies stratégiquement (3 patches BDL, 2 injuries bloquées, 5 lignes non patchées). Alignement avec `MEMORY.md`. Une seule incohérence trouvée → retour Phase 1 pour patcher la table.

---

### Phase 3 — Bascule de la lecture (séquentiel court)
> Remplacer `const DATA = [...]` inline par un `fetch('./data/dashboard.json')`.

- [ ] Livrable 5 — Refacto `index.html` chargement JSON externe

✅ **Point de validation 3 :** non-régression visuelle stricte. Ancien et nouveau dashboard ouverts côte à côte affichent les mêmes charts, mêmes KPIs, mêmes filtres, même tableau (à 3 champs près non encore affichés). Si différence → fix avant de continuer.

---

### Phase 4 — Affichage des nouvelles colonnes (parallélisable)
> Rendre visible et filtrable les 2 nouveaux champs énumérés + nouveaux KPIs.

- [ ] Livrable 6 — Filtres sidebar `poc_status` + `data_quality`
- [ ] Livrable 7 — Colonnes tableau + pills colorées + affichage `validation_note` en détail
- [ ] Livrable 8 — KPIs PoC dans la kpi-bar

✅ **Point de validation 4 :** navigation usage typique "filtre `poc_status=validé` + tri par catégorie" donne un résultat lisible et juste. Filtres combinables avec les filtres existants sans casse.

---

### Phase 5 — Workflow d'édition (séquentiel, c'est le cœur)
> Permettre l'édition inline d'une ligne en < 30 sec, avec tampon localStorage et export JSON patch.

- [ ] Livrable 9 — Mode édition inline dans le tableau détail
- [ ] Livrable 10 — Indicateur "N modifs non exportées" dans le header
- [ ] Livrable 11 — Bouton "Exporter modifs en JSON patch"
- [ ] Livrable 12 — Bouton "Réinitialiser les modifs locales"

✅ **Point de validation 5 :** test end-to-end réel. Modifier 5 lignes en session, exporter le patch, coller dans `data/dashboard.json`, commit, rafraîchir le dashboard, vérifier que les 5 modifs sont persistées et que le localStorage est vidable proprement. Si une étape dépasse 1 min de friction → revoir l'UX du Livrable 9 ou 11.

---

### Phase 6 — Workflow IA (autonome)
> Permettre d'exporter une sélection filtrée vers un format consommable par Claude/Cowork.

- [ ] Livrable 13 — Export markdown + prompt template

✅ **Point de validation 6 :** test réel sur Cowork avec une sélection de 10 lignes `poc_status=bloqué`. Résultat actionnable (alternatives proposées + faisabilité argumentée + zéro hallucination d'endpoint) → V1 validée. Sinon, itérer **uniquement** sur le prompt template, pas sur le format.

---

### Phase 7 — Documentation et clôture
> Capitaliser le workflow réellement adopté et figer la V1.

- [ ] Livrable 15 — README opérationnel
- [ ] **Tag Git `v1.0` + snapshot `poc-1-final`**

---

## Livrables détaillés

1. **Setup repo `statspro-dashboard`** — repo Git initialisé avec README, structure dossiers (`/`, `data/`, `scripts/`, `exports/`, `docs/`), `.gitignore`, ouvrable en local. `XS`

2. **Script migration `scripts/migrate.py`** — extrait le `const DATA` du HTML actuel, applique la table de patch BDL, initialise les 3 nouveaux champs (`poc_status=non_testé`, `data_quality=unknown`, `validation_note=""`) + `last_updated=null`, écrit `data/dashboard.json`. `M`

3. **Table de patch BDL `scripts/bdl_patch_table.py`** — liste exhaustive des numéros de ligne à patcher avec ancien `fournisseur` → nouveau `fournisseur`, et liste des 6 injuries à passer en `poc_status=bloqué`. Relue manuellement avant intégration au script de migration. `S`

4. **`data/dashboard.json`** — produit du script de migration, 163 lignes complètes avec 3 nouveaux champs initialisés, ~22 lignes BDL patchées, 6 injuries marquées `bloqué`. Validé par diff manuel sur échantillon. `XS` (livrable produit)

5. **Refacto `index.html` — chargement JSON externe** — remplacer le `const DATA = [...]` inline par un `fetch('./data/dashboard.json').then(...)` qui boote le dashboard une fois les données chargées. Tout le reste intact. `S`

6. **Filtres sidebar `poc_status` + `data_quality`** — deux nouveaux groupes de filtres avec valeurs énumérées, intégrés au pipeline `applyFilters()` existant. `S`

7. **Colonnes tableau détail + pills colorées** — deux colonnes ajoutées au tableau principal avec pills, affichage de `validation_note` dans le bloc détail dépliable. `S`

8. **KPIs PoC dans la kpi-bar** — remplacer/compléter les KPIs actuels par des KPIs PoC : `% validé`, `% bloqué`, `% non_testé` sur le filtre courant. `XS`

9. **Mode édition inline tableau détail** — bouton "✎ éditer" sur la ligne détail dépliée, fait apparaître 2 selects (`poc_status`, `data_quality`) + input `validation_note`. Modifs stockées en `localStorage` sous clé `dashboard_edits_v1`. Auto-fill du `last_updated`. `M`

10. **Indicateur "N modifs non exportées"** — badge dans le header. Rouge si > 0, vert si 0. Clic = ouvre le panel export. `XS`

11. **Bouton "Exporter modifs en JSON patch"** — génère un snippet JSON (clé `num` + champs modifiés + `last_updated`). Copie auto dans le presse-papier + téléchargement de `patch_YYYYMMDD.json`. `S`

12. **Bouton "Réinitialiser les modifs locales"** — vider le localStorage proprement avec confirmation, après commit du patch. `XS`

13. **Bouton "Exporter pour IA" (markdown + prompt template)** — en plus de l'export CSV existant, génère un markdown structuré : entête contexte projet (figé) + sémantique des colonnes (figé) + 1 section par ligne filtrée + template de prompt en tête. `M`

14. **`docs/SCHEMA.md`** — document court qui définit sans ambiguïté chaque valeur de `poc_status` et `data_quality` avec 1-2 exemples concrets issus du PoC actuel, et le format attendu de `validation_note`. Référence pour relecture future. `S`

15. **README opérationnel** — comment ouvrir le dashboard en local, workflow type d'une session de test (load → modifier → exporter → coller dans JSON → commit), tag Git de snapshot en fin de cycle PoC. `XS`

---

## Dépendances critiques

- **Livrables 3 + 14 bloquent Livrable 2** — la table de patch BDL et la sémantique doivent être figées avant d'écrire le script de migration. Sinon on patche deux fois.
- **Livrable 2 bloque Livrable 4** — qui bloque toutes les phases 3-7.
- **Livrable 5 bloque les phases 4, 5, 6** — sans bascule JSON externe, rien d'autre ne peut s'appuyer dessus.
- **Livrable 9 bloque Livrables 10, 11, 12** — l'édition est le point d'entrée du workflow.
- **Livrable 11 bloque Livrable 12** — le reset ne fait sens qu'une fois l'export possible.

---

## Garde-fous

- Si une phase déborde > 1.5× son estimation `XS/S/M` → **stop, simplifier le scope**. Sur-conception probable.
- Si le workflow inline ne tient pas la promesse "< 30 sec par modif" au point de validation #5 → **retour aux pistes écartées** (édition Windsurf directe ou CLI Python) plutôt qu'empiler du polish UI sur le mode inline.
- Aucune nouvelle feature non listée ici ne s'ajoute en cours de chantier sans repasser par le PROSIT.
- Phase 4 et Phase 5 ne doivent **jamais** précéder Phase 3 — afficher les nouveaux champs avant la bascule JSON externe = double travail garanti.

---

## État d'avancement

Aucun livrable terminé à ce jour. Démarrage prévu : session Claude Code initiée depuis le premier prompt du kickoff.
