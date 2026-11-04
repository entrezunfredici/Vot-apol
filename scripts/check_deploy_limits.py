"""Vérifie les limites Cloudflare avant déploiement : < 20 000 fichiers, < 25 Mo par fichier."""

import sys
from pathlib import Path

MAX_FILES = 20_000
MAX_BYTES = 25 * 1024 * 1024


def main(root: str) -> int:
    files = [p for p in Path(root).rglob("*") if p.is_file()]
    biggest = max(files, key=lambda p: p.stat().st_size, default=None)
    size = biggest.stat().st_size if biggest else 0
    print(f"{len(files)} fichiers ; plus gros : {biggest} ({size} octets)")
    if len(files) >= MAX_FILES or size >= MAX_BYTES:
        print("Limite Cloudflare dépassée")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "web/dist"))
