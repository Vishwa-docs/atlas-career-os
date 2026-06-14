"""Pydantic v2 schemas for applications and their status timeline."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel
from app.domains.applications.models import APPLICATION_STATUSES


class ApplicationCreate(BaseModel):
    """Candidate applies to a job."""

    job_id: uuid.UUID
    cover_note: str | None = None


class ApplicationStatusUpdate(BaseModel):
    """Employer advances an application through the pipeline."""

    status: str
    note: str | None = None
    feedback: str | None = None


class ApplicationEventRead(ORMModel):
    """One immutable status-change event."""

    id: uuid.UUID
    from_status: str | None = None
    to_status: str
    note: str | None = None
    actor_id: uuid.UUID | None = None
    created_at: datetime


class ApplicationRead(ORMModel):
    """An application record."""

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    cover_note: str | None = None
    feedback: str | None = None
    source: str
    created_at: datetime
    updated_at: datetime


class CandidateSummary(BaseModel):
    """Lightweight candidate card shown to employers in the pipeline."""

    candidate_id: uuid.UUID
    user_id: uuid.UUID | None = None
    headline: str | None = None
    location: str | None = None
    years_experience: float | None = None


class JobSummary(BaseModel):
    """Lightweight job card shown to candidates in their applications list."""

    id: uuid.UUID
    title: str
    location: str | None = None
    work_mode: str
    seniority: str
    status: str
    org_id: uuid.UUID


class ApplicationDetail(BaseModel):
    """A candidate's application enriched with the job + event timeline."""

    application: ApplicationRead
    job: JobSummary | None = None
    events: list[ApplicationEventRead] = Field(default_factory=list)


class PipelineEntry(BaseModel):
    """One row of an employer's pipeline view for a job."""

    application: ApplicationRead
    candidate_summary: CandidateSummary | None = None
    events: list[ApplicationEventRead] = Field(default_factory=list)


# Re-exported so routers/services can validate against the canonical set.
VALID_STATUSES = set(APPLICATION_STATUSES)
