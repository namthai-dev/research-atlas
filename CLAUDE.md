# Research Atlas

## Project purpose

Research Atlas is a personal research assistant for discovering and organizing internet sources, including articles and research papers. It should preserve source material and bibliographic details, help explore research trends, suggest topics based on the user's interests, and support drafting papers grounded in collected sources.

## Technology direction

- Use Python for application code.
- Use FastAPI for the web API.
- Use SQLite for structured application data and metadata.
- Store downloaded or archived raw source files in the local filesystem; keep their paths and related metadata in SQLite.
- Keep the first implementation simple and suitable for a single-user, local-first workflow unless requirements change.
- Initial source-support priority: arXiv (`https://arxiv.org/`) first, then IEEE (`https://ieeexplore.ieee.org/`). Keep source integrations extensible so additional sources can be added later. Use APIs and Playwright crawler methods; find tool/website/archive sources.

## Research integrity

- Preserve source URLs, titles, authors, publication dates, access/collection dates, and available identifiers (such as DOI) where applicable.
- Keep collected source files distinct from derived text, summaries, analyses, and drafts.
- Track provenance so claims, trend analysis, topic suggestions, and draft content can be traced back to their supporting sources.
- Clearly distinguish source facts from generated summaries or hypotheses; do not invent citations or bibliographic details.
- Respect source access restrictions, copyright, and website terms. Prefer permitted APIs, open-access repositories, and user-provided documents. Avoid bypassing paywalls or access controls.

## Development guidance

- Before implementing a feature, inspect the existing project structure and relevant files; follow established conventions.
- Prefer small, focused changes and avoid adding dependencies without a clear need.
- Keep filesystem paths configurable and handle missing, malformed, or inaccessible source files gracefully.
- Validate external input at API boundaries and use parameterized database queries through the project's chosen database library.
- Keep secrets, local databases, downloaded research files, and other user data out of version control. Add suitable ignore rules when initializing version control.
- Add focused tests for behavior changes and run the relevant project checks before reporting completion.
- Document setup, configuration, and operational decisions as the application grows.

## Intended application structure

The repository currently has no application source tree. Treat this as a proposed starting structure and update it as implementation choices are made:

- `app/main.py` — FastAPI application entry point.
- `app/api/` — HTTP routes for articles and dashboard data.
- `app/db/` — SQLite setup, schema, and data-access code.
- `app/services/` — Source collection, metadata handling, and chart data aggregation.
- `app/web/` — Dashboard templates and static assets; choose the rendering approach when frontend requirements are clearer.
- `data/sources/` — Local source archives; keep user data out of version control.
- `tests/` — Focused tests for API, storage, and source-handling behavior.

## Web dashboard goals

- Let the user browse, search, and filter collected articles, then open an article detail view with available bibliographic metadata and its source/provenance.
- Provide charts for research trends based on stored collection data. Make chart definitions and their underlying records traceable; do not present generated interpretations as source facts.
- Keep the dashboard local-first and make collection actions explicit. Decide specific import, annotation, or editing workflows before implementing them.

## Scope

Do not assume a specific frontend, hosting platform, crawler implementation, database ORM, or AI provider until the project requirements call for one. Discuss material trade-offs before making decisions that would significantly affect architecture, data handling, or research workflows.
