from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.models.job import Job
from app.models.rule import Rule
from app.schemas.pipeline import (
    GlobalReportResponse,
    JobStatusResponse,
    ReportResponse,
    RulesResponse,
    RunPipelineResponse,
)
from app.services.pipeline import execute_pipeline
from app.core.global_report import generar_informe_global

router = APIRouter()


# ── POST /run ──────────────────────────────────────────────────────────────

@router.post("/run", response_model=RunPipelineResponse, status_code=202)
async def run_pipeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV del sensor (raw o ya dividido)"),
    lift_minimo: float = Form(1.5),
    min_confianza: float = Form(0.5),
    min_soporte: float = Form(0.005),
    k_beam: int = Form(10),
    max_prof: int = Form(3),
    tol_horas: float = Form(0.5),
    modo_verbalizacion: str = Form("tecnico"),
    db: AsyncSession = Depends(get_db),
) -> RunPipelineResponse:
    """Lanza el pipeline completo en segundo plano y devuelve un job_id."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=422, detail="El fichero debe ser un CSV.")

    job_id = uuid.uuid4()
    upload_dir = Path(settings.upload_dir) / str(job_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = str(upload_dir / "upload.csv")

    contents = await file.read()
    with open(upload_path, "wb") as fh:
        fh.write(contents)

    job = Job(
        id=job_id,
        status="pending",
        progress=0,
        step="En cola",
        created_at=datetime.now(tz=timezone.utc),
    )
    db.add(job)
    await db.commit()

    background_tasks.add_task(
        execute_pipeline,
        job_id, upload_path,
        lift_minimo, min_confianza, min_soporte, k_beam, max_prof, tol_horas,
        modo_verbalizacion,
    )

    return RunPipelineResponse(job_id=job_id)


# ── GET /{job_id}/status ───────────────────────────────────────────────────

@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    job = await _get_job_or_404(db, job_id)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        step=job.step,
        created_at=job.created_at,
        sensor_id=job.sensor_id,
        metrica=job.metrica,
        error_msg=job.error_msg if job.status == "error" else None,
    )


# ── GET /{job_id}/report ───────────────────────────────────────────────────

@router.get("/{job_id}/report", response_model=ReportResponse)
async def get_report(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    job = await _get_job_or_404(db, job_id)
    return ReportResponse(
        job_id=job.id,
        status=job.status,
        sensor_id=job.sensor_id,
        metrica=job.metrica,
        report_md=job.report_md,
    )


# ── GET /{job_id}/rules ────────────────────────────────────────────────────

@router.get("/{job_id}/rules", response_model=RulesResponse)
async def get_rules(
    job_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    sensor_id: Optional[str] = Query(None, description="Filtrar por sensor concreto"),
    db: AsyncSession = Depends(get_db),
) -> RulesResponse:
    if page < 1:
        raise HTTPException(status_code=422, detail="page debe ser ≥ 1.")
    if not (1 <= page_size <= 200):
        raise HTTPException(status_code=422, detail="page_size debe estar entre 1 y 200.")

    job = await _get_job_or_404(db, job_id)

    base_where = [Rule.job_id == job_id]
    if sensor_id:
        base_where.append(Rule.sensor_id == sensor_id)

    total_result = await db.execute(
        select(func.count()).where(*base_where)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    rules_result = await db.execute(
        select(Rule)
        .where(*base_where)
        .order_by(Rule.lift.desc())
        .offset(offset)
        .limit(page_size)
    )
    rules = rules_result.scalars().all()

    return RulesResponse(
        job_id=job.id,
        status=job.status,
        total=total,
        page=page,
        page_size=page_size,
        rules=rules,
    )


# ── GET /{job_id}/global-report ────────────────────────────────────────────

@router.get("/{job_id}/global-report", response_model=GlobalReportResponse)
async def get_global_report(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> GlobalReportResponse:
    """Genera informe global comparativo cross-sensor (src04)."""
    job = await _get_job_or_404(db, job_id)

    if job.status != "done":
        raise HTTPException(
            status_code=400,
            detail="Job no completado. El informe global solo está disponible para jobs completados."
        )

    # Directorio de datos del job
    upload_dir = Path(settings.upload_dir) / str(job_id)
    dir_datos = str(upload_dir)

    if not upload_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Directorio de datos del job no encontrado: {dir_datos}"
        )

    # Detectar sensores y métricas a partir de los CSVs de reglas disponibles
    import glob
    import re
    reglas_csvs = glob.glob(str(upload_dir / "*_reglas.csv"))

    if not reglas_csvs:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron CSVs de reglas. El pipeline debe completarse primero."
        )

    # Extraer (sensor, metrica) de los nombres de archivo: {sensor}_{metrica}_reglas.csv
    sensores_metricas = set()
    for csv_path in reglas_csvs:
        match = re.match(r"(.+)_(.+)_reglas\.csv$", Path(csv_path).name)
        if match:
            sensores_metricas.add((match.group(1), match.group(2)))

    sensores = sorted(set(s for s, _ in sensores_metricas))
    metricas = sorted(set(m for _, m in sensores_metricas))

    # Nombre del conjunto: usar sensor_id del job o "Dataset"
    nombre_conjunto = job.sensor_id or "Dataset"
    nombre_metrica_global = job.metrica or (metricas[0] if metricas else "métrica")

    # Generar el informe global
    resultado = generar_informe_global(
        sensores=sensores,
        metricas=metricas,
        dir_datos=dir_datos,
        nombre_conjunto=nombre_conjunto,
        nombre_metrica_global=nombre_metrica_global,
    )

    return GlobalReportResponse(
        job_id=job.id,
        status=job.status,
        global_report_md=resultado["informe_md"],
        n_sources=resultado["n_sources"],
        total_rules=resultado["total_rules"],
    )


# ── Helper ─────────────────────────────────────────────────────────────────

async def _get_job_or_404(db: AsyncSession, job_id: uuid.UUID) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} no encontrado.")
    return job
