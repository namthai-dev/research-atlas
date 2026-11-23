from dataclasses import dataclass


@dataclass(frozen=True)
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published: str
    updated: str
    doi: str | None
    source_url: str
    collected_at: str
    archive_path: str
