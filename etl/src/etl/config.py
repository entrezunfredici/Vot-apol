"""Configuration : chemins et URL source (variables d'environnement)."""

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("VOTEAPOL_DATA_DIR", "data"))
SOURCE_URL = os.environ.get("VOTEAPOL_SOURCE_URL", "")  # adresse officielle à vérifier (ALG-13)

# Adresses officielles vérifiées le 2026-11-14 (fiches ALG-13 et ALG-09) ; hôte unique autorisé.
URL_SCRUTINS = os.environ.get(
    "VOTEAPOL_URL_SCRUTINS",
    "https://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.json.zip",
)
URL_REFERENTIELS = os.environ.get(
    "VOTEAPOL_URL_REFERENTIELS",
    "https://data.assemblee-nationale.fr/static/openData/repository/17/amo/"
    "tous_acteurs_mandats_organes_xi_legislature/"
    "AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip",
)
# Racine publique des fichiers de données (ex. https://exemple.workers.dev/data/v1/) : vide = aucune
# comparaison avec une version publiée (exécution locale, première publication).
URL_PUBLIEE = os.environ.get("VOTEAPOL_URL_PUBLIEE", "")
