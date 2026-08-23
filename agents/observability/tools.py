"""Tool bindings for the observability agent."""

from __future__ import annotations

from typing import Any

from google.adk.tools import FunctionTool

from tools.observability.logs import count_errors, search_logs, summarize_events
from tools.observability.metrics import (
	calculate_percentage_change,
	compute_statistics,
	identify_anomaly_window,
)
from tools.observability.traces import (
	identify_bottleneck_services,
	identify_slow_spans,
	rank_services_by_latency,
	summarize_trace_dependencies,
)


def analyze_logs(
	logs: list[dict[str, Any]],
	query: str | None = None,
	severity: str | None = None,
	service: str | None = None,
) -> dict[str, Any]:
	"""Deterministically analyze log entries for the Observability Agent."""

	matched_logs = search_logs(logs, query=query, severity=severity, service=service)
	important_events = summarize_events(matched_logs)
	error_counts = count_errors(logs, service=service)

	return {
		"matched_logs": matched_logs,
		"important_events": important_events,
		"error_counts": error_counts,
		"total_matches": len(matched_logs),
		"query": query,
		"severity": severity,
		"service": service,
	}


def analyze_metrics(metrics_payload: dict[str, Any]) -> dict[str, Any]:
	"""Deterministically analyze metric series for the Observability Agent."""

	series = metrics_payload.get("series", [])
	values = [float(point.get("value", 0.0)) for point in series]
	statistics = compute_statistics(values)
	anomaly_window = identify_anomaly_window(series)

	percent_change = None
	if anomaly_window["baseline"] is not None and anomaly_window["max_value"] is not None:
		percent_change = calculate_percentage_change(
			float(anomaly_window["baseline"]),
			float(anomaly_window["max_value"]),
		)

	return {
		"service": metrics_payload.get("service"),
		"metric": metrics_payload.get("metric"),
		"unit": metrics_payload.get("unit"),
		"statistics": statistics,
		"anomaly_window": anomaly_window,
		"percentage_change": percent_change,
		"series": series,
		"anomaly": metrics_payload.get("anomaly"),
	}


def analyze_traces(traces_payload: dict[str, Any]) -> dict[str, Any]:
	"""Deterministically analyze distributed traces for the Observability Agent."""

	trace_items = traces_payload.get("traces", [])
	slow_spans = identify_slow_spans(trace_items)
	bottlenecks = identify_bottleneck_services(trace_items)
	ranked_services = rank_services_by_latency(trace_items)
	dependency_summaries = summarize_trace_dependencies(trace_items)

	return {
		"service": traces_payload.get("service"),
		"slow_spans": slow_spans,
		"bottlenecks": bottlenecks,
		"ranked_services": ranked_services,
		"dependency_summaries": dependency_summaries,
		"trace_count": len(trace_items),
	}


def build_observability_tools() -> list[FunctionTool]:
	"""Build ADK FunctionTool wrappers around deterministic observability analyzers."""

	return [
		FunctionTool(analyze_logs),
		FunctionTool(analyze_metrics),
		FunctionTool(analyze_traces),
	]
