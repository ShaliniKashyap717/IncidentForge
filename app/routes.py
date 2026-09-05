"""API route declarations for IncidentForge."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_state_store_instance, get_workflow
from app.schemas import (
    EvidenceResponse,
    FindingsResponse,
    FullStateResponse,
    InvestigationCreateRequest,
    InvestigationListResponse,
    InvestigationSummaryResponse,
    RecommendationsResponse,
    TimelineResponse,
)
from orchestrator.workflow import IncidentWorkflow
from orchestrator.state_store import InvestigationStateStore

router = APIRouter()


def _to_summary_response(investigation_id: str, state_manager) -> InvestigationSummaryResponse:
    """Convert state manager to summary response."""
    summary = state_manager.get_status_summary()
    return InvestigationSummaryResponse(
        investigation_id=investigation_id,
        incident_id=summary["incident_id"],
        incident_title=summary["incident_title"],
        status=summary["status"],
        evidence_count=summary["evidence_count"],
        findings_count=summary["findings_count"],
        recommendations_count=summary["recommendations_count"],
        active_agents=summary["active_agents"],
        completed_agents=summary["completed_agents"],
        pending_tasks=summary["pending_tasks"],
        completed_tasks=summary["completed_tasks"],
    )


@router.post(
    "/investigations",
    response_model=InvestigationSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_investigation(
    request: InvestigationCreateRequest,
    workflow: IncidentWorkflow = Depends(get_workflow),
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> InvestigationSummaryResponse:
    """Create and run a new investigation."""
    investigation_id = str(uuid.uuid4())

    state_manager = await workflow.start(
        request.incident,
        request.context,
        use_llm=request.use_llm,
    )

    state_store.save(investigation_id, state_manager)

    return _to_summary_response(investigation_id, state_manager)


@router.get(
    "/investigations",
    response_model=InvestigationListResponse,
)
async def list_investigations(
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> InvestigationListResponse:
    """List all stored investigations with their summaries."""
    summaries = state_store.list_summaries()
    return InvestigationListResponse(
        investigations=[
            InvestigationSummaryResponse(**s) for s in summaries
        ]
    )


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationSummaryResponse,
)
async def get_investigation(
    investigation_id: str,
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> InvestigationSummaryResponse:
    """Get investigation status summary by ID."""
    state_manager = state_store.get(investigation_id)
    if state_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found",
        )
    return _to_summary_response(investigation_id, state_manager)


@router.get(
    "/investigations/{investigation_id}/state",
    response_model=FullStateResponse,
)
async def get_investigation_state(
    investigation_id: str,
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> FullStateResponse:
    """Get complete exported investigation state."""
    state_manager = state_store.get(investigation_id)
    if state_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found",
        )
    return FullStateResponse(**state_manager.export_state())


@router.get(
    "/investigations/{investigation_id}/timeline",
    response_model=TimelineResponse,
)
async def get_investigation_timeline(
    investigation_id: str,
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> TimelineResponse:
    """Get investigation timeline events."""
    state_manager = state_store.get(investigation_id)
    if state_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found",
        )
    return TimelineResponse(timeline=state_manager.timeline.get_events())


@router.get(
    "/investigations/{investigation_id}/evidence",
    response_model=EvidenceResponse,
)
async def get_investigation_evidence(
    investigation_id: str,
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> EvidenceResponse:
    """Get all evidence from the investigation."""
    state_manager = state_store.get(investigation_id)
    if state_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found",
        )
    return EvidenceResponse(evidence=state_manager.evidence_store.export_to_dict())


@router.get(
    "/investigations/{investigation_id}/findings",
    response_model=FindingsResponse,
)
async def get_investigation_findings(
    investigation_id: str,
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> FindingsResponse:
    """Get all findings from the investigation."""
    state_manager = state_store.get(investigation_id)
    if state_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found",
        )
    return FindingsResponse(findings=[f.model_dump(mode="json") for f in state_manager.findings])


@router.get(
    "/investigations/{investigation_id}/recommendations",
    response_model=RecommendationsResponse,
)
async def get_investigation_recommendations(
    investigation_id: str,
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> RecommendationsResponse:
    """Get all recommendations from the investigation."""
    state_manager = state_store.get(investigation_id)
    if state_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found",
        )
    return RecommendationsResponse(recommendations=[r.model_dump(mode="json") for r in state_manager.recommendations])