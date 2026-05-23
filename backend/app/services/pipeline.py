from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from functools import partial
from pathlib import Path

import pandas as pd
from sqlalchemy import update

from app.core.fuzzy.heuristic import _detectar_var_tiempo, detectar_var_metrica
from app.core.fuzzy.pipeline import fuzzify
from app.core.mining.miner import BeamSearchMiner
from app.core.nlg.pipeline import generar_resumen
from app.core.preprocessing.splitter import split_by_sensor
from app.db.session import AsyncSessionLocal
from app.models.job import Job
from app.models.rule import Rule


# ── Sync helpers (run in thread-pool via run_in_executor) ─────────────────

def _get_all_sensor_paths(upload_path: str, work_dir: str) -> list[tuple[str, str]]:
    """Returns [(sensor_id, path)] for every sensor in the CSV.

    If the CSV has no 'id' column, the file is treated as a single-sensor dataset.
    Otherwise split_by_sensor() splits it and all per-sensor files are returned.
    """
    df = pd.read_csv(upload_path)

    if "id" not in df.columns:
        sensor_id = Path(upload_path).stem
        return [(sensor_id, upload_path)]

    sensor_paths = split_by_sensor(upload_path, work_dir)
    return [(Path(p).stem, p) for p in sorted(sensor_paths)]


def _run_fuzzify(sensor_path: str, tol_horas: float = 0.5) -> tuple[pd.DataFrame, str]:
    """Runs src01 and returns (fuzzy_df, metrica_col_name)."""
    from app.core.fuzzy.config import FuzzyConfig
    df_raw = pd.read_csv(sensor_path)

    # Detectar automáticamente la columna temporal (en vez de hardcodear "fecha")
    var_tiempo, df_raw = _detectar_var_tiempo(df_raw)
    if var_tiempo is None:
        raise ValueError("No se detectó columna temporal en el CSV. Especifica manualmente.")

    df_raw[var_tiempo] = pd.to_datetime(df_raw[var_tiempo])
    metrica = detectar_var_metrica(df_raw, var_tiempo)
    cfg = FuzzyConfig(tol_horas=tol_horas)
    fuzzy_df = fuzzify(sensor_path, var_tiempo=var_tiempo, config=cfg)
    return fuzzy_df, metrica


def _run_mining(
    fuzzy_df: pd.DataFrame,
    lift_minimo: float = 1.5,
    min_confianza: float = 0.5,
    min_soporte: float = 0.005,
    k_beam: int = 10,
    max_prof: int = 3,
) -> pd.DataFrame:
    """Runs src02 and returns rules DataFrame."""
    return BeamSearchMiner(
        lift_minimo=lift_minimo,
        min_confianza=min_confianza,
        min_soporte=min_soporte,
        k_beam=k_beam,
        max_prof=max_prof,
    ).fit(fuzzy_df)


def _run_nlg(rules_df: pd.DataFrame, sensor_id: str, metrica: str, modo: str = "tecnico") -> str:
    """Runs src03 and returns the Markdown report."""
    return generar_resumen(rules_df, sensor=sensor_id, metrica=metrica, modo=modo)


# ── Async DB helpers ──────────────────────────────────────────────────────

async def _set_status(
    db,
    job_id: uuid.UUID,
    status: str,
    progress: int,
    step: str,
) -> None:
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(status=status, progress=progress, step=step)
    )
    await db.commit()


async def _set_metadata(db, job_id: uuid.UUID, sensor_id: str, metrica: str | None) -> None:
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(sensor_id=sensor_id, metrica=metrica)
    )
    await db.commit()


async def _set_error(db, job_id: uuid.UUID, error_msg: str) -> None:
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(status="error", step="Error", error_msg=error_msg[:2000])
    )
    await db.commit()


