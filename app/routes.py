"""API route declarations for IncidentForge."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_state_store_instance, get_workflow
from app.schemas import (
    EvidenceResponse,
    FindingsResponse,
    FullStateResponse,
    InvestigationCreateRequest,
    InvestigationListResponse,
    InvestigationSummaryResponse,
    RecommendationActionRequest,
    RecommendationActionResponse,
    RecommendationsResponse,
    ScenarioListResponse,
    ScenarioResponse,
    TimelineResponse,
)
from models.incident import Incident
from models.recommendation import RecommendationStatus
from orchestrator.workflow import IncidentWorkflow
from orchestrator.state_store import InvestigationStateStore
from scripts.load_scenarios import load_scenario, ScenarioLoadError

router = APIRouter()

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


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


@router.get(
    "/scenarios",
    response_model=ScenarioListResponse,
)
async def list_scenarios() -> ScenarioListResponse:
    """List all available scenario names."""
    scenario_names = []
    if SCENARIOS_DIR.exists():
        for entry in SCENARIOS_DIR.iterdir():
            if entry.is_dir() and (entry / "incident.json").exists():
                scenario_names.append(entry.name)
    return ScenarioListResponse(scenarios=sorted(scenario_names))


@router.get(
    "/scenarios/{name}",
    response_model=ScenarioResponse,
)
async def get_scenario(name: str) -> ScenarioResponse:
    """Load a scenario by name."""
    scenario_path = SCENARIOS_DIR / name
    if not scenario_path.exists() or not scenario_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{name}' not found",
        )
    try:
        scenario = load_scenario(scenario_path)
    except ScenarioLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ScenarioResponse(**scenario)


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
    """Create and run a new investigation.

    Either provide a scenario name (e.g., "payment_latency") OR provide incident + context manually.
    """
    investigation_id = str(uuid.uuid4())

    if request.scenario:
        # Load scenario using existing logic
        scenario_path = SCENARIOS_DIR / request.scenario
        if not scenario_path.exists() or not scenario_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario '{request.scenario}' not found",
            )
        try:
            scenario = load_scenario(scenario_path)
        except ScenarioLoadError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        incident = Incident.model_validate(scenario["incident"])
        context = {
            "incident": scenario["incident"],
            "logs": scenario["logs"],
            "metrics": scenario["metrics"],
            "traces": scenario["traces"],
            "deployments": scenario["deployments"],
            "commits": scenario["commits"],
        }
    else:
        # Manual mode: require incident
        if request.incident is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'scenario' or 'incident' must be provided",
            )
        incident = request.incident
        context = request.context

    state_manager = await workflow.start(
        incident,
        context,
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


@router.post(
    "/investigations/{investigation_id}/recommendations/{recommendation_index}/approve",
    response_model=RecommendationActionResponse,
)
async def approve_recommendation(
    investigation_id: str,
    recommendation_index: int,
    request: RecommendationActionRequest,
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> RecommendationActionResponse:
    """Approve a recommendation."""
    state_manager = state_store.get(investigation_id)
    if state_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found",
        )

    if recommendation_index < 0 or recommendation_index >= len(state_manager.recommendations):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation index {recommendation_index} not found",
        )

    recommendation = state_manager.recommendations[recommendation_index]

    if not recommendation.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recommendation does not require approval",
        )

    recommendation.status = RecommendationStatus.APPROVED
    note = f" (note: {request.note})" if request.note else ""
    state_manager.timeline.add_event(
        "recommendation_approved",
        f"Recommendation approved: {recommendation.action}{note}",
        "API",
    )

    return RecommendationActionResponse(
        recommendation_index=recommendation_index,
        action="approve",
        status=RecommendationStatus.APPROVED,
        message=f"Recommendation approved: {recommendation.action}{note}",
    )


@router.post(
    "/investigations/{investigation_id}/recommendations/{recommendation_index}/reject",
    response_model=RecommendationActionResponse,
)
async def reject_recommendation(
    investigation_id: str,
    recommendation_index: int,
    request: RecommendationActionRequest,
    state_store: InvestigationStateStore = Depends(get_state_store_instance),
) -> RecommendationActionResponse:
    """Reject a recommendation."""
    state_manager = state_store.get(investigation_id)
    if state_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found",
        )

    if recommendation_index < 0 or recommendation_index >= len(state_manager.recommendations):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation index {recommendation_index} not found",
        )

    recommendation = state_manager.recommendations[recommendation_index]

    if not recommendation.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recommendation does not require approval",
        )

    recommendation.status = RecommendationStatus.REJECTED
    note = f" (note: {request.note})" if request.note else ""
    state_manager.timeline.add_event(
        "recommendation_rejected",
        f"Recommendation rejected: {recommendation.action}{note}",
        "API",
    )

    return RecommendationActionResponse(
        recommendation_index=recommendation_index,
        action="reject",
        status=RecommendationStatus.REJECTED,
        message=f"Recommendation rejected: {recommendation.action}{note}",
    )