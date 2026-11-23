from pathlib import Path

from app.db import init_db
from app.models import Paper
from app.repository import get_paper, search_papers, upsert_paper


def make_paper(**overrides: object) -> Paper:
    values: dict[str, object] = {
        "arxiv_id": "2301.12345",
        "title": "A Study of Local Research",
        "authors": ["A. Author", "B. Researcher"],
        "abstract": "A careful study of reproducible research systems.",
        "categories": ["cs.IR", "cs.DL"],
        "published": "2023-01-23T00:00:00Z",
        "updated": "2023-02-01T00:00:00Z",
        "doi": "10.1234/example",
        "source_url": "https://arxiv.org/abs/2301.12345",
        "collected_at": "2026-11-23T10:00:00Z",
        "archive_path": "sources/arxiv/2301.12345.atom.xml",
    }
    values.update(overrides)
    return Paper(**values)  # type: ignore[arg-type]


def test_upsert_and_get_preserve_bibliographic_and_provenance_fields(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "catalog.sqlite3"
    init_db(db_path)

    expected = make_paper()
    upsert_paper(db_path, expected)

    assert get_paper(db_path, "2301.12345") == expected


def test_upsert_updates_existing_canonical_identifier(tmp_path: Path) -> None:
    db_path = tmp_path / "catalog.sqlite3"
    init_db(db_path)
    upsert_paper(db_path, make_paper())
    revised = make_paper(title="Updated title", collected_at="2026-11-24T10:00:00Z")

    upsert_paper(db_path, revised)

    assert get_paper(db_path, "2301.12345") == revised
    assert len(search_papers(db_path)) == 1


def test_search_matches_title_abstract_authors_and_identifier(tmp_path: Path) -> None:
    db_path = tmp_path / "catalog.sqlite3"
    init_db(db_path)
    paper = make_paper()
    upsert_paper(db_path, paper)

    assert search_papers(db_path, "local research") == [paper]
    assert search_papers(db_path, "reproducible systems") == [paper]
    assert search_papers(db_path, "Researcher") == [paper]
    assert search_papers(db_path, "2301.12345") == [paper]


def test_sql_like_search_text_is_treated_as_data(tmp_path: Path) -> None:
    db_path = tmp_path / "catalog.sqlite3"
    init_db(db_path)
    paper = make_paper()
    upsert_paper(db_path, paper)

    assert search_papers(db_path, "' OR 1=1 --") == []
    assert get_paper(db_path, paper.arxiv_id) == paper
