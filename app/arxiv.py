import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import Settings
from app.db import init_db
from app.models import Paper
from app.repository import get_paper, upsert_paper

ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"
_ARXIV_ID_RE = re.compile(r"[0-9]{4}\.[0-9]{4,5}(?:v[1-9][0-9]*)?\Z")


class ImportNotFoundError(LookupError):
    """The arXiv API did not return the requested paper/version."""


def normalize_arxiv_id(value: str) -> str:
    candidate = value.strip()
    if candidate.startswith(("https://", "http://")):
        parsed = urlparse(candidate)
        if (
            parsed.scheme != "https"
            or parsed.netloc.lower() not in {"arxiv.org", "www.arxiv.org"}
            or parsed.path.count("/") != 2
            or not parsed.path.startswith("/abs/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Enter a valid arXiv identifier or https://arxiv.org/abs/ URL")
        candidate = parsed.path.removeprefix("/abs/")
    if not _ARXIV_ID_RE.fullmatch(candidate):
        raise ValueError("Enter a valid arXiv identifier or https://arxiv.org/abs/ URL")
    return candidate


def _entry_id(entry: ET.Element) -> str:
    identifier_url = entry.findtext(f"{{{ATOM_NS}}}id", default="")
    parsed = urlparse(identifier_url)
    if (
        parsed.scheme != "http"
        or parsed.netloc.lower() != "arxiv.org"
        or parsed.path.count("/") != 2
        or not parsed.path.startswith("/abs/")
        or parsed.query
        or parsed.fragment
    ):
        return ""
    candidate = parsed.path.removeprefix("/abs/")
    return candidate if _ARXIV_ID_RE.fullmatch(candidate) else ""


def parse_atom_entry(xml_bytes: bytes, requested_id: str) -> Paper:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("The arXiv API returned malformed Atom XML") from exc

    base_id = requested_id.split("v", 1)[0]
    entry = next(
        (
            candidate
            for candidate in root.findall(f"{{{ATOM_NS}}}entry")
            if _entry_id(candidate).split("v", 1)[0] == base_id
            and ("v" not in requested_id or _entry_id(candidate) == requested_id)
        ),
        None,
    )
    if entry is None:
        raise ImportNotFoundError(f"No arXiv record found for {requested_id}")

    actual_id = _entry_id(entry)
    authors = [
        name.text.strip()
        for author in entry.findall(f"{{{ATOM_NS}}}author")
        if (name := author.find(f"{{{ATOM_NS}}}name")) is not None
        and name.text
        and name.text.strip()
    ]
    categories = [
        category.get("term", "")
        for category in entry.findall(f"{{{ATOM_NS}}}category")
        if category.get("term")
    ]
    title = " ".join(entry.findtext(f"{{{ATOM_NS}}}title", default="").split())
    abstract = " ".join(entry.findtext(f"{{{ATOM_NS}}}summary", default="").split())
    published = entry.findtext(f"{{{ATOM_NS}}}published")
    updated = entry.findtext(f"{{{ATOM_NS}}}updated")
    if not title or not published or not updated:
        raise ValueError("The arXiv API record is missing required metadata")

    return Paper(
        arxiv_id=actual_id,
        title=title,
        authors=authors,
        abstract=abstract,
        categories=categories,
        published=published,
        updated=updated,
        doi=entry.findtext(f"{{{ARXIV_NS}}}doi"),
        source_url=f"https://arxiv.org/abs/{actual_id}",
        collected_at="",
        archive_path="",
    )


def import_arxiv(
    value: str,
    settings: Settings,
    *,
    client: httpx.Client | None = None,
) -> Paper:
    requested_id = normalize_arxiv_id(value)
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20.0, follow_redirects=False)
    try:
        response = http_client.get(
            "https://export.arxiv.org/api/query",
            params={"id_list": requested_id},
            headers={"User-Agent": "ResearchAtlas/0.1 (local research catalog)"},
        )
        response.raise_for_status()
        paper = parse_atom_entry(response.content, requested_id)
    finally:
        if owns_client:
            http_client.close()

    init_db(settings.db_path)
    archive_relative = Path("sources") / "arxiv" / f"{paper.arxiv_id}.atom.xml"
    data_root = settings.data_dir.resolve()
    archive_path = settings.data_dir / archive_relative
    try:
        archive_path.resolve().relative_to(data_root)
    except ValueError as exc:
        raise ValueError("Resolved archive path escapes the configured data directory") from exc
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = archive_path.with_suffix(archive_path.suffix + ".tmp")
    temporary_path.write_bytes(response.content)
    temporary_path.replace(archive_path)

    stored = Paper(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        authors=paper.authors,
        abstract=paper.abstract,
        categories=paper.categories,
        published=paper.published,
        updated=paper.updated,
        doi=paper.doi,
        source_url=paper.source_url,
        collected_at=datetime.now(UTC).isoformat(),
        archive_path=archive_relative.as_posix(),
    )
    try:
        upsert_paper(settings.db_path, stored)
    except Exception:
        if get_paper(settings.db_path, stored.arxiv_id) is None:
            archive_path.unlink(missing_ok=True)
        raise
    return stored
