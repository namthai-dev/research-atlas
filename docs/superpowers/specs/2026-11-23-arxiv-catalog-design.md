# ArXiv Catalog MVP Design

## Intent

Build the first useful Research Atlas slice for a single user: import an arXiv paper from its identifier or abstract URL, preserve the fetched source record locally, and browse/search the catalog. This establishes provenance and bibliographic storage before adding analysis or drafting features.

## Goals

- Provide a local FastAPI dashboard for importing, searching, and opening saved arXiv records.
- Preserve bibliographic metadata and the exact successful arXiv Atom API response separately from any future derived material.
- Keep SQLite metadata and archived source files under a configurable local data directory.
- Be usable and testable without live arXiv network access in the test suite.

## Non-goals / anti-goals

- No PDF downloading, IEEE integration, crawling, generated summaries, recommendations, charts, accounts, remote hosting, or paywall/access-control bypass.
- Do not fabricate missing metadata; preserve optional DOI and available identifiers only when supplied by arXiv.
- Do not commit the local database or downloaded/source archive files.

## Constraints

- Use Python, FastAPI, SQLite, and filesystem archives, consistent with `CLAUDE.md`.
- Treat arXiv API data as source material and keep raw Atom XML distinct from structured metadata.
- Validate user-provided identifiers at the application boundary and use parameterized SQLite statements.
- Keep the first implementation local-first and single-user.

## Approaches

1. **Whole-app scaffold first:** establish broad app infrastructure but defer a complete user workflow. Rejected because it produces little usable value and expands scope before validating the core storage flow.
2. **Storage/API only:** import and query papers through JSON endpoints. Smaller, but does not satisfy the stated dashboard goal or provide an immediately usable workflow.
3. **Narrow end-to-end arXiv catalog (chosen):** a small server-rendered dashboard calls FastAPI JSON endpoints, the service fetches the arXiv Atom API response, writes the raw response under the data directory, and stores searchable metadata plus its archive path in SQLite. This follows the project's source priority and proves the complete provenance path while excluding unrelated features.

## Proposed behavior

- Accept modern arXiv identifiers (`YYYY.NNNN` or `YYYY.NNNNN`, optionally versioned) and `https://arxiv.org/abs/<id>` URLs; reject unrelated URLs and malformed identifiers with a clear client error.
- Fetch one record through the arXiv Atom API. If there is no matching entry or the upstream request fails, report a useful error and do not create a catalog row.
- Store title, authors, abstract, categories, published/updated dates, DOI when present, canonical arXiv identifier, collection timestamp, source URL, and relative raw-archive path.
- A versioned identifier requests and stores that exact arXiv version; an unversioned identifier requests the current version returned by arXiv. Records are keyed by the returned versioned identifier, so distinct versions can coexist. Re-importing the same returned identifier updates its record/archive rather than creating a duplicate.
- Search saved records locally across title, abstract, authors, and identifier; show a list and a detail view with metadata and source/provenance. Do not imply that local search is a search of all arXiv.
- Use a configurable data directory (default `data/`), with SQLite at `data/research_atlas.sqlite3` and archives at `data/sources/arxiv/`.

## Implementation calls left to the builder

- Use the standard library XML parser for Atom and a small HTTP client dependency already declared in project metadata; test network behavior with a mocked transport.
- Use a compact HTML template and native browser form/fetch behavior rather than introducing a frontend framework.
- Add focused unit and API/UI tests; document installation, configuration, and local run commands.
