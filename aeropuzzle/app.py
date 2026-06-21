"""PyInstaller entrypoint wrapper for AeroPuzzle.

This file exists so `pyinstaller --onefile --windowed aeropuzzle/app.py`
can be used directly from the project root while the real application
logic remains in `src/aeropuzzle`.
"""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aeropuzzle.main import main


if __name__ == "__main__":
    main()