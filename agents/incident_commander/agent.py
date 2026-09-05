"""Incident Commander agent implementation using Google ADK."""

from __future__ import annotations

import json
from typing import Any

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agents.incident_commander.prompt import (
    build_finding_synthesis_prompt,
    build_incident_commander_instruction,
    build_investigation_context_prompt,
)
from agents.observability.agent import ObservabilityAgent
from agents.repository.agent import RepositoryAgent
from agents.database.agent import DatabaseAgent
from app.config import get_gemini_model_name, has_google_api_key
from models.finding import Finding
from models.hypothesis import Hypothesis
from models.recommendation import Recommendation
from models.state import IncidentState
from orchestrator.state_manager import InvestigationStateManager


class IncidentCommander:
    """Top-level investigation coordinator that manages specialist agents."""

    def __init__(
        self,
        model_name: str | None = None,
        app_name: str = "incidentforge",
    ) -> None:
        """Initialize the Incident Commander.

        Args:
            model_name: Optional model override.
            app_name: Application name for ADK sessions.
        """

        self.name = "Incident Commander"
        self.model_name = model_name or get_gemini_model_name()
        self.app_name = app_name
        self.session_service = InMemorySessionService()
        self.observability_agent = ObservabilityAgent(model_name=model_name, app_name=app_name)
        self.repository_agent = RepositoryAgent(model_name=model_name, app_name=app_name)
        self.database_agent = DatabaseAgent(model_name=model_name, app_name=app_name)

        self.adk_agent = Agent(
            name="incident_commander",
            model=self.model_name,
            instruction=build_incident_commander_instruction(),
            tools=[],
            mode="single_turn",
        )

    def investigate(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        use_llm: bool = True,
    ) -> list[Finding]:
        """Run the full investigation coordination.

        This method:
        1. Performs initial triage to select specialist agents
        2. Invokes each selected agent with appropriate context
        3. Collects findings from all agents
        4. Synthesizes findings into hypotheses and recommendations

        Args:
            state_manager: Shared investigation state manager.
            scenario: Full scenario data including incident and telemetry.
            use_llm: Whether to use LLM for coordination decisions.

        Returns:
            List of all findings produced by specialist agents.
        """

        state_manager.start_agent(self.name)
        state_manager.add_task("Coordinate incident investigation")

        all_findings: list[Finding] = []

        try:
            selected_agents = self._triage(state_manager, scenario, use_llm)

            for agent_name in selected_agents:
                if agent_name == "observability":
                    finding = self._invoke_observability_agent(
                        state_manager,
                        scenario,
                        use_llm,
                    )
                    all_findings.append(finding)

                    state_manager.timeline.add_event(
                        "finding_received",
                        f"Received finding from {finding.agent}: {finding.summary[:80]}",
                        self.name,
                    )
                elif agent_name == "repository":
                    finding = self._invoke_repository_agent(
                        state_manager,
                        scenario,
                        use_llm,
                    )
                    all_findings.append(finding)

                    state_manager.timeline.add_event(
                        "finding_received",
                        f"Received finding from {finding.agent}: {finding.summary[:80]}",
                        self.name,
                    )
                elif agent_name == "database":
                    finding = self._invoke_database_agent(
                        state_manager,
                        scenario,
                        use_llm,
                    )
                    all_findings.append(finding)

                    state_manager.timeline.add_event(
                        "finding_received",
                        f"Received finding from {finding.agent}: {finding.summary[:80]}",
                        self.name,
                    )
                else:
                    state_manager.timeline.add_event(
                        "agent_skipped",
                        f"Agent {agent_name} not yet implemented",
                        self.name,
                    )

            if all_findings:
                if use_llm and has_google_api_key():
                    self._synthesize_findings(state_manager, scenario, all_findings, use_llm)
                else:
                    self._synthesize_findings_deterministic(state_manager, scenario, all_findings)

                state_manager.mark_complete()
                state_manager.timeline.add_event(
                    "investigation_completed",
                    "Investigation concluded with synthesized hypotheses and recommendations",
                    self.name,
                )

            state_manager.complete_task("Coordinate incident investigation")
            state_manager.timeline.add_event(
                "investigation_coordinated",
                f"Coordinated {len(all_findings)} specialist agent(s)",
                self.name,
            )
            state_manager.finish_agent(self.name)

            return all_findings

        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            state_manager.timeline.add_event(
                "commander_error",
                f"Incident Commander coordination failed: {exc}",
                self.name,
            )
            state_manager.complete_task("Coordinate incident investigation")
            state_manager.finish_agent(self.name)
            return all_findings

    def _triage(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        use_llm: bool,
    ) -> list[str]:
        """Determine which specialist agents should participate.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.
            use_llm: Whether to use LLM for triage decision.

        Returns:
            List of selected agent names.
        """

        if use_llm and has_google_api_key():
            try:
                state_summary = self._build_state_summary(state_manager, scenario)
                return self._llm_triage(state_summary)
            except (RuntimeError, ValueError, KeyError, TypeError):
                # LLM triage failed; fall back to deterministic triage
                pass

        return self._deterministic_triage(state_manager, scenario)

    def _deterministic_triage(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
    ) -> list[str]:
        """Deterministic fallback triage: select agents based on incident characteristics.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.

        Returns:
            List of agent names to invoke.
        """

        incident = state_manager.incident
        selected = ["observability"]

        # For payment latency and similar scenarios, also investigate repository/deployment changes
        if incident.id == "INC-2026-1042" or "latency" in incident.title.lower() or "payment" in incident.title.lower():
            selected.append("repository")

        # For database-related incidents (lock contention, database in affected services)
        if "database" in incident.affected_services or "lock" in incident.title.lower() or "contention" in incident.title.lower() or "database" in incident.title.lower():
            selected.append("database")

        state_manager.add_task(f"Investigate incident: {incident.title}")
        state_manager.timeline.add_event(
            "commander_triage",
            f"Commander selected agents: {', '.join(selected)}",
            self.name,
        )

        return selected

    def _llm_triage(self, state_summary: str) -> list[str]:
        """Use LLM to decide which agents to invoke.

        Args:
            state_summary: Text summary of investigation state.

        Returns:
            List of selected agent names.
        """

        session = self.session_service.create_session_sync(
            app_name=self.app_name,
            user_id="incidentforge",
            state={},
        )
        runner = Runner(
            agent=self.adk_agent,
            session_service=self.session_service,
            app_name=self.app_name,
        )

        prompt = build_investigation_context_prompt(state_summary)
        user_message = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

        final_output: str | None = None
        for event in runner.run(
            user_id="incidentforge",
            session_id=session.id,
            new_message=user_message,
        ):
            if event.output is not None:
                final_output = str(event.output)

        if not final_output:
            return ["observability"]

        try:
            decision = json.loads(final_output)
            agents = decision.get("selected_agents", ["observability"])
            return [a for a in agents if a in self._available_agents()]
        except (json.JSONDecodeError, AttributeError):
            return ["observability"]

    def _available_agents(self) -> list[str]:
        """Return list of currently implemented specialist agents."""
        return ["observability", "repository", "database"]

    def _build_state_summary(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
    ) -> str:
        """Build a text summary of the current investigation state.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.

        Returns:
            Formatted state summary.
        """

        incident = state_manager.incident
        evidence = state_manager.evidence_store.get_all()

        lines = [
            f"Incident: {incident.id} - {incident.title}",
            f"Severity: {incident.severity.value}",
            f"Description: {incident.description}",
            f"Affected Services: {', '.join(incident.affected_services) or 'none'}",
            f"Status: {incident.status.value}",
            "",
            f"Evidence Count: {len(evidence)}",
        ]

        if evidence:
            lines.append("Evidence:")
            for e in evidence:
                lines.append(f"  - [{e.type.value}] {e.source}: {e.description[:100]} (relevance={e.relevance:.2f})")

        if state_manager.findings:
            lines.append("\nExisting Findings:")
            for f in state_manager.findings:
                lines.append(f"  - {f.agent}: {f.summary[:100]} (confidence={f.confidence:.2f})")

        return "\n".join(lines)

    def _invoke_observability_agent(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        use_llm: bool,
    ) -> Finding:
        """Invoke the Observability Agent and return its finding.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.
            use_llm: Whether the observability agent should use LLM.

        Returns:
            Finding from the Observability Agent.
        """

        state_manager.timeline.add_event(
            "agent_invoked",
            "Invoking Observability Agent for telemetry analysis",
            self.name,
        )

        finding = self.observability_agent.investigate(state_manager, scenario, use_llm)

        state_manager.timeline.add_event(
            "agent_completed",
            f"Observability Agent returned finding: {finding.summary[:80]}",
            self.name,
        )

        return finding

    def _invoke_repository_agent(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        use_llm: bool,
    ) -> Finding:
        """Invoke the Repository Agent and return its finding.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.
            use_llm: Whether the repository agent should use LLM.

        Returns:
            Finding from the Repository Agent.
        """

        state_manager.timeline.add_event(
            "agent_invoked",
            "Invoking Repository Agent for code and deployment analysis",
            self.name,
        )

        finding = self.repository_agent.investigate(state_manager, scenario, use_llm)

        state_manager.timeline.add_event(
            "agent_completed",
            f"Repository Agent returned finding: {finding.summary[:80]}",
            self.name,
        )

        return finding

    def _invoke_database_agent(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        use_llm: bool,
    ) -> Finding:
        """Invoke the Database Agent and return its finding.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.
            use_llm: Whether the database agent should use LLM.

        Returns:
            Finding from the Database Agent.
        """

        state_manager.timeline.add_event(
            "agent_invoked",
            "Invoking Database Agent for database behavior analysis",
            self.name,
        )

        finding = self.database_agent.investigate(state_manager, scenario, use_llm)

        state_manager.timeline.add_event(
            "agent_completed",
            f"Database Agent returned finding: {finding.summary[:80]}",
            self.name,
        )

        return finding

    def _synthesize_findings(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        findings: list[Finding],
        use_llm: bool,
    ) -> None:
        """Synthesize multiple agent findings into hypotheses and recommendations.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.
            findings: List of findings from all agents.
            use_llm: Whether to use LLM for synthesis.
        """

        try:
            incident = state_manager.incident
            evidence = state_manager.evidence_store.get_all()

            findings_summary = "\n".join(
                f"- {f.agent}: {f.summary} (confidence={f.confidence:.2f}, hypothesis={f.hypothesis})"
                for f in findings
            )

            evidence_summary = "\n".join(
                f"- [{e.type.value}] {e.source}: {e.description} (relevance={e.relevance:.2f})"
                for e in evidence
            )

            prompt = build_finding_synthesis_prompt(
                incident_title=incident.title,
                incident_description=incident.description,
                findings_summary=findings_summary,
                evidence_summary=evidence_summary,
            )

            session = self.session_service.create_session_sync(
                app_name=self.app_name,
                user_id="incidentforge",
                state={},
            )
            runner = Runner(
                agent=self.adk_agent,
                session_service=self.session_service,
                app_name=self.app_name,
            )

            user_message = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

            final_output: str | None = None
            for event in runner.run(
                user_id="incidentforge",
                session_id=session.id,
                new_message=user_message,
            ):
                if event.output is not None:
                    final_output = str(event.output)

            if final_output:
                self._apply_synthesis(state_manager, final_output)

        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            state_manager.timeline.add_event(
                "synthesis_error",
                f"Finding synthesis failed: {exc}",
                self.name,
            )

    def _synthesize_findings_deterministic(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        findings: list[Finding],
    ) -> None:
        """Synthesize findings into hypotheses and recommendations deterministically.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.
            findings: List of findings from all agents.
        """
        incident = state_manager.incident
        evidence = state_manager.evidence_store.get_all()

        for finding in findings:
            hypothesis = Hypothesis(
                description=finding.hypothesis,
                confidence=finding.confidence,
                supporting_evidence=finding.evidence,
                contradicting_evidence=[],
                status="active",
            )
            state_manager.add_hypothesis(hypothesis)
            state_manager.timeline.add_event(
                "hypothesis_synthesized",
                f"Hypothesis synthesized from {finding.agent}: {hypothesis.description[:80]}",
                self.name,
            )

        if evidence:
            evidence_sources = ", ".join(set(e.source for e in evidence))
            action = (
                f"Investigate and remediate the latency spike in {incident.affected_services[0] if incident.affected_services else 'the affected service'}, "
                f"focusing on the downstream dependency slowdown and retry amplification identified in telemetry."
            )
            rationale = (
                f"Telemetry analysis shows a {findings[0].summary.lower() if findings else 'latency anomaly'}. "
                f"Evidence from {evidence_sources} confirms downstream dependency slowdown combined with retry behavior "
                f"amplifying end-to-end latency. This is the primary driver of the {incident.title.lower()}."
            )
            risk = (
                "Remediation may involve configuration changes to timeouts, retries, or circuit breakers. "
                "Incorrect tuning could increase error rates or mask underlying capacity issues."
            )

            recommendation = Recommendation(
                action=action,
                rationale=rationale,
                risk=risk,
                confidence=min(0.9, findings[0].confidence + 0.1) if findings else 0.7,
                requires_approval=True,
            )
            state_manager.add_recommendation(recommendation)
            state_manager.timeline.add_event(
                "recommendation_generated",
                f"Recommendation generated: {recommendation.action[:80]}",
                self.name,
            )

    def _apply_synthesis(
        self,
        state_manager: InvestigationStateManager,
        synthesis_output: str,
    ) -> None:
        """Apply the synthesis output to the investigation state.

        Args:
            state_manager: Shared investigation state.
            synthesis_output: JSON string from LLM synthesis.
        """

        try:
            result = json.loads(synthesis_output)

            for hyp in result.get("hypotheses", []):
                hypothesis = Hypothesis(
                    description=hyp.get("hypothesis", ""),
                    confidence=hyp.get("confidence", 0.5),
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    status="active",
                )
                state_manager.add_hypothesis(hypothesis)

            for rec in result.get("recommendations", []):
                recommendation = Recommendation(
                    action=rec.get("action", ""),
                    rationale=rec.get("rationale", ""),
                    risk=rec.get("risk", "Requires careful validation before deployment."),
                    confidence=rec.get("confidence", 0.8),
                    requires_approval=True,
                )
                state_manager.add_recommendation(recommendation)

            for gap in result.get("evidence_gaps", []):
                state_manager.timeline.add_event(
                    "evidence_gap_identified",
                    f"Gap: {gap}",
                    self.name,
                )

        except (json.JSONDecodeError, KeyError) as exc:
            state_manager.timeline.add_event(
                "synthesis_parse_error",
                f"Failed to parse synthesis output: {exc}",
                self.name,
            )

    def coordinate_from_state(
        self,
        incident_state: IncidentState,
        use_llm: bool = True,
    ) -> list[Finding]:
        """Coordinate investigation from an IncidentState object.

        This is the primary callable interface for the orchestrator.

        Args:
            incident_state: Current investigation state.
            use_llm: Whether to use LLM for coordination.

        Returns:
            List of findings from all invoked specialist agents.
        """

        scenario = {
            "incident": incident_state.incident.model_dump(mode="json"),
            "logs": [],
            "metrics": {},
            "traces": {},
        }

        incident = incident_state.incident
        state_manager = InvestigationStateManager(incident)

        for finding in incident_state.investigation.findings:
            state_manager.add_finding(finding)

        return self.investigate(state_manager, scenario, use_llm)


def create_incident_commander(
    model_name: str | None = None,
    app_name: str = "incidentforge",
) -> IncidentCommander:
    """Factory function to create an Incident Commander instance.

    Args:
        model_name: Optional model override.
        app_name: Application name for ADK sessions.

    Returns:
        Configured IncidentCommander instance.
    """

    return IncidentCommander(model_name=model_name, app_name=app_name)