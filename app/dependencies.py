"""Dependency injection helpers for the IncidentForge application."""

from __future__ import annotations

from orchestrator.state_store import InvestigationStateStore, get_state_store
from orchestrator.workflow import IncidentWorkflow


_workflow: IncidentWorkflow | None = None


def get_workflow() -> IncidentWorkflow:
    """Get the singleton IncidentWorkflow instance."""
    global _workflow
    if _workflow is None:
        _workflow = IncidentWorkflow()
    return _workflow


def get_state_store_instance() -> InvestigationStateStore:
    """Get the singleton InvestigationStateStore instance."""
    return get_state_store()