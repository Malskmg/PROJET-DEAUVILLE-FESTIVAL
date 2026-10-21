"""Point d'entrée de la ligne de commande."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def run() -> int:
    """Charger la CLI après configuration du chemin local."""
    from festival.cli.commands import main

    return main(default_data_path=PROJECT_ROOT / "data" / "festival.json")


if __name__ == "__main__":
    raise SystemExit(run())
