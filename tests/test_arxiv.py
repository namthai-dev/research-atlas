from pathlib import Path

import httpx
import pytest

from app.arxiv import import_arxiv, normalize_arxiv_id, parse_atom_entry
from app.config import Settings
from app.db import init_db
from app.repository import get_paper, search_papers

ATOM = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v2</id>
    <updated>2023-02-01T00:00:00Z</updated>
    <published>2023-01-23T00:00:00Z</published>
    <title>A Study of Local Research</title>
    <summary>A careful study of reproducible research systems.</summary>
    <author><name>A. Author</name></author>
    <author><name>B. Researcher</name></author>
    <category term="cs.IR" />
    <category term="cs.DL" />
    <arxiv:doi>10.1234/example</arxiv:doi>
  </entry>
</feed>'''


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2301.12345", "2301.12345"),
        ("2301.12345v2", "2301.12345v2"),
        ("https://arxiv.org/abs/2301.12345", "2301.12345"),
        ("https://arxiv.org/abs/2301.12345v2", "2301.12345v2"),
    ],
)
def test_normalize_arxiv_id_accepts_identifiers_and_abstract_urls(
    value: str, expected: str
) -> None:
    assert normalize_arxiv_id(value) == expected


@pytest.mark.parametrize(
    "value",
    ["", "2301.123", "2301.123456", "2301.12345v0", "../1234567", "https://example.com/abs/2301.12345"],
)
def test_normalize_arxiv_id_rejects_invalid_sources(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_arxiv_id(value)


def test_parse_atom_entry_preserves_metadata_and_exact_version() -> None:
    paper = parse_atom_entry(ATOM, "2301.12345v2")

    assert paper.arxiv_id == "2301.12345v2"
    assert paper.title == "A Study of Local Research"
    assert paper.authors == ["A. Author", "B. Researcher"]
    assert paper.abstract == "A careful study of reproducible research systems."
    assert paper.categories == ["cs.IR", "cs.DL"]
    assert paper.published == "2023-01-23T00:00:00Z"
    assert paper.updated == "2023-02-01T00:00:00Z"
    assert paper.doi == "10.1234/example"
    assert paper.source_url == "https://arxiv.org/abs/2301.12345v2"


def test_parse_atom_entry_keeps_optional_doi_absent() -> None:
    xml = ATOM.replace(b"    <arxiv:doi>10.1234/example</arxiv:doi>\n", b"")

    paper = parse_atom_entry(xml, "2301.12345")

    assert paper.doi is None
    assert paper.arxiv_id == "2301.12345v2"


def test_parse_atom_entry_rejects_malformed_xml() -> None:
    with pytest.raises(ValueError):
        parse_atom_entry(b"<feed><entry>", "2301.12345")


def test_parse_atom_entry_rejects_empty_feed() -> None:
    with pytest.raises(LookupError):
        parse_atom_entry(b'<feed xmlns="http://www.w3.org/2005/Atom" />', "2301.12345")


def test_parse_atom_entry_rejects_path_like_upstream_identifier() -> None:
    malicious_xml = ATOM.replace(
        b"2301.12345v2", b"2301.12345v2/../../outside"
    )

    with pytest.raises(LookupError):
        parse_atom_entry(malicious_xml, "2301.12345")


def test_parse_atom_entry_rejects_unicode_digits() -> None:
    unicode_id = "２３０１.１２３４５"
    with pytest.raises(ValueError):
        normalize_arxiv_id(unicode_id)


def test_parse_atom_entry_rejects_a_different_paper_or_requested_version() -> None:
    wrong_id = ATOM.replace(b"2301.12345v2", b"2301.99999v2")
    wrong_version = ATOM.replace(b"2301.12345v2", b"2301.12345v3")

    with pytest.raises(LookupError):
        parse_atom_entry(wrong_id, "2301.12345")
    with pytest.raises(LookupError):
        parse_atom_entry(wrong_version, "2301.12345v2")


def test_import_archives_exact_response_and_persists_record(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "data")
    init_db(settings.db_path)
    requested_urls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, content=ATOM)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        paper = import_arxiv("2301.12345", settings, client=client)

    assert len(requested_urls) == 1
    assert "id_list=2301.12345" in requested_urls[0]
    assert (settings.data_dir / paper.archive_path).read_bytes() == ATOM
    assert get_paper(settings.db_path, "2301.12345v2") == paper


def test_import_rejects_invalid_id_before_network_or_persistence(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "data")
    init_db(settings.db_path)
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=ATOM)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ValueError):
            import_arxiv("https://example.com/abs/2301.12345", settings, client=client)

    assert requests == []
    assert search_papers(settings.db_path) == []
    assert not (settings.data_dir / "sources" / "arxiv").exists()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503),
        httpx.Response(200, content=b"not xml"),
        httpx.Response(200, content=b'<feed xmlns="http://www.w3.org/2005/Atom" />'),
        httpx.Response(200, content=ATOM.replace(b"2301.12345v2", b"2301.99999v2")),
    ],
)
def test_import_upstream_errors_do_not_persist_or_archive(
    tmp_path: Path, response: httpx.Response
) -> None:
    settings = Settings(tmp_path / "data")
    init_db(settings.db_path)
    with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
        with pytest.raises((httpx.HTTPStatusError, ValueError, LookupError)):
            import_arxiv("2301.12345", settings, client=client)

    assert search_papers(settings.db_path) == []
    assert not (settings.data_dir / "sources" / "arxiv").exists()


def test_import_refuses_archive_directory_symlink_escape(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "data")
    init_db(settings.db_path)
    external_dir = tmp_path / "outside"
    external_dir.mkdir()
    source_dir = settings.data_dir / "sources"
    source_dir.mkdir(parents=True)
    (source_dir / "arxiv").symlink_to(external_dir, target_is_directory=True)

    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=ATOM))
    ) as client:
        with pytest.raises(ValueError, match="archive path"):
            import_arxiv("2301.12345", settings, client=client)

    assert list(external_dir.iterdir()) == []
    assert search_papers(settings.db_path) == []


def test_import_timeout_does_not_persist_or_archive(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "data")
    init_db(settings.db_path)

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("request timed out", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(httpx.TimeoutException):
            import_arxiv("2301.12345", settings, client=client)

    assert search_papers(settings.db_path) == []
    assert not (settings.data_dir / "sources" / "arxiv").exists()


def test_reimport_updates_the_exact_version_record(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "data")
    init_db(settings.db_path)
    newer = ATOM.replace(b"A Study of Local Research", b"A Revised Study")
    responses = iter([ATOM, newer])

    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=next(responses))
        )
    ) as client:
        import_arxiv("2301.12345v2", settings, client=client)
        updated = import_arxiv("2301.12345v2", settings, client=client)

    assert updated.title == "A Revised Study"
    assert get_paper(settings.db_path, "2301.12345v2") == updated
    assert len(search_papers(settings.db_path)) == 1
