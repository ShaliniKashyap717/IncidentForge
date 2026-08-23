"""Trace analysis helpers for observability tooling."""

from __future__ import annotations

from typing import Any


def identify_slow_spans(
    traces: list[dict[str, Any]],
    latency_threshold_ms: float = 1000.0,
) -> list[dict[str, Any]]:
    """Identify all spans across traces that exceed the latency threshold.

    Args:
        traces: List of trace objects, each containing a 'slow_spans' list.
        latency_threshold_ms: Threshold in milliseconds to consider a span "slow".

    Returns:
        List of slow spans found, each with service, name, and duration_ms.
    """
    slow_spans = []

    for trace in traces:
        for span in trace.get("slow_spans", []):
            if span.get("duration_ms", 0) >= latency_threshold_ms:
                slow_spans.append(span)

    return slow_spans


def identify_bottleneck_services(
    traces: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Identify services that are bottlenecks by aggregating their latency across traces.

    Args:
        traces: List of trace objects with 'slow_spans' containing service/duration_ms.

    Returns:
        Dictionary mapping service name to stats including 'total_time_ms', 'occurrence_count', 'avg_duration_ms'.
    """
    service_stats: dict[str, dict[str, float | int]] = {}

    for trace in traces:
        for span in trace.get("slow_spans", []):
            service = span.get("service", "unknown")
            duration = float(span.get("duration_ms", 0))

            if service not in service_stats:
                service_stats[service] = {
                    "total_time_ms": 0.0,
                    "occurrence_count": 0,
                    "avg_duration_ms": 0.0,
                }

            service_stats[service]["total_time_ms"] += duration
            service_stats[service]["occurrence_count"] += 1

    for service, stats in service_stats.items():
        count = stats["occurrence_count"]
        if count > 0:
            stats["avg_duration_ms"] = stats["total_time_ms"] / count

    return service_stats


def rank_services_by_latency(
    traces: list[dict[str, Any]],
) -> list[tuple[str, float]]:
    """Rank services by total latency contribution across all traces.

    Args:
        traces: List of trace objects with 'slow_spans' containing service/duration_ms.

    Returns:
        List of (service_name, total_latency_ms) tuples, sorted by latency descending.
    """
    service_totals: dict[str, float] = {}

    for trace in traces:
        for span in trace.get("slow_spans", []):
            service = span.get("service", "unknown")
            duration = float(span.get("duration_ms", 0))
            service_totals[service] = service_totals.get(service, 0.0) + duration

    ranked = sorted(service_totals.items(), key=lambda x: x[1], reverse=True)
    return ranked


def summarize_trace_dependencies(
    traces: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Summarize the dependency chain and error patterns for each trace.

    Args:
        traces: List of trace objects with 'dependencies', 'status', 'latency_ms'.

    Returns:
        Dictionary mapping trace_id to a summary with 'latency_ms', 'status', 'service_chain', 'error_flag'.
    """
    summaries: dict[str, dict[str, Any]] = {}

    for trace in traces:
        trace_id = trace.get("trace_id", "unknown")
        latency = trace.get("latency_ms", 0)
        status = trace.get("status", "unknown")
        dependencies = trace.get("dependencies", [])
        is_error = status != "ok"

        summaries[trace_id] = {
            "latency_ms": latency,
            "status": status,
            "service_chain": " -> ".join(dependencies) if dependencies else "unknown",
            "error_flag": is_error,
        }

    return summaries
