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
        data={"lift_minimo": "2.0", "k_beam": "5", "max_prof": "2"},
    )
    assert resp.status_code == 202


async def test_pipeline_run_acepta_modo_verbalizacion(http_client: AsyncClient):
    """POST /run con modo_verbalizacion='coloquial' debe devolver 202."""
    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
        data={"modo_verbalizacion": "coloquial"},
    )
    assert resp.status_code == 202
    assert "job_id" in resp.json()


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


# ── GET /{job_id}/image/{filename} ────────────────────────────────────────

async def test_image_endpoint_returns_png(http_client: AsyncClient, tmp_path, monkeypatch):
    """El endpoint de imágenes devuelve 200 con content-type image/png si el archivo existe."""
    from app.core.config import settings

    # Configurar upload_dir temporal
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    # Crear job
    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # Crear directorio del job y archivo PNG de prueba
    job_dir = tmp_path / job_id
    job_dir.mkdir(exist_ok=True)
    test_image = job_dir / "test_heatmap.png"
    test_image.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG header mínimo

    # Solicitar imagen
    resp = await http_client.get(f"/api/v1/pipeline/{job_id}/image/test_heatmap.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == b"\x89PNG\r\n\x1a\n"


async def test_image_endpoint_404_si_no_existe(http_client: AsyncClient, tmp_path, monkeypatch):
    """El endpoint de imágenes devuelve 404 si el archivo no existe."""
    from app.core.config import settings

    # Configurar upload_dir temporal
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    # Crear job
    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # Crear directorio del job (pero sin archivo)
    job_dir = tmp_path / job_id
    job_dir.mkdir(exist_ok=True)

    # Solicitar imagen inexistente
    resp = await http_client.get(f"/api/v1/pipeline/{job_id}/image/nonexistent.png")
    assert resp.status_code == 404
    assert "no encontrada" in resp.json()["detail"].lower()


async def test_image_endpoint_rechaza_path_traversal(http_client: AsyncClient, tmp_path, monkeypatch):
    """El endpoint de imágenes rechaza nombres de archivo con path traversal."""
    from app.core.config import settings

    # Configurar upload_dir temporal
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    # Crear job
    resp = await http_client.post(
        "/api/v1/pipeline/run",
        files={"file": _csv_file()},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # Intentar path traversal con ..
    # Nota: usamos %252E%252E para double-encode y que llegue literal ".."
    resp = await http_client.get(f"/api/v1/pipeline/{job_id}/image/%252E%252E/secret.png")
    assert resp.status_code == 400 or resp.status_code == 404  # 404 si FastAPI normaliza

    # Intentar path traversal con backslash (Windows)
    # El backslash no se normaliza en URLs, así que este test debería funcionar
    filename_with_backslash = "subdir\\file.png"
    resp = await http_client.get(f"/api/v1/pipeline/{job_id}/image/{filename_with_backslash}")
    assert resp.status_code == 400
    assert "inválido" in resp.json()["detail"].lower()
