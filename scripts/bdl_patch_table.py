# scripts/bdl_patch_table.py
# Table de patch BDL — à relire manuellement avant intégration dans migrate.py.
#
# Contexte : BallDontLie a passé ses endpoints clés en payant.
# NBA Stats (nba_api) couvre la majorité des cas en gratuit.
#
# Ce fichier est importé par migrate.py — ne pas modifier la structure des dicts.

# ---------------------------------------------------------------------------
# 1. Lignes injury → poc_status = "bloqué"
#    Endpoints BDL injury (ALL-STAR 9.99$/mo) + SportsDataIO payants.
#    Aucune alternative gratuite fiable identifiée à ce stade.
# ---------------------------------------------------------------------------
INJURY_BLOCKED = [
    1,    # Statut injury par joueur (questionable / probable / doubtful / out)
    2,    # Five de départ officiel (annoncé 30-40 min avant le match)
    3,    # Liste joueurs confirmés absents
    4,    # Liste joueurs statut incertain
    5,    # Liste joueurs confirmés présents
    124,  # Historique des blessures — durée d'absence et stats au retour
]

# ---------------------------------------------------------------------------
# 2. Patches fournisseur : BallDontLie → NBA Stats
#    Toutes les lignes où BDL était utilisé mais NBA Stats couvre le besoin
#    en gratuit via nba_api (stats, boxscore, schedule, live).
#
#    Format : { num: {"fournisseur_old": "...", "fournisseur_new": "..."} }
# ---------------------------------------------------------------------------
FOURNISSEUR_PATCHES = {
    # --- Scores & résultats match (Pre-match) ---
    15: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    16: {"fournisseur_old": "BallDontLie",              "fournisseur_new": "NBA Stats"},
    17: {"fournisseur_old": "BallDontLie",              "fournisseur_new": "NBA Stats"},

    # --- Schedule & contexte match (Pre-match) ---
    18: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    19: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    22: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    24: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    64: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    67: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    70: {"fournisseur_old": "BallDontLie",              "fournisseur_new": "NBA Stats"},

    # --- Classements (Pre-match) ---
    27: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    28: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    38: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    39: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},

    # --- Confrontations directes H2H (Pre-match) ---
    54: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},
    55: {"fournisseur_old": "BallDontLie",              "fournisseur_new": "NBA Stats"},
    56: {"fournisseur_old": "BallDontLie + NBA Stats",  "fournisseur_new": "NBA Stats"},

    # --- Stats joueur avancées (Pre-match) ---
    96:  {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    104: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    105: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    112: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},

    # --- Live (nba_api.live gratuit couvre tous ces endpoints) ---
    147: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    148: {"fournisseur_old": "BallDontLie",             "fournisseur_new": "NBA Stats"},
    150: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    151: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    152: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    154: {"fournisseur_old": "BallDontLie",             "fournisseur_new": "NBA Stats"},
    156: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    157: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    158: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
    159: {"fournisseur_old": "BallDontLie + NBA Stats", "fournisseur_new": "NBA Stats"},
}
