from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.db import init_db
from app.main import create_app
from app.models import Paper
from app.repository import upsert_paper


def make_paper(**overrides: object) -> Paper:
    values: dict[str, object] = {
        "arxiv_id": "2301.12345v2",
        "title": "A Study of Local Research",
        "authors": ["A. Author"],
        "abstract": "A careful study of reproducible research systems.",
        "categories": ["cs.IR"],
        "published": "2023-01-23T00:00:00Z",
        "updated": "2023-02-01T00:00:00Z",
        "doi": None,
        "source_url": "https://arxiv.org/abs/2301.12345v2",
        "collected_at": "2026-11-23T10:00:00Z",
        "archive_path": "sources/arxiv/2301.12345v2.atom.xml",
    }
    values.update(overrides)
    return Paper(**values)  # type: ignore[arg-type]


def test_dashboard_renders_local_search_and_paper_links(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "data")
    init_db(settings.db_path)
    upsert_paper(settings.db_path, make_paper())
    with TestClient(create_app(settings)) as client:
        response = client.get("/", params={"q": "reproducible"})

    assert response.status_code == 200
    assert 'name="source"' in response.text
    assert 'name="q"' in response.text
    assert "A Study of Local Research" in response.text
    assert "/papers/2301.12345v2" in response.text
    assert "Searches your saved library" in response.text


def test_detail_page_shows_provenance_and_handles_missing_metadata_and_archive(
    tmp_path: Path,
) -> None:
    settings = Settings(tmp_path / "data")
    init_db(settings.db_path)
    upsert_paper(settings.db_path, make_paper())
    with TestClient(create_app(settings)) as client:
        response = client.get("/papers/2301.12345v2")

    assert response.status_code == 200
    assert "A Study of Local Research" in response.text
    assert "A. Author" in response.text
    assert 'href="https://arxiv.org/abs/2301.12345v2"' in response.text
    assert "DOI not provided by arXiv" in response.text
    assert "Archive file is missing" in response.text
    assert "2026-11-23T10:00:00Z" in response.text


def test_detail_page_returns_404_for_unknown_paper(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(tmp_path / "data"))) as client:
        response = client.get("/papers/2301.12345")

    assert response.status_code == 404
