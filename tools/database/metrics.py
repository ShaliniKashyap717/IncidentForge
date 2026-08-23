"""Database metrics helpers."""

from __future__ import annotations

from typing import Any


def estimate_database_latency_metrics(database_spans: list[dict[str, Any]]) -> dict[str, float]:
	"""Compute basic latency metrics from database spans."""

	if not database_spans:
		return {"min_ms": 0.0, "max_ms": 0.0, "avg_ms": 0.0, "p95_ms": 0.0}

	durations = sorted(float(span.get("duration_ms", 0.0)) for span in database_spans)
	length = len(durations)
	p95_index = max(0, min(length - 1, int(round((length - 1) * 0.95))))

	return {
		"min_ms": durations[0],
		"max_ms": durations[-1],
		"avg_ms": sum(durations) / length,
		"p95_ms": durations[p95_index],
	}


def detect_database_latency_anomaly(
	metrics: dict[str, float],
	max_threshold_ms: float = 1200.0,
	p95_threshold_ms: float = 1000.0,
) -> dict[str, Any]:
	"""Detect obvious database latency anomalies using thresholds."""

	max_ms = float(metrics.get("max_ms", 0.0))
	p95_ms = float(metrics.get("p95_ms", 0.0))
	anomaly = max_ms >= max_threshold_ms or p95_ms >= p95_threshold_ms

	reason = []
	if max_ms >= max_threshold_ms:
		reason.append(f"max latency {max_ms:.0f}ms exceeded {max_threshold_ms:.0f}ms")
	if p95_ms >= p95_threshold_ms:
		reason.append(f"p95 latency {p95_ms:.0f}ms exceeded {p95_threshold_ms:.0f}ms")

	return {
		"is_anomalous": anomaly,
		"reason": "; ".join(reason) if reason else "no threshold breach",
	}


def correlate_database_latency_with_incident(
	database_spans: list[dict[str, Any]],
	incident_title: str,
) -> dict[str, Any]:
	"""Create a simple correlation descriptor between DB latency and incident context."""

	if not database_spans:
		return {
			"correlated": False,
			"description": f"No database spans found to correlate with incident '{incident_title}'.",
		}

	high_latency = [span for span in database_spans if float(span.get("duration_ms", 0.0)) >= 1000.0]
	if high_latency:
		return {
			"correlated": True,
			"description": (
				f"{len(high_latency)} database spans above 1000ms were observed during traces related to "
				f"incident '{incident_title}'."
			),
		}

	return {
		"correlated": False,
		"description": f"Database spans were present but did not exceed 1000ms for incident '{incident_title}'.",
	}
