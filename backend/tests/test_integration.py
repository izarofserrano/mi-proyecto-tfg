"""Integration tests for the pipeline HTTP endpoints.

Uses the `http_client` fixture from conftest.py (in-memory SQLite + mocked pipeline).
All tests verify the HTTP contract: status codes, response shape, error handling.
"""
import io
import uuid

import pytest
from httpx import AsyncClient


# ── helpers ────────────────────────────────────────────────────────────────

def _csv_file(content: str = "id,fecha,intensidad\n1,2024-01-01,100\n"):
    return ("upload.csv", io.BytesIO(content.encode()), "text/csv")


# ── POST /run ──────────────────────────────────────────────────────────────

async def test_run_returns_202_and_uuid(http_client: AsyncClient):
    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    uuid.UUID(body["job_id"])  # raises ValueError if not a valid UUID


async def test_run_rejects_non_csv(http_client: AsyncClient):
    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 422


async def test_run_accepts_custom_mining_params(http_client: AsyncClient):
    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
        data={"min_lift": "2.0", "beam_width": "5", "max_vars": "2"},
    )
    assert resp.status_code == 202


# ── GET /{job_id}/status ───────────────────────────────────────────────────

async def test_status_returns_valid_response_after_submit(http_client: AsyncClient):
    run_resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    job_id = run_resp.json()["job_id"]

    resp = await http_client.get(f"/api/v1/pipeline/{job_id}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job_id
    assert body["status"] in {"pending", "running", "done", "error"}
    assert "progress" in body
    assert "step" in body


async def test_status_404_unknown_job(http_client: AsyncClient):
    resp = await http_client.get(f"/api/v1/pipeline/{uuid.uuid4()}/status")
    assert resp.status_code == 404


# ── GET /{job_id}/report ───────────────────────────────────────────────────

async def test_report_404_unknown_job(http_client: AsyncClient):
    resp = await http_client.get(f"/api/v1/pipeline/{uuid.uuid4()}/report")
    assert resp.status_code == 404


async def test_report_returns_pending_for_new_job(http_client: AsyncClient):
    run_resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    job_id = run_resp.json()["job_id"]

    resp = await http_client.get(f"/api/v1/pipeline/{job_id}/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job_id
    assert body["status"] in {"pending", "running", "done", "error"}


# ── GET /{job_id}/rules ────────────────────────────────────────────────────

async def test_rules_404_unknown_job(http_client: AsyncClient):
    resp = await http_client.get(f"/api/v1/pipeline/{uuid.uuid4()}/rules")
    assert resp.status_code == 404


async def test_rules_empty_list_for_new_job(http_client: AsyncClient):
    run_resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    job_id = run_resp.json()["job_id"]

    resp = await http_client.get(f"/api/v1/pipeline/{job_id}/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["rules"] == []
    assert body["page"] == 1


async def test_rules_invalid_page_returns_422(http_client: AsyncClient):
    run_resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    job_id = run_resp.json()["job_id"]

    resp = await http_client.get(f"/api/v1/pipeline/{job_id}/rules?page=0")
    assert resp.status_code == 422


async def test_rules_invalid_page_size_returns_422(http_client: AsyncClient):
    run_resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    job_id = run_resp.json()["job_id"]

    resp = await http_client.get(f"/api/v1/pipeline/{job_id}/rules?page_size=0")
    assert resp.status_code == 422


# ── API key auth ───────────────────────────────────────────────────────────

async def test_api_key_blocks_request_when_configured(
    http_client: AsyncClient, monkeypatch
):
    from app.core.config import settings
    monkeypatch.setattr(settings, "api_key", "secret-key-123")

    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    assert resp.status_code == 403


async def test_api_key_allows_request_with_correct_key(
    http_client: AsyncClient, monkeypatch
):
    from app.core.config import settings
    monkeypatch.setattr(settings, "api_key", "secret-key-123")

    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
        headers={"X-API-Key": "secret-key-123"},
    )
    assert resp.status_code == 202


async def test_api_key_disabled_when_empty(http_client: AsyncClient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "api_key", "")

    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    assert resp.status_code == 202
