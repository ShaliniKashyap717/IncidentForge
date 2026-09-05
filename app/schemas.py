"""API request/response schemas for IncidentForge."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from models.incident import Incident


class InvestigationCreateRequest(BaseModel):
    """Request to create a new investigation."""

    incident: Incident
    context: dict[str, Any] = {}
    use_llm: bool = False


class InvestigationSummaryResponse(BaseModel):
    """Summary response for an investigation."""

    investigation_id: str
    incident_id: str
    incident_title: str
    status: str
    evidence_count: int
    findings_count: int
    recommendations_count: int
    active_agents: list[str]
    completed_agents: list[str]
    pending_tasks: list[str]
    completed_tasks: list[str]


class InvestigationListResponse(BaseModel):
    """Response for listing investigations."""

    investigations: list[InvestigationSummaryResponse]


class EvidenceResponse(BaseModel):
    """Response for evidence endpoint."""

    evidence: list[dict[str, Any]]


class FindingsResponse(BaseModel):
    """Response for findings endpoint."""

    findings: list[dict[str, Any]]


class RecommendationsResponse(BaseModel):
    """Response for recommendations endpoint."""

    recommendations: list[dict[str, Any]]


class TimelineResponse(BaseModel):
    """Response for timeline endpoint."""

    timeline: list[dict[str, Any]]


class FullStateResponse(BaseModel):
    """Response for full state export."""

    incident: dict[str, Any]
    status: str
    investigation_started_at: str
    evidence: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    active_agents: list[str]
    completed_agents: list[str]
    pending_tasks: list[str]
    completed_tasks: list[str]
    timeline: list[dict[str, Any]]