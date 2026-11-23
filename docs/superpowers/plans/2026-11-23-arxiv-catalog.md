# ArXiv Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deliver a local-first Research Atlas MVP that imports arXiv papers, preserves their source Atom XML and bibliographic metadata, and supports local browse/search/detail views.

**Architecture:** A small FastAPI app serves HTML pages and JSON routes. A service normalizes identifiers, fetches/parses one arXiv Atom entry, archives the raw Atom response, then stores structured metadata and archive provenance in SQLite. Configuration centralizes the data directory; tests mock upstream HTTP.

**Tech Stack:** Python 3, FastAPI, SQLite via `sqlite3`, Jinja2 templates, `httpx` for upstream HTTP, pytest and FastAPI TestClient.

**Spec:** `docs/superpowers/specs/2026-11-23-arxiv-catalog-design.md`

## Global Constraints

- Use Python for application code, FastAPI for the web API, and SQLite for structured application data and metadata.
- Store downloaded or archived raw source files in the local filesystem; keep their paths and related metadata in SQLite.
- Keep the first implementation simple and suitable for a single-user, local-first workflow.
- Initial source-support priority: arXiv first, then IEEE; use APIs and Playwright crawler methods; find tool/website/archive sources.
- Preserve source URLs, titles, authors, publication dates, access/collection dates, and available identifiers (such as DOI) where applicable.
- Keep collected source files distinct from derived text, summaries, analyses, and drafts.
- Respect source access restrictions, copyright, and website terms. Prefer permitted APIs, open-access repositories, and user-provided documents. Avoid bypassing paywalls or access controls.
- Keep filesystem paths configurable; handle missing, malformed, or inaccessible source files gracefully.
- Validate external input at API boundaries and use parameterized database queries through the project's chosen database library.
- Keep secrets, local databases, downloaded research files, and other user data out of version control.
- Do not add PDF downloads, IEEE integration, generated summaries, recommendations, charts, authentication, or remote hosting in this MVP.

## Review Focus

- Malformed IDs or unrelated URLs must be rejected without network calls or database rows; cover in Task 2 parser/service input tests and Task 3 API tests.
- Upstream timeout, non-success response, malformed Atom, or no matching entry must not create a record or orphaned archive; cover with mocked service tests in Task 2.
- Duplicate imports must update one canonical record without producing duplicate rows or unsafe archive paths; cover in Task 2.
- Quotes and SQL-looking search text must be treated as data, not SQL; cover in Task 1 repository search tests.
- Missing optional fields and inaccessible/missing archive paths must render gracefully without inventing bibliographic values; cover in Task 3 API/detail tests and Task 4 template tests.

---

## File Structure

- `pyproject.toml` — package metadata, runtime and test dependencies, pytest configuration.
- `.gitignore` — exclude local database, archive data, and Python tooling artifacts.
- `app/__init__.py` — package marker.
- `app/config.py` — `Settings` dataclass and `get_settings()` for configurable data path.
- `app/db.py` — SQLite schema initialization and connection lifecycle.
- `app/models.py` — typed paper record representation.
- `app/repository.py` — parameterized paper insert/update, lookup, list, and local search.
- `app/arxiv.py` — identifier/URL validation, API fetch, Atom parsing, XML archival, and import orchestration.
- `app/main.py` — FastAPI app factory, HTML routes, and JSON API routes.
- `app/templates/index.html` — import/search form and paper list.
- `app/templates/paper.html` — bibliographic detail and provenance view.
- `tests/conftest.py` — temporary data directory, initialized app, and mocked HTTP fixtures.
- `tests/test_repository.py` — SQLite schema and parameterized search behavior.
- `tests/test_arxiv.py` — identifier handling, Atom parse, archive/import behavior, upstream errors.
- `tests/test_api.py` — JSON route validation, duplicate import, browse/detail behavior.
- `tests/test_pages.py` — dashboard and detail rendering, missing archive behavior.
- `README.md` — setup, config, API/UI usage, data/provenance behavior, and limits.

## Task 1: Project foundation and SQLite repository

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/models.py`
- Create: `app/db.py`
- Create: `app/repository.py`
- Create: `tests/conftest.py`
- Create: `tests/test_repository.py`

**Interfaces:**
- Produces `Settings(data_dir: Path)`, `get_settings() -> Settings`, `init_db(db_path: Path) -> None`, and a `Paper` dataclass with `arxiv_id`, `title`, `authors`, `abstract`, `categories`, `published`, `updated`, optional `doi`, `source_url`, `collected_at`, and `archive_path`.
- Repository functions: `upsert_paper(db_path: Path, paper: Paper) -> Paper`, `get_paper(db_path: Path, arxiv_id: str) -> Paper | None`, and `search_papers(db_path: Path, query: str = "") -> list[Paper]`.

- [x] **Step 1: Write repository tests** for schema initialization, insert and retrieval preserving each metadata field, duplicate canonical ID updating one row, and search matching title/abstract/authors/ID.
- [x] **Step 2: Run `pytest tests/test_repository.py -q`** and confirm it fails because the app/repository interfaces do not exist.
- [x] **Step 3: Add package metadata and configuration** with Python >=3.11, FastAPI, httpx, Jinja2, uvicorn, and pytest/test client dependencies; default `data_dir` is repository-relative `data/`, overridable by `RESEARCH_ATLAS_DATA_DIR`.
- [x] **Step 4: Implement model, schema, and repository** using SQLite stdlib and parameterized statements; initialize schema idempotently and index the canonical arXiv ID.
- [x] **Step 5: Run `pytest tests/test_repository.py -q`** and confirm all tests pass, including SQL-like input as plain query data.
- [x] **Step 6: Add `.gitignore` rules** for `data/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, and `*.py[cod]`.

