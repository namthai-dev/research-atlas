# Research Atlas

A local-first research source catalog. The first release imports arXiv bibliographic records, preserves each successful Atom API response locally, and lets you search and inspect your saved library.

## Requirements

- Python 3.11 or newer
- Network access to the arXiv API when importing a paper

## Install and run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. Enter a modern arXiv ID such as `2301.12345` or an abstract URL such as `https://arxiv.org/abs/2301.12345`. The dashboard only searches the papers already saved to your local catalog; it does not search arXiv itself.

Choose a different data directory by setting `RESEARCH_ATLAS_DATA_DIR` before starting the app:

```bash
RESEARCH_ATLAS_DATA_DIR="$HOME/research-atlas-data" .venv/bin/uvicorn app.main:app --reload
```

The default data directory is `data/` in the repository. It contains the SQLite catalog at `data/research_atlas.sqlite3` and exact arXiv Atom responses under `data/sources/arxiv/`. The paths are configurable; this user data is excluded from version control.

## API

- `GET /api/papers?q=<term>` — list saved records, optionally searching title, abstract, authors, and arXiv identifier.
- `POST /api/papers` — import a paper; JSON body: `{"source": "2301.12345"}`. Returns `201` for a new record and `200` when refreshing an existing record.
- `GET /api/papers/{arxiv_id}` — read a saved record by its stored arXiv identifier, including an archive path but not the raw XML.

Import accepts modern numeric arXiv IDs with four- or five-digit sequence numbers, optionally ending in a version such as `v2`, and secure `https://arxiv.org/abs/<id>` URLs. A versioned ID requests that exact source version; an unversioned ID follows arXiv's returned current version. A missing record returns `404`, invalid input returns `400`, and upstream or malformed-record failures return `502`.

## Source data and provenance

Research Atlas stores the bibliographic fields returned by the arXiv Atom API (title, authors, abstract, categories, published/updated dates, and DOI when present), the canonical arXiv URL, collection time, and a relative path to the exact Atom XML response. Structured metadata and source archives remain separate. Missing optional fields are shown as unavailable rather than inferred. A detail page indicates if an archive file has become unavailable.

Only arXiv API metadata is supported in this MVP. It does not download PDFs, bypass access controls, crawl sites, import IEEE sources, generate summaries or recommendations, draft papers, or provide charts, accounts, or remote hosting.

## Tests

```bash
.venv/bin/python -m pytest -q
```
