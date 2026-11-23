import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "research_atlas.sqlite3"

    @property
    def sources_dir(self) -> Path:
        return self.data_dir / "sources"


def get_settings() -> Settings:
    configured_dir = os.environ.get("RESEARCH_ATLAS_DATA_DIR")
    data_dir = (
        Path(configured_dir).expanduser()
        if configured_dir
        else Path(__file__).resolve().parent.parent / "data"
    )
    return Settings(data_dir=data_dir)
