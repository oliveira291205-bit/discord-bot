from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"


def main() -> None:
    os.chdir(ROOT)

    if Path(sys.executable).resolve() != VENV_PYTHON.resolve():
        if not VENV_PYTHON.exists():
            subprocess.check_call([sys.executable, "-m", "venv", str(ROOT / ".venv")])
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(__file__)])

    subprocess.check_call([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.check_call([str(VENV_PYTHON), "-m", "rei_suzukawa.bot"])


if __name__ == "__main__":
    main()
