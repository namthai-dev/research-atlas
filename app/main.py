from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.arxiv import ImportNotFoundError, import_arxiv, normalize_arxiv_id
from app.config import Settings, get_settings
from app.db import init_db
from app.repository import get_paper, search_papers


class ImportRequest(BaseModel):
    source: str


def _paper_payload(paper: object) -> dict[str, object]:
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "categories": paper.categories,
        "published": paper.published,
        "updated": paper.updated,
        "doi": paper.doi,
        "source_url": paper.source_url,
        "collected_at": paper.collected_at,
        "archive_path": paper.archive_path,
    }


def create_app(
    settings: Settings | None = None,
    *,
    http_client: httpx.Client | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    init_db(app_settings.db_path)
    owns_client = http_client is None
    upstream_client = http_client or httpx.Client(timeout=20.0, follow_redirects=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        if owns_client:
            upstream_client.close()

    app = FastAPI(title="Research Atlas", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.http_client = upstream_client
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, q: str = "") -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"papers": search_papers(app_settings.db_path, q), "query": q},
        )

    @app.get("/papers/{arxiv_id}", response_class=HTMLResponse)
    def paper_page(request: Request, arxiv_id: str) -> HTMLResponse:
        paper = get_paper(app_settings.db_path, arxiv_id)
        if paper is None:
            raise HTTPException(status_code=404, detail="Paper not found")
        archive_path = (app_settings.data_dir / paper.archive_path).resolve()
        data_root = app_settings.data_dir.resolve()
        try:
            archive_path.relative_to(data_root)
            archive_exists = archive_path.is_file()
        except ValueError:
            archive_exists = False
        return templates.TemplateResponse(
            request=request,
            name="paper.html",
            context={"paper": paper, "archive_exists": archive_exists},
        )

    @app.get("/api/papers")
    def list_papers(q: Annotated[str, Query()] = "") -> list[dict[str, object]]:
        return [_paper_payload(paper) for paper in search_papers(app_settings.db_path, q)]

    @app.post("/api/papers")
    def add_paper(payload: ImportRequest, response: Response) -> dict[str, object]:
        try:
            requested_id = normalize_arxiv_id(payload.source)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        base_id = requested_id.split("v", 1)[0]
        existing = next(
            (
                paper
                for paper in search_papers(app_settings.db_path)
                if paper.arxiv_id.split("v", 1)[0] == base_id
                and ("v" not in requested_id or paper.arxiv_id == requested_id)
            ),
            None,
        )
        try:
            paper = import_arxiv(
                requested_id, app_settings, client=upstream_client
            )
        except ImportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail="Unable to fetch the arXiv record"
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=502, detail="The arXiv API returned an invalid record"
            ) from exc
        response.status_code = 200 if existing else 201
        return _paper_payload(paper)

    @app.get("/api/papers/{arxiv_id}")
    def paper_detail(arxiv_id: str) -> dict[str, object]:
        paper = get_paper(app_settings.db_path, arxiv_id)
        if paper is None:
            raise HTTPException(status_code=404, detail="Paper not found")
        return _paper_payload(paper)

    return app


app = create_app()
