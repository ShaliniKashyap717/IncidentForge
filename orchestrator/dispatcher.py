"""Agent dispatcher for IncidentForge."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agents.observability.agent import ObservabilityAgent
from orchestrator.state_manager import InvestigationStateManager


class AgentDispatcher:
    """
    Routes investigation tasks to specialized agents.

    The dispatcher is intentionally kept separate from the Incident Commander:
    the Commander decides WHAT should happen, while the Dispatcher determines
    HOW to invoke the corresponding agent.
    """

    def __init__(self) -> None:
        self._agents: dict[str, Callable[..., Any]] = {
            "observability": ObservabilityAgent,
        }

    def register_agent(
        self,
        name: str,
        factory: Callable[..., Any],
    ) -> None:
        """Register an agent factory."""

        self._agents[name] = factory

    def available_agents(self) -> list[str]:
        """Return the names of registered agents."""

        return list(self._agents.keys())

    def has_agent(self, name: str) -> bool:
        """Check whether an agent is registered."""

        return name in self._agents

    async def dispatch(
        self,
        agent_name: str,
        state_manager: InvestigationStateManager,
        context: dict[str, Any],
    ) -> Any:
        """
        Execute a registered agent.

        Args:
            agent_name: Name of the specialist agent.
            state_manager: Shared investigation state.
            context: Scenario/incident context for the agent.

        Returns:
            Agent execution result.
        """

        if not self.has_agent(agent_name):
            raise ValueError(
                f"Unknown agent '{agent_name}'. "
                f"Available agents: {self.available_agents()}"
            )

        state_manager.start_agent(agent_name)

        try:
            agent_factory = self._agents[agent_name]
            agent = agent_factory()

            # Execute the agent's investigate method
            if hasattr(agent, "investigate"):
                result = agent.investigate(state_manager, context, use_llm=False)
                return {
                    "agent_name": agent_name,
                    "agent": agent,
                    "result": result,
                }
            else:
                # Fallback for agents without investigate method
                return {
                    "agent_name": agent_name,
                    "agent": agent,
                    "context": context,
                }

        finally:
            state_manager.finish_agent(agent_name)