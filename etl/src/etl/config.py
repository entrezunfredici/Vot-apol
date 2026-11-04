"""Configuration : chemins et URL source (variables d'environnement)."""

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("VOTEAPOL_DATA_DIR", "data"))
SOURCE_URL = os.environ.get("VOTEAPOL_SOURCE_URL", "")  # adresse officielle à vérifier (ALG-13)
