import sys
from pathlib import Path

# Ensure the repository root (project/) is on sys.path so tests can import the
# local `custom_components` package without installing the integration.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# python -m venv .venv
# .venv\Scripts\activate
# python -m pip install --upgrade pip
# pip install pytest pytest-asyncio
# pytest -q tests/