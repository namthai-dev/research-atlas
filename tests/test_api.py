from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

ATOM = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v2</id>
    <updated>2023-02-01T00:00:00Z</updated>
    <published>2023-01-23T00:00:00Z</published>
    <title>A Study of Local Research</title>
    <summary>A careful study of reproducible research systems.</summary>
    <author><name>A. Author</name></author>
    <category term="cs.IR" />
    <arxiv:doi>10.1234/example</arxiv:doi>
  </entry>
</feed>'''


def make_client(
    tmp_path: Path, response_body: bytes = ATOM, status_code: int = 200
) -> tuple[TestClient, list[httpx.Request]]:
    settings = Settings(tmp_path / "data")
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code, content=response_body)

    client = httpx.Client(transport=httpx.MockTransport(respond))
    return TestClient(create_app(settings, http_client=client)), requests


def test_list_and_search_return_saved_metadata(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        assert client.post("/api/papers", json={"source": "2301.12345"}).status_code == 201

        response = client.get("/api/papers", params={"q": "reproducible"})

        assert response.status_code == 200
        assert [paper["arxiv_id"] for paper in response.json()] == ["2301.12345v2"]
        assert "archive_path" in response.json()[0]
        assert "<?xml" not in response.text
    finally:
        client.close()


def test_import_returns_201_then_200_for_duplicate_record(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        first = client.post("/api/papers", json={"source": "2301.12345"})
        second = client.post("/api/papers", json={"source": "2301.12345"})

        assert first.status_code == 201
        assert second.status_code == 200
        assert first.json()["arxiv_id"] == "2301.12345v2"
        assert second.json()["arxiv_id"] == "2301.12345v2"
        assert len(client.get("/api/papers").json()) == 1
    finally:
        client.close()


def test_invalid_import_returns_400_without_network_request(tmp_path: Path) -> None:
    client, requests = make_client(tmp_path)
    try:
        response = client.post(
            "/api/papers", json={"source": "https://example.com/2301.12345"}
        )

        assert response.status_code == 400
        assert requests == []
        assert client.get("/api/papers").json() == []
    finally:
        client.close()


def test_detail_returns_404_for_unknown_record(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        response = client.get("/api/papers/2301.12345")

        assert response.status_code == 404
        assert response.json()["detail"] == "Paper not found"
    finally:
        client.close()


def test_upstream_http_failure_returns_502_without_record(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path, status_code=503)
    try:
        response = client.post("/api/papers", json={"source": "2301.12345"})

        assert response.status_code == 502
        assert client.get("/api/papers").json() == []
    finally:
        client.close()


def test_upstream_empty_feed_returns_404_without_record(tmp_path: Path) -> None:
    client, _ = make_client(
        tmp_path,
        response_body=b'<feed xmlns="http://www.w3.org/2005/Atom" />',
    )
    try:
        response = client.post("/api/papers", json={"source": "2301.12345"})

        assert response.status_code == 404
        assert client.get("/api/papers").json() == []
    finally:
        client.close()
