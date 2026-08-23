"""Observability Agent implementation using Google ADK."""

from __future__ import annotations

import json
from typing import Any

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.config import get_gemini_model_name, has_google_api_key
from agents.observability.prompt import (
	build_finding_generation_prompt,
	build_observability_instruction,
)
from agents.observability.tools import (
	analyze_logs,
	analyze_metrics,
	analyze_traces,
	build_observability_tools,
)
from models.evidence import Evidence, EvidenceType
from models.finding import Finding
from orchestrator.state_manager import InvestigationStateManager


class ObservabilityAgent:
	"""Analyze telemetry and produce a structured Finding for an incident."""

	def __init__(self, model_name: str | None = None, app_name: str = "incidentforge") -> None:
		"""Initialize the ADK-backed Observability Agent."""

		self.name = "Observability Agent"
		self.model_name = model_name or get_gemini_model_name()
		self.app_name = app_name
		self.session_service = InMemorySessionService()
		self.adk_agent = Agent(
			name="observability_agent",
			model=self.model_name,
			instruction=build_observability_instruction(),
			tools=build_observability_tools(),
			output_schema=Finding,
			mode="single_turn",
		)

	def investigate(
		self,
		state_manager: InvestigationStateManager,
		scenario: dict[str, Any],
		use_llm: bool = True,
	) -> Finding:
		"""Run the observability investigation and update shared state."""

		state_manager.start_agent(self.name)
		state_manager.add_task("Analyze observability telemetry")

		analysis_results: dict[str, Any] = {}
		evidence_pool: list[Evidence] = []

		try:
			logs_result = analyze_logs(scenario.get("logs", []), severity="ERROR")
			metrics_result = analyze_metrics(scenario.get("metrics", {}))
			traces_result = analyze_traces(scenario.get("traces", {}))

			analysis_results = {
				"incident": scenario.get("incident", {}),
				"logs": logs_result,
				"metrics": metrics_result,
				"traces": traces_result,
			}

			evidence_pool = self._build_evidence_from_analysis(metrics_result, logs_result, traces_result)
			for evidence in evidence_pool:
				state_manager.add_evidence(evidence)

			finding = self._generate_finding(
				analysis_results=analysis_results,
				evidence_pool=evidence_pool,
				use_llm=use_llm,
			)
			finding.evidence = self._align_finding_evidence(finding.evidence, evidence_pool)

			if not finding.evidence and evidence_pool:
				finding.evidence = evidence_pool

			state_manager.add_finding(finding)
			state_manager.complete_task("Analyze observability telemetry")
			state_manager.timeline.add_event(
				"telemetry_analyzed",
				"Metrics, logs, and traces were correlated into a structured finding.",
				self.name,
			)
			state_manager.finish_agent(self.name)
			return finding

		except Exception as exc:
			state_manager.timeline.add_event(
				"observability_error",
				f"Observability investigation failed: {exc}",
				self.name,
			)
			fallback = Finding(
				agent=self.name,
				summary="Observability analysis failed before a structured conclusion could be produced.",
				hypothesis="Telemetry analysis unavailable due to tool or model failure.",
				confidence=0.1,
				evidence=evidence_pool,
				next_actions=["Retry telemetry analysis", "Inspect tool failures", "Validate telemetry fixtures"],
			)
			state_manager.add_finding(fallback)
			state_manager.complete_task("Analyze observability telemetry")
			state_manager.finish_agent(self.name)
			return fallback

	def _build_evidence_from_analysis(
		self,
		metrics_result: dict[str, Any],
		logs_result: dict[str, Any],
		traces_result: dict[str, Any],
	) -> list[Evidence]:
		"""Create Evidence objects from structured telemetry analysis."""

		evidence: list[Evidence] = []

		metric_name = metrics_result.get("metric") or "latency"
		service = metrics_result.get("service") or "payment-api"
		stats = metrics_result.get("statistics", {})
		anomaly_window = metrics_result.get("anomaly_window", {})

		if stats:
			description = (
				f"{metric_name} statistics show min {stats.get('min', 0):.0f}ms, max {stats.get('max', 0):.0f}ms, "
				f"average {stats.get('average', 0):.0f}ms."
			)
			if anomaly_window.get("start_idx") is not None and anomaly_window.get("max_value") is not None:
				description += (
					f" Anomaly window begins at index {anomaly_window['start_idx']} and peaks at "
					f"{float(anomaly_window['max_value']):.0f}ms."
				)
			evidence.append(
				Evidence(
					type=EvidenceType.METRIC,
					source=str(service),
					description=description,
					relevance=self._confidence_from_percentage(metrics_result.get("percentage_change"), 0.75),
				)
			)

		if logs_result.get("total_matches", 0) or logs_result.get("error_counts"):
			matched_logs = logs_result.get("matched_logs", [])
			if matched_logs:
				first_log = matched_logs[0]
				log_description = (
					f"{logs_result.get('total_matches', 0)} error log entries matched the observability query; "
					f"example: {first_log.get('timestamp', 'unknown')} {first_log.get('service', 'unknown')} "
					f"{first_log.get('message', '')}"
				)
			else:
				log_description = "Error and warning logs were present during the incident window."
			evidence.append(
				Evidence(
					type=EvidenceType.LOG,
					source=str(logs_result.get("service") or service),
					description=log_description,
					relevance=self._confidence_from_counts(logs_result.get("total_matches", 0), 0.7),
				)
			)

		slow_spans = traces_result.get("slow_spans", [])
		ranked_services = traces_result.get("ranked_services", [])
		if slow_spans:
			span = slow_spans[0]
			trace_description = (
				f"Slow spans were observed in {span.get('service', 'unknown')} with {span.get('name', 'unknown')} "
				f"taking {float(span.get('duration_ms', 0)):.0f}ms."
			)
			if ranked_services:
				top_service, total_latency = ranked_services[0]
				trace_description += f" Highest aggregate latency: {top_service} at {float(total_latency):.0f}ms."
			evidence.append(
				Evidence(
					type=EvidenceType.TRACE,
					source=str(span.get("service") or traces_result.get("service") or service),
					description=trace_description,
					relevance=self._confidence_from_counts(len(slow_spans), 0.85),
				)
			)

		return evidence

	def _generate_finding(
		self,
		analysis_results: dict[str, Any],
		evidence_pool: list[Evidence],
		use_llm: bool,
	) -> Finding:
		"""Generate a structured Finding using the ADK agent when possible."""

		if use_llm and has_google_api_key():
			try:
				model_output = self._run_with_adk(analysis_results)
				if isinstance(model_output, Finding):
					return model_output
				if isinstance(model_output, dict):
					return Finding.model_validate(model_output)
			except Exception:
				pass

		return self._build_deterministic_finding(analysis_results, evidence_pool)

	def _run_with_adk(self, analysis_results: dict[str, Any]) -> Finding | dict[str, Any] | None:
		"""Execute the ADK agent and return the structured final output if available."""

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

		prompt = build_finding_generation_prompt(json.dumps(analysis_results, indent=2, sort_keys=True))
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
		"""Produce a deterministic fallback finding from structured telemetry analysis."""

		incident = analysis_results.get("incident", {})
		metrics_result = analysis_results.get("metrics", {})
		logs_result = analysis_results.get("logs", {})
		traces_result = analysis_results.get("traces", {})

		percent_change = metrics_result.get("percentage_change")
		change_text = f"{percent_change:.1f}%" if isinstance(percent_change, (int, float)) else "unknown"
		ranked_services = traces_result.get("ranked_services", [])
		top_service = ranked_services[0][0] if ranked_services else str(metrics_result.get("service") or "unknown")

		summary = (
			f"Telemetry indicates a latency spike on {metrics_result.get('service', 'the primary service')} "
			f"with an observed percentage increase of {change_text}. Logs show {logs_result.get('total_matches', 0)} "
			f"error-oriented entries, and traces show the heaviest latency in {top_service}."
		)
		hypothesis = (
			f"The {incident.get('title', 'incident')} is likely driven by a downstream dependency slowdown "
			"combined with retry behavior amplifying end-to-end latency."
		)
		confidence = self._combine_confidence(evidence_pool)

		next_actions = [
			f"Inspect the slowest service path around {top_service}.",
			"Review retry and timeout configuration for the affected service.",
			"Correlate the anomaly window with deployment or dependency changes.",
		]

		return Finding(
			agent=self.name,
			summary=summary,
			hypothesis=hypothesis,
			confidence=confidence,
			evidence=evidence_pool,
			next_actions=next_actions,
		)

	def _align_finding_evidence(
		self,
		finding_evidence: list[Evidence],
		evidence_pool: list[Evidence],
	) -> list[Evidence]:
		"""Ensure the final finding only references evidence from the actual evidence pool."""

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
				),
				None,
			)
			if match is not None:
				aligned.append(match)
		return aligned or evidence_pool

	def _confidence_from_percentage(self, percentage_change: float | None, base: float) -> float:
		"""Translate a metric percentage change into a bounded confidence contribution."""

		if percentage_change is None:
			return min(1.0, base)
		magnitude = min(abs(float(percentage_change)) / 1000.0, 1.0)
		return min(1.0, base + magnitude * 0.2)

	def _confidence_from_counts(self, count: int, base: float) -> float:
		"""Translate a count of confirmed signals into a bounded confidence contribution."""

		return min(1.0, base + min(count, 5) * 0.03)

	def _combine_confidence(self, evidence_pool: list[Evidence]) -> float:
		"""Combine evidence relevances into a single bounded confidence score."""

		if not evidence_pool:
			return 0.2
		return max(0.0, min(1.0, sum(e.relevance for e in evidence_pool) / len(evidence_pool)))
