#!/usr/bin/env python
"""
Repo-level manage.py proxy.
Delegates to ccc/astrobiology/backend/manage.py so root-level commands work.
"""
from pathlib import Path
import os
import runpy
import sys


def main() -> None:
    root = Path(__file__).resolve().parent
    backend_dir = root / "ccc" / "astrobiology" / "backend"
    backend_manage = backend_dir / "manage.py"

    if not backend_manage.exists():
        raise FileNotFoundError(f"Backend manage.py not found: {backend_manage}")

    os.chdir(str(backend_dir))
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    runpy.run_path(str(backend_manage), run_name="__main__")


if __name__ == "__main__":
    main()
