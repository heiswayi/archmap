"""PyInstaller entry point — uses an absolute import so it runs as a top-level
script (unlike archmap/__main__.py, which relies on relative imports)."""
from archmap.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
