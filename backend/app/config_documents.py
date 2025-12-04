from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_DEFAULT_STORAGE_PATH = "/app/storage/mission_documents"


@lru_cache(maxsize=1)
def get_mission_documents_storage_dir() -> Path:
    """Return the root directory where mission document uploads are stored."""

    base_path = os.getenv("APEX_MISSION_DOC_STORAGE", _DEFAULT_STORAGE_PATH)
    path = Path(base_path).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
