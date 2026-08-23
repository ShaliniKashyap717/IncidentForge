"""Repository/Deployment Analysis Agent implementation using Google ADK."""

from __future__ import annotations

import json
from typing import Any

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agents.repository.prompt import (
    build_repository_finding_prompt,
    build_repository_instruction,
)
from agents.repository.tools import (
    analyze_repository_change_correlation,
    analyze_repository_commits,
    analyze_repository_deployments,
    build_repository_tools,
    infer_incident_reference_timestamp,
)
from app.config import get_gemini_model_name, has_google_api_key
from models.evidence import Evidence, EvidenceType
from models.finding import Finding
from orchestrator.state_manager import InvestigationStateManager


class RepositoryAgent:
    """Analyze repository and deployment changes and produce a structured Finding."""

    def __init__(self, model_name: str | None = None, app_name: str = "incidentforge") -> None:
        self.name = "Repository Agent"
        self.model_name = model_name or get_gemini_model_name()
        self.app_name = app_name
        self.session_service = InMemorySessionService()
        self.adk_agent = Agent(
            name="repository_agent",
            model=self.model_name,
            instruction=build_repository_instruction(),
            tools=build_repository_tools(),
            output_schema=Finding,
            mode="single_turn",
        )

    def investigate(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        use_llm: bool = True,
    ) -> Finding:
        """Run repository/deployment analysis and update shared investigation state."""

        state_manager.start_agent(self.name)
        state_manager.add_task("Analyze repository and deployment changes")

        evidence_pool: list[Evidence] = []

        try:
            incident = scenario.get("incident", {})
            affected_services = incident.get("affected_services", []) if isinstance(incident, dict) else []
            reference_timestamp = infer_incident_reference_timestamp(scenario)

            commits_result = analyze_repository_commits(
                commits_payload=scenario.get("commits", {}),
                affected_services=affected_services,
            )
            deployments_result = analyze_repository_deployments(
                deployments_payload=scenario.get("deployments", {}),
                affected_services=affected_services,
                reference_timestamp=reference_timestamp,
            )
            correlation_result = analyze_repository_change_correlation(commits_result, deployments_result)

            analysis_results = {
                "incident": incident,
                "reference_timestamp": reference_timestamp,
                "commits": commits_result,
                "deployments": deployments_result,
                "correlations": correlation_result,
            }

            evidence_pool = self._build_evidence(commits_result, deployments_result, correlation_result)
            for evidence in evidence_pool:
                state_manager.add_evidence(evidence)

            finding = self._generate_finding(analysis_results, evidence_pool, use_llm=use_llm)
            finding.evidence = self._align_finding_evidence(finding.evidence, evidence_pool)
            if not finding.evidence and evidence_pool:
                finding.evidence = evidence_pool

            state_manager.add_finding(finding)
            state_manager.complete_task("Analyze repository and deployment changes")
            state_manager.timeline.add_event(
                "repository_analyzed",
                "Repository commits and deployments were correlated against the incident timeline.",
                self.name,
            )
            state_manager.finish_agent(self.name)
            return finding

        except Exception as exc:
            state_manager.timeline.add_event(
                "repository_error",
                f"Repository analysis failed: {exc}",
                self.name,
            )
            fallback = Finding(
                agent=self.name,
                summary="Repository analysis failed before a structured conclusion could be produced.",
                hypothesis="Repository or deployment evidence was unavailable due to tool or model failure.",
                confidence=0.1,
                evidence=evidence_pool,
                next_actions=[
                    "Retry repository analysis",
                    "Validate commit and deployment scenario files",
                    "Inspect repository-tool failures",
                ],
            )
            state_manager.add_finding(fallback)
            state_manager.complete_task("Analyze repository and deployment changes")
            state_manager.finish_agent(self.name)
            return fallback

    def _build_evidence(
        self,
        commits_result: dict[str, Any],
        deployments_result: dict[str, Any],
        correlation_result: dict[str, Any],
    ) -> list[Evidence]:
        """Create Evidence objects from repository analysis outputs."""

        evidence: list[Evidence] = []

        for commit in commits_result.get("relevant_commits", []):
            sha = str(commit.get("sha", "unknown"))
            message = str(commit.get("message", ""))
            source = str(commits_result.get("service") or "repository")
            evidence.append(
                Evidence(
                    type=EvidenceType.CODE,
                    source=source,
                    description=f"Commit {sha}: {message}",
                    relevance=0.82,
                )
            )

        deployment_candidates = deployments_result.get("nearby_deployments") or deployments_result.get("keyword_matched", [])
        for deployment in deployment_candidates:
            deployment_id = str(deployment.get("id", "unknown"))
            service = str(deployment.get("service", "unknown"))
            timestamp = deployment.get("timestamp")
            notes = str(deployment.get("notes", ""))
            evidence.append(
                Evidence(
                    type=EvidenceType.DEPLOYMENT,
                    source=service,
                    description=f"Deployment {deployment_id}: {notes}",
                    timestamp=str(timestamp) if timestamp is not None else None,
                    relevance=0.84,
                )
            )

        top_correlation = (correlation_result.get("correlations") or [None])[0]
        if isinstance(top_correlation, dict):
            sha = str(top_correlation.get("commit_sha", "unknown"))
            deployment_id = str(top_correlation.get("deployment_id", "unknown"))
            overlap = float(top_correlation.get("overlap_score", 0.0))
            evidence.append(
                Evidence(
                    type=EvidenceType.CODE,
                    source="repository-correlation",
                    description=(
                        f"Commit {sha} correlates with deployment {deployment_id} "
                        f"(overlap score {overlap:.2f})."
                    ),
                    relevance=min(1.0, 0.7 + overlap * 0.3),
                )
            )

        return evidence

    def _generate_finding(
        self,
        analysis_results: dict[str, Any],
        evidence_pool: list[Evidence],
        use_llm: bool,
    ) -> Finding:
        """Generate a structured finding via ADK with deterministic fallback."""

        if use_llm and has_google_api_key():
            try:
                output = self._run_with_adk(analysis_results)
                if isinstance(output, Finding):
                    return output
                if isinstance(output, dict):
                    return Finding.model_validate(output)
            except Exception:
                pass

        return self._build_deterministic_finding(analysis_results, evidence_pool)

    def _run_with_adk(self, analysis_results: dict[str, Any]) -> Finding | dict[str, Any] | None:
        """Run ADK reasoning and return the final structured output if present."""

        session = self.session_service.create_session_sync(
            app_name=self.app_name,
            user_id="incidentforge",
            state={"analysis_results": analysis_results},
        )
        runner = Runner(
            agent=self.adk_agent,
            session_service=self.session_service,
            app_name=self.app_name,
        )

        prompt = build_repository_finding_prompt(json.dumps(analysis_results, indent=2, sort_keys=True))
        user_message = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

        final_output: Finding | dict[str, Any] | None = None
        for event in runner.run(
            user_id="incidentforge",
            session_id=session.id,
            new_message=user_message,
        ):
            if event.output is not None:
                final_output = event.output

        return final_output

    def _build_deterministic_finding(
        self,
        analysis_results: dict[str, Any],
        evidence_pool: list[Evidence],
    ) -> Finding:
        """Produce deterministic fallback finding when LLM execution is unavailable."""

        commits = analysis_results.get("commits", {})
        deployments = analysis_results.get("deployments", {})
        correlations = analysis_results.get("correlations", {})

        relevant_count = int(commits.get("relevant_count", 0))
        deployment_count = len(deployments.get("nearby_deployments") or deployments.get("keyword_matched", []))
        correlation_count = int(correlations.get("correlation_count", 0))

        summary = (
            f"Repository analysis found {relevant_count} change-related commits and {deployment_count} "
            f"deployments near the incident context, with {correlation_count} commit/deployment correlations."
        )

        if relevant_count > 0:
            first_commit = commits.get("relevant_commits", [])[0]
            hypothesis = (
                "A recent code or configuration change likely contributed to incident behavior; "
                f"notably commit {first_commit.get('sha', 'unknown')} modified retry/timeout related logic."
            )
        else:
            hypothesis = "Repository metadata does not yet isolate a likely change-related trigger."

        confidence = self._combine_confidence(evidence_pool)
        next_actions = [
            "Inspect the identified commit set for retry, timeout, and backoff changes.",
            "Validate deployment configuration drift for affected services.",
            "Correlate commit/deployment timing with telemetry anomaly onset.",
        ]

        return Finding(
            agent=self.name,
            summary=summary,
            hypothesis=hypothesis,
            confidence=confidence,
            evidence=evidence_pool,
            next_actions=next_actions,
        )

    def _align_finding_evidence(self, finding_evidence: list[Evidence], evidence_pool: list[Evidence]) -> list[Evidence]:
        """Ensure final finding references only evidence from the generated evidence pool."""

        if not finding_evidence:
            return evidence_pool

        aligned: list[Evidence] = []
        for candidate in finding_evidence:
            match = next(
                (
                    evidence
                    for evidence in evidence_pool
                    if evidence.type == candidate.type
                    and evidence.source == candidate.source
                    and evidence.description == candidate.description
                    and evidence.timestamp == candidate.timestamp
                ),
                None,
            )
            if match is not None:
                aligned.append(match)

        return aligned or evidence_pool

    def _combine_confidence(self, evidence_pool: list[Evidence]) -> float:
        """Combine evidence relevance scores into a bounded confidence value."""

        if not evidence_pool:
            return 0.2
        return max(0.0, min(1.0, sum(item.relevance for item in evidence_pool) / len(evidence_pool)))
