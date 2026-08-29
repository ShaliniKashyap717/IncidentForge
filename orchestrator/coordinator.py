"""Incident Commander coordination logic."""

from __future__ import annotations

from typing import Any

from orchestrator.dispatcher import AgentDispatcher
from orchestrator.state_manager import InvestigationStateManager


class IncidentCoordinator:
    """
    Coordinates the investigation at a high level.

    The coordinator represents the Engineering Incident Commander.
    """

    def __init__(
        self,
        dispatcher: AgentDispatcher | None = None,
    ) -> None:
        self.dispatcher = dispatcher or AgentDispatcher()

    def triage(
        self,
        state_manager: InvestigationStateManager,
        context: dict[str, Any],
    ) -> list[str]:
        """
        Determine which specialist agents should investigate first.

        This initial implementation is deterministic. Later this decision
        can be delegated to a Gemini-powered Incident Commander.
        """

        incident = state_manager.incident

        selected_agents: list[str] = []

        # Every production incident should initially receive
        # telemetry investigation.
        if self.dispatcher.has_agent("observability"):
            selected_agents.append("observability")

        state_manager.add_task(
            f"Investigate incident: {incident.title}"
        )

        state_manager.timeline.add_event(
            "commander_triage",
            (
                f"Commander selected agents: "
                f"{', '.join(selected_agents)}"
            ),
            "Incident Commander",
        )

        return selected_agents