## Task 2: arXiv API importer and source archive

**Files:**
- Create: `app/arxiv.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_arxiv.py`

**Interfaces:**
- Consumes Task 1 `Settings`, `Paper`, `init_db`, and `upsert_paper`.
- Produces `normalize_arxiv_id(value: str) -> str`, `parse_atom_entry(xml_bytes: bytes, requested_id: str) -> Paper`, and `import_arxiv(value: str, settings: Settings, *, client: httpx.Client | None = None) -> Paper`.

- [x] **Step 1: Write tests** for valid ID forms (`2301.12345`, `2301.12345v2`) and `https://arxiv.org/abs/2301.12345`, rejecting malformed IDs/unrelated URLs; parse metadata and optional DOI from an Atom fixture; reject no-entry, mismatched entry, malformed XML, HTTP errors and timeout; verify no row/archive on failure and one updated row on duplicate import.
- [x] **Step 2: Run `pytest tests/test_arxiv.py -q`** and confirm the tests fail before implementation.
- [x] **Step 3: Implement identifier normalization and Atom parsing** with the standard library XML parser; return a clear `ValueError` for invalid input/data and preserve optional metadata only when present.
- [x] **Step 4: Implement `import_arxiv`** to call `https://export.arxiv.org/api/query?id_list=<id>`, require a matching entry, save exact successful XML under `data_dir/sources/arxiv/<safe-id>.atom.xml`, set collection time and canonical URL, then upsert SQLite metadata; use an injectable httpx client for deterministic tests.
- [x] **Step 5: Run `pytest tests/test_arxiv.py -q`** and confirm all importer tests pass; check failures leave neither a row nor a partial archive.

## Task 3: FastAPI application and JSON API

**Files:**
- Create: `app/main.py`
- Create: `tests/test_api.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- `create_app(settings: Settings | None = None, *, http_client: httpx.Client | None = None) -> FastAPI` initializes DB and exposes `/api/papers` (GET with optional `q`, POST JSON `{"source": "..."}`), `/api/papers/{arxiv_id}` (GET); API responses include stored bibliographic and provenance fields but never inline raw XML.
- HTTP status behavior: 201 on new import, 200 on duplicate import, 400 invalid input, 404 no record/no upstream entry, and 502 upstream/network/parse failure.

- [x] **Step 1: Write API tests** for list/search, import status codes, malformed input/no network call, duplicate response without duplicate rows, detail 404, and upstream failure not persisted.
- [x] **Step 2: Run `pytest tests/test_api.py -q`** and confirm tests fail before routes exist.
- [x] **Step 3: Implement `create_app` and JSON endpoints** using the repository and importer interfaces; keep database and HTTP client injectable for tests and ensure application errors have safe, useful messages.
- [x] **Step 4: Run `pytest tests/test_api.py -q`** and confirm API tests pass.

## Task 4: Local dashboard and detail pages

**Files:**
- Create: `app/templates/index.html`
- Create: `app/templates/paper.html`
- Create: `tests/test_pages.py`
- Modify: `app/main.py`

**Interfaces:**
- Adds `GET /` HTML page with import field, local search field, and results; `GET /papers/{arxiv_id}` detail page.
- Page handlers share the same settings/repository/import service as JSON endpoints; forms submit to the API and show success/error text without frontend framework dependencies.

- [x] **Step 1: Write page tests** asserting dashboard form/search/list links; detail page bibliographic fields and source URL; graceful rendering for absent DOI and a missing archive path.
- [x] **Step 2: Run `pytest tests/test_pages.py -q`** and confirm they fail before templates/routes exist.
- [x] **Step 3: Implement the two server-rendered templates and HTML handlers** with auto-escaping, clear labels, simple responsive layout, and honest distinction between source facts/provenance and any non-existent derived analysis.
- [x] **Step 4: Run `pytest tests/test_pages.py -q`** and confirm all page tests pass.

## Task 5: Documentation and final verification

**Files:**
- Create: `README.md`

- [x] **Step 1: Document setup and run instructions** using the declared project tooling, `RESEARCH_ATLAS_DATA_DIR`, import/search usage, API routes, archive layout, and the MVP's local-only/source-support limits.
- [x] **Step 2: Run the full test suite** with `pytest -q` and confirm all tests pass.
- [x] **Step 3: Run formatting/lint checks if configured** and report the exact commands and results; do not add tools solely to create a check.
- [x] **Step 4: Inspect `git diff --check` and `git status --short`**; confirm there are no generated data files, databases, or archives in the patch.
