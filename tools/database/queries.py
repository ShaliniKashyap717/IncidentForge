"""Database query support helpers."""

from __future__ import annotations

from statistics import mean
from typing import Any


def extract_database_spans(traces_payload: dict[str, Any]) -> list[dict[str, Any]]:
	"""Extract spans that are database-related from distributed traces.

	A span is considered database-related when its service or span name suggests
	database activity.
	"""

	traces = traces_payload.get("traces", [])
	if not isinstance(traces, list):
		raise TypeError("traces payload must contain a list under 'traces'.")

	database_spans: list[dict[str, Any]] = []
	for trace in traces:
		slow_spans = trace.get("slow_spans", [])
		if not isinstance(slow_spans, list):
			continue
		for span in slow_spans:
			service = str(span.get("service", "")).lower()
			name = str(span.get("name", "")).lower()
			if "db" in name or "database" in service or "query" in name:
				database_spans.append(
					{
						"trace_id": trace.get("trace_id"),
						"service": span.get("service"),
						"name": span.get("name"),
						"duration_ms": float(span.get("duration_ms", 0.0)),
						"status": trace.get("status"),
					}
				)
	return database_spans


def find_slow_queries(
	database_spans: list[dict[str, Any]],
	threshold_ms: float = 1000.0,
) -> list[dict[str, Any]]:
	"""Return database spans considered slow by duration threshold."""

	return [span for span in database_spans if float(span.get("duration_ms", 0.0)) >= threshold_ms]


def summarize_query_performance(database_spans: list[dict[str, Any]]) -> dict[str, Any]:
	"""Summarize database query latency from database spans."""

	if not database_spans:
		return {
			"count": 0,
			"min_ms": 0.0,
			"max_ms": 0.0,
			"avg_ms": 0.0,
		}

	durations = [float(span.get("duration_ms", 0.0)) for span in database_spans]
	return {
		"count": len(durations),
		"min_ms": min(durations),
		"max_ms": max(durations),
		"avg_ms": mean(durations),
	}


def list_query_names(database_spans: list[dict[str, Any]]) -> list[str]:
	"""List distinct query/span names in encounter order."""

	names: list[str] = []
	seen: set[str] = set()
	for span in database_spans:
		name = str(span.get("name", "")).strip()
		if name and name not in seen:
			seen.add(name)
			names.append(name)
	return names
