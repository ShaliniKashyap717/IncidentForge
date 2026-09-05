"""In-memory store for InvestigationStateManager objects."""

from __future__ import annotations

from typing import Any

from orchestrator.state_manager import InvestigationStateManager


class InvestigationStateStore:
    """Simple in-memory store for investigation state managers."""

    def __init__(self) -> None:
        self._store: dict[str, InvestigationStateManager] = {}

    def save(self, investigation_id: str, state_manager: InvestigationStateManager) -> None:
        """Save a state manager by investigation ID."""
        self._store[investigation_id] = state_manager

    def get(self, investigation_id: str) -> InvestigationStateManager | None:
        """Get a state manager by investigation ID. Returns None if not found."""
        return self._store.get(investigation_id)

    def exists(self, investigation_id: str) -> bool:
        """Check if an investigation ID exists in the store."""
        return investigation_id in self._store

    def delete(self, investigation_id: str) -> bool:
        """Delete an investigation from the store. Returns True if deleted."""
        if investigation_id in self._store:
            del self._store[investigation_id]
            return True
        return False

    def list_ids(self) -> list[str]:
        """List all investigation IDs in the store."""
        return list(self._store.keys())

    def list_summaries(self) -> list[dict[str, Any]]:
        """List summaries of all investigations."""
        return [
            {
                "investigation_id": inv_id,
                "incident_id": state_manager.incident.id,
                "incident_title": state_manager.incident.title,
                "status": state_manager.status,
                "stage": state_manager.stage,
                "progress": state_manager.progress,
                "error": state_manager.error,
                "evidence_count": state_manager.evidence_store.count(),
                "findings_count": len(state_manager.findings),
                "recommendations_count": len(state_manager.recommendations),
                "active_agents": list(state_manager.active_agents),
                "completed_agents": list(state_manager.completed_agents),
                "pending_tasks": state_manager.pending_tasks,
                "completed_tasks": state_manager.completed_tasks,
            }
            for inv_id, state_manager in self._store.items()
        ]


_state_store: InvestigationStateStore | None = None


def get_state_store() -> InvestigationStateStore:
    """Get the singleton state store instance."""
    global _state_store
    if _state_store is None:
        _state_store = InvestigationStateStore()
    return _state_store