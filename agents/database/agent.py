"""Database Analysis Agent implementation using Google ADK."""

from __future__ import annotations

import json
from typing import Any

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agents.database.prompt import build_database_finding_prompt, build_database_instruction
from agents.database.tools import (
	analyze_database_locks,
	analyze_database_metrics,
	analyze_database_queries,
	build_database_tools,
)
from app.config import get_gemini_model_name, has_google_api_key
from models.evidence import Evidence, EvidenceType
from models.finding import Finding
from orchestrator.state_manager import InvestigationStateManager


class DatabaseAgent:
	"""Analyze database-related behavior and produce a structured Finding."""

	def __init__(self, model_name: str | None = None, app_name: str = "incidentforge") -> None:
		self.name = "Database Agent"
		self.model_name = model_name or get_gemini_model_name()
		self.app_name = app_name
		self.session_service = InMemorySessionService()
		self.adk_agent = Agent(
			name="database_agent",
			model=self.model_name,
			instruction=build_database_instruction(),
			tools=build_database_tools(),
			output_schema=Finding,
			mode="single_turn",
		)

	def investigate(
		self,
		state_manager: InvestigationStateManager,
		scenario: dict[str, Any],
		use_llm: bool = True,
	) -> Finding:
		"""Run database analysis and update shared investigation state."""

		state_manager.start_agent(self.name)
		state_manager.add_task("Analyze database behavior")

		evidence_pool: list[Evidence] = []

		try:
			incident = scenario.get("incident", {})
			traces_payload = scenario.get("traces", {})
			logs = scenario.get("logs", [])

			query_result = analyze_database_queries(traces_payload)
			lock_result = analyze_database_locks(logs, query_result.get("database_spans", []))
			metrics_result = analyze_database_metrics(
				query_result.get("database_spans", []),
				incident_title=str(incident.get("title", "incident")),
			)

			analysis_results = {
				"incident": incident,
				"queries": query_result,
				"locks": lock_result,
				"metrics": metrics_result,
			}

			evidence_pool = self._build_evidence(query_result, lock_result, metrics_result)
			for evidence in evidence_pool:
				state_manager.add_evidence(evidence)

			finding = self._generate_finding(analysis_results, evidence_pool, use_llm=use_llm)
			finding.evidence = self._align_finding_evidence(finding.evidence, evidence_pool)
			if not finding.evidence and evidence_pool:
				finding.evidence = evidence_pool

			state_manager.add_finding(finding)
			state_manager.complete_task("Analyze database behavior")
			state_manager.timeline.add_event(
				"database_analyzed",
				"Database spans, locks, and latency indicators were analyzed.",
				self.name,
			)
			state_manager.finish_agent(self.name)
			return finding

		except Exception as exc:
			state_manager.timeline.add_event(
				"database_error",
				f"Database analysis failed: {exc}",
				self.name,
			)
			fallback = Finding(
				agent=self.name,
				summary="Database analysis failed before a structured conclusion could be produced.",
				hypothesis="Database evidence was unavailable due to tool or model failure.",
				confidence=0.1,
				evidence=evidence_pool,
				next_actions=[
					"Retry database analysis",
					"Validate trace and log scenario files",
					"Inspect database-tool failures",
				],
			)
			state_manager.add_finding(fallback)
			state_manager.complete_task("Analyze database behavior")
			state_manager.finish_agent(self.name)
			return fallback

	def _build_evidence(
		self,
		query_result: dict[str, Any],
		lock_result: dict[str, Any],
		metrics_result: dict[str, Any],
	) -> list[Evidence]:
		"""Convert database analysis outputs into Evidence models."""

		evidence: list[Evidence] = []

		summary = query_result.get("summary", {})
		if summary.get("count", 0) > 0:
			evidence.append(
				Evidence(
					type=EvidenceType.DATABASE,
					source="database",
					description=(
						f"Observed {summary.get('count', 0)} database spans with min {float(summary.get('min_ms', 0.0)):.0f}ms, "
						f"max {float(summary.get('max_ms', 0.0)):.0f}ms, avg {float(summary.get('avg_ms', 0.0)):.0f}ms."
					),
					relevance=0.86,
				)
			)

		slow_queries = query_result.get("slow_queries", [])
		if slow_queries:
			first = slow_queries[0]
			evidence.append(
				Evidence(
					type=EvidenceType.DATABASE,
					source=str(first.get("service", "database")),
					description=(
						f"Slow database span {first.get('name', 'unknown')} in trace {first.get('trace_id', 'unknown')} "
						f"took {float(first.get('duration_ms', 0.0)):.0f}ms."
					),
					relevance=min(1.0, 0.8 + min(len(slow_queries), 5) * 0.03),
				)
			)

		anomaly = metrics_result.get("anomaly", {})
		if anomaly.get("is_anomalous"):
			evidence.append(
				Evidence(
					type=EvidenceType.METRIC,
					source="database",
					description=f"Database latency anomaly detected: {anomaly.get('reason', 'threshold breach')}",
					relevance=0.9,
				)
			)

		correlation = metrics_result.get("correlation", {})
		if correlation.get("description"):
			evidence.append(
				Evidence(
					type=EvidenceType.DATABASE,
					source="database",
					description=str(correlation.get("description")),
					relevance=0.8 if correlation.get("correlated") else 0.55,
				)
			)

		contention = lock_result.get("contention", {})
		if contention.get("possible_contention"):
			evidence.append(
				Evidence(
					type=EvidenceType.DATABASE,
					source="database",
					description=str(contention.get("description", "Possible contention inferred from spans.")),
					relevance=0.74,
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
		"""Run ADK reasoning and return structured output when available."""

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

		prompt = build_database_finding_prompt(json.dumps(analysis_results, indent=2, sort_keys=True))
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
		"""Produce deterministic fallback finding from database analysis outputs."""

		query_summary = analysis_results.get("queries", {}).get("summary", {})
		slow_count = len(analysis_results.get("queries", {}).get("slow_queries", []))
		anomaly = analysis_results.get("metrics", {}).get("anomaly", {})

		summary = (
			f"Database analysis observed {int(query_summary.get('count', 0))} database spans and {slow_count} "
			"slow query spans in incident-related traces."
		)

		if anomaly.get("is_anomalous"):
			hypothesis = (
				"Database latency likely amplified end-to-end request latency, potentially contributing as a secondary "
				"factor alongside upstream service behavior."
			)
		else:
			hypothesis = (
				"Database behavior does not currently show dominant evidence of being the primary incident driver."
			)

		next_actions = [
			"Inspect query execution plans for the slow database spans.",
			"Correlate database span latency with deployment and retry windows.",
			"Check lock and contention metrics in database observability systems.",
		]

		return Finding(
			agent=self.name,
			summary=summary,
			hypothesis=hypothesis,
			confidence=self._combine_confidence(evidence_pool),
			evidence=evidence_pool,
			next_actions=next_actions,
		)

	def _align_finding_evidence(self, finding_evidence: list[Evidence], evidence_pool: list[Evidence]) -> list[Evidence]:
		"""Ensure final finding uses only evidence generated during this investigation."""

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
		"""Combine evidence relevance into a bounded confidence score."""

		if not evidence_pool:
			return 0.2
		return max(0.0, min(1.0, sum(item.relevance for item in evidence_pool) / len(evidence_pool)))
