"""Root launcher for AeroPuzzle.

This keeps the legacy command `python app.py` working while the real
implementation lives under `src/aeropuzzle`.
"""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aeropuzzle.main import main


if __name__ == "__main__":
    main()