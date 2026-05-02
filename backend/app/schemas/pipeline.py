from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RunPipelineResponse(BaseModel):
    job_id: uuid.UUID


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    progress: int
    step: Optional[str]
    created_at: datetime
    sensor_id: Optional[str]
    metrica: Optional[str]
    error_msg: Optional[str]


class ReportResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    sensor_id: Optional[str]
    metrica: Optional[str]
    report_md: Optional[str]


class RuleItem(BaseModel):
    sensor_id: Optional[str]
    antecedente: str
    consecuente: str
    n_vars: int
    soporte: float
    confianza: float
    lift: float

    class Config:
        from_attributes = True


class RulesResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    total: int
    page: int
    page_size: int
    rules: list[RuleItem]
