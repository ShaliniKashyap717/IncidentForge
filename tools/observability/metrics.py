"""Metrics analysis helpers for observability tooling."""

from __future__ import annotations

from statistics import mean, stdev


def compute_statistics(values: list[float]) -> dict[str, float]:
    """Compute basic statistics over a list of numeric values.

    Args:
        values: List of numeric metric values.

    Returns:
        Dictionary with 'min', 'max', 'average', and optionally 'stddev' keys.
    """
    if not values:
        return {"min": 0.0, "max": 0.0, "average": 0.0}

    stats = {
        "min": min(values),
        "max": max(values),
        "average": mean(values),
    }

    if len(values) > 1:
        stats["stddev"] = stdev(values)

    return stats


def detect_spike(
    baseline: float,
    current: float,
    threshold_multiplier: float = 2.0,
) -> bool:
    """Detect if a current value represents a spike above the baseline.

    Args:
        baseline: The expected/normal metric value.
        current: The observed metric value.
        threshold_multiplier: The multiplier above baseline to trigger a spike (default 2.0x).

    Returns:
        True if current value is a spike, False otherwise.
    """
    if baseline <= 0:
        return current > 0

    return current >= (baseline * threshold_multiplier)


def calculate_percentage_change(before: float, after: float) -> float:
    """Calculate the percentage change from before to after.

    Args:
        before: The starting value.
        after: The ending value.

    Returns:
        The percentage change (positive = increase, negative = decrease).
    """
    if before == 0:
        return 0.0 if after == 0 else 100.0

    return ((after - before) / before) * 100


def identify_anomaly_window(
    series: list[dict[str, float | str]],
    key: str = "value",
    spike_threshold: float = 2.0,
) -> dict[str, int | float | None]:
    """Identify the time window where a metric anomaly (spike) occurs.

    Args:
        series: List of metric data points, each with a 'timestamp' and numeric key.
        key: The key name for the metric value in each data point (default 'value').
        spike_threshold: The multiplier above the baseline to detect a spike.

    Returns:
        Dictionary with 'start_idx', 'end_idx', 'max_value', and 'baseline' keys.
        Returns None values if no anomaly is detected.
    """
    if not series or len(series) < 2:
        return {"start_idx": None, "end_idx": None, "max_value": None, "baseline": None}

    values = [float(point.get(key, 0)) for point in series]

    baseline = sum(values[:2]) / 2 if len(values) >= 2 else values[0]

    anomaly_start = None
    anomaly_end = None
    max_anomaly_value = baseline

    for idx, value in enumerate(values):
        is_spiking = detect_spike(baseline, value, spike_threshold)

        if is_spiking and anomaly_start is None:
            anomaly_start = idx

        if anomaly_start is not None:
            max_anomaly_value = max(max_anomaly_value, value)

            if not is_spiking and anomaly_start is not None:
                anomaly_end = idx - 1
                break

    if anomaly_start is not None and anomaly_end is None:
        anomaly_end = len(values) - 1

    return {
        "start_idx": anomaly_start,
        "end_idx": anomaly_end,
        "max_value": max_anomaly_value if anomaly_start is not None else None,
        "baseline": baseline,
    }
