#!/usr/bin/env python3
"""Entry point: `python3 ghost.py <command>` (the shell hook defines a `ghost` function for it)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from revenant.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