async def _save_rules(
    db,
    job_id: uuid.UUID,
    sensor_id: str,
    rules_df: pd.DataFrame,
) -> None:
    if rules_df.empty:
        return
    rows = [
        Rule(
            job_id=job_id,
            sensor_id=sensor_id,
            antecedente=row["antecedente"],
            consecuente=row["consecuente"],
            n_vars=int(row["n_vars"]),
            soporte=float(row["soporte"]),
            confianza=float(row["confianza"]),
            lift=float(row["lift"]),
        )
        for _, row in rules_df.iterrows()
    ]
    db.add_all(rows)
    await db.commit()


def _cleanup_dir(dir_path: str | None) -> None:
    if dir_path and os.path.isdir(dir_path):
        try:
            shutil.rmtree(dir_path)
        except OSError:
            pass


# ── Main background task ──────────────────────────────────────────────────

async def execute_pipeline(
    job_id: uuid.UUID,
    upload_path: str,
    lift_minimo: float = 1.5,
    min_confianza: float = 0.5,
    min_soporte: float = 0.005,
    k_beam: int = 10,
    max_prof: int = 3,
    tol_horas: float = 0.5,
    modo_verbalizacion: str = "tecnico",
) -> None:
    """Full pipeline for ALL sensors: src00 → src01 → src02 → src03, persists to DB."""
    loop = asyncio.get_running_loop()
    work_dir = str(Path(upload_path).parent)

    async with AsyncSessionLocal() as db:
        try:
            await _set_status(db, job_id, "running", 5, "Detectando sensores…")
            sensors: list[tuple[str, str]] = await loop.run_in_executor(
                None, partial(_get_all_sensor_paths, upload_path, work_dir)
            )
            n = len(sensors)

            # (sensor_id, metrica, rules_df, report_md)
            results: list[tuple[str, str, pd.DataFrame, str]] = []

            for i, (sensor_id, sensor_path) in enumerate(sensors):
                base = 10 + 80 * i // n
                chunk = max(80 // n, 1)

                await _set_status(
                    db, job_id, "running",
                    base + chunk * 1 // 4,
                    f"[{i + 1}/{n}] {sensor_id}: fuzzificando…",
                )
                fuzzy_df, metrica = await loop.run_in_executor(
                    None, partial(_run_fuzzify, sensor_path, tol_horas)
                )

                await _set_status(
                    db, job_id, "running",
                    base + chunk * 2 // 4,
                    f"[{i + 1}/{n}] {sensor_id}: minando reglas…",
                )
                rules_df = await loop.run_in_executor(
                    None,
                    partial(_run_mining, fuzzy_df, lift_minimo, min_confianza,
                            min_soporte, k_beam, max_prof),
                )

                await _set_status(
                    db, job_id, "running",
                    base + chunk * 3 // 4,
                    f"[{i + 1}/{n}] {sensor_id}: generando informe…",
                )
                report_md = await loop.run_in_executor(
                    None, partial(_run_nlg, rules_df, sensor_id, metrica, modo_verbalizacion)
                )

                results.append((sensor_id, metrica, rules_df, report_md))

            await _set_status(db, job_id, "running", 92, "Guardando resultados…")

            for sensor_id, _, rules_df, _ in results:
                await _save_rules(db, job_id, sensor_id, rules_df)

            # Combine per-sensor reports
            if len(results) == 1:
                combined_report = results[0][3]
                all_sensor_ids = results[0][0]
                first_metrica: str | None = results[0][1]
            else:
                sections = [
                    f"## Sensor {sid} — {met}\n\n{rmd}"
                    for sid, met, _, rmd in results
                ]
                combined_report = "\n\n---\n\n".join(sections)
                all_sensor_ids = ", ".join(sid for sid, _, _, _ in results)
                first_metrica = results[0][1] if results else None

            await _set_metadata(db, job_id, all_sensor_ids, first_metrica)

            await db.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(status="done", progress=100, step="Completado", report_md=combined_report)
            )
            await db.commit()

        except Exception as exc:
            await _set_error(db, job_id, str(exc))

        finally:
            _cleanup_dir(work_dir)
