"""Tool bindings for the database agent."""

from __future__ import annotations

from typing import Any

from google.adk.tools import FunctionTool

from tools.database.locks import (
	detect_lock_signals_from_logs,
	infer_contention_from_spans,
	summarize_lock_signals,
)
from tools.database.metrics import (
	correlate_database_latency_with_incident,
	detect_database_latency_anomaly,
	estimate_database_latency_metrics,
)
from tools.database.queries import (
	extract_database_spans,
	find_slow_queries,
	list_query_names,
	summarize_query_performance,
)


def analyze_database_queries(traces_payload: dict[str, Any]) -> dict[str, Any]:
	"""Analyze database query behavior from trace spans."""

	database_spans = extract_database_spans(traces_payload)
	slow_queries = find_slow_queries(database_spans)
	summary = summarize_query_performance(database_spans)

	return {
		"database_spans": database_spans,
		"slow_queries": slow_queries,
		"query_names": list_query_names(database_spans),
		"summary": summary,
	}


def analyze_database_locks(
	logs: list[dict[str, Any]],
	database_spans: list[dict[str, Any]],
) -> dict[str, Any]:
	"""Analyze lock and contention indicators from logs and spans."""

	lock_logs = detect_lock_signals_from_logs(logs)
	contention = infer_contention_from_spans(database_spans)

	return {
		"lock_logs": lock_logs,
		"lock_summary": summarize_lock_signals(lock_logs),
		"contention": contention,
	}


def analyze_database_metrics(
	database_spans: list[dict[str, Any]],
	incident_title: str,
) -> dict[str, Any]:
	"""Analyze database latency metrics and incident correlation."""

	metrics = estimate_database_latency_metrics(database_spans)
	anomaly = detect_database_latency_anomaly(metrics)
	correlation = correlate_database_latency_with_incident(database_spans, incident_title)

	return {
		"metrics": metrics,
		"anomaly": anomaly,
		"correlation": correlation,
	}


def build_database_tools() -> list[FunctionTool]:
	"""Build ADK function tools for database analysis."""

	return [
		FunctionTool(analyze_database_queries),
		FunctionTool(analyze_database_locks),
		FunctionTool(analyze_database_metrics),
	]
