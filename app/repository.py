import json
from pathlib import Path

from app.db import connect
from app.models import Paper


def _paper_from_row(row: object) -> Paper:
    return Paper(
        arxiv_id=row["arxiv_id"],
        title=row["title"],
        authors=json.loads(row["authors"]),
        abstract=row["abstract"],
        categories=json.loads(row["categories"]),
        published=row["published"],
        updated=row["updated"],
        doi=row["doi"],
        source_url=row["source_url"],
        collected_at=row["collected_at"],
        archive_path=row["archive_path"],
    )


def upsert_paper(db_path: Path, paper: Paper) -> Paper:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO papers (
                arxiv_id, title, authors, abstract, categories, published, updated,
                doi, source_url, collected_at, archive_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(arxiv_id) DO UPDATE SET
                title = excluded.title,
                authors = excluded.authors,
                abstract = excluded.abstract,
                categories = excluded.categories,
                published = excluded.published,
                updated = excluded.updated,
                doi = excluded.doi,
                source_url = excluded.source_url,
                collected_at = excluded.collected_at,
                archive_path = excluded.archive_path
            """,
            (
                paper.arxiv_id,
                paper.title,
                json.dumps(paper.authors),
                paper.abstract,
                json.dumps(paper.categories),
                paper.published,
                paper.updated,
                paper.doi,
                paper.source_url,
                paper.collected_at,
                paper.archive_path,
            ),
        )
    return paper


def get_paper(db_path: Path, arxiv_id: str) -> Paper | None:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        ).fetchone()
    return _paper_from_row(row) if row is not None else None


def search_papers(db_path: Path, query: str = "") -> list[Paper]:
    with connect(db_path) as connection:
        if query.strip():
            terms = query.split()
            conditions = " AND ".join(
                "(title LIKE ? OR abstract LIKE ? OR authors LIKE ? OR arxiv_id LIKE ?)"
                for _ in terms
            )
            parameters = tuple(
                f"%{term}%" for term in terms for _ in range(4)
            )
            rows = connection.execute(
                f"SELECT * FROM papers WHERE {conditions} ORDER BY published DESC, arxiv_id",
                parameters,
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM papers ORDER BY published DESC, arxiv_id"
            ).fetchall()
    return [_paper_from_row(row) for row in rows]
