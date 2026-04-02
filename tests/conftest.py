"""Root conftest.py — ensures repo root is on sys.path for all tests."""

import sys
from pathlib import Path

# Add the repo root so that `import wflib`, `import profiles`, `import adapters`
# work from any test file regardless of how pytest is invoked.
_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
