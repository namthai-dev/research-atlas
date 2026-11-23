from pathlib import Path

import pytest

from app.config import Settings
from app.db import init_db


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    result = Settings(data_dir=tmp_path / "data")
    init_db(result.db_path)
    return result
