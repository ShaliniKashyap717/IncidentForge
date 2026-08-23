"""Integration test: Run observability tools against the payment_latency scenario."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.load_scenarios import load_scenario
from tools.observability import logs, metrics, traces


def main():
    scenario = load_scenario("scenarios/payment_latency")

    print("=== LOGS ANALYSIS ===")
    error_entries = logs.search_logs(scenario["logs"], severity="ERROR")
    print(f"Found {len(error_entries)} error entries")
    for entry in error_entries:
        print(f"  - {entry['timestamp']} [{entry['service']}] {entry['message']}")

    payment_errors = logs.count_errors(scenario["logs"], service="payment-api")
    print(f"\nError counts for payment-api: {payment_errors}")

    print("\n=== METRICS ANALYSIS ===")
    metrics_data = scenario["metrics"]["series"]
    values = [float(point["value"]) for point in metrics_data]
    stats = metrics.compute_statistics(values)
    print(f"Metrics stats: min={stats['min']:.0f}ms, max={stats['max']:.0f}ms, avg={stats['average']:.0f}ms")

    anomaly = metrics.identify_anomaly_window(metrics_data, spike_threshold=2.0)
    print(f"Anomaly window: indices {anomaly['start_idx']}-{anomaly['end_idx']}, peak {anomaly['max_value']:.0f}ms")

    if anomaly["start_idx"] is not None:
        pct_change = metrics.calculate_percentage_change(anomaly["baseline"], anomaly["max_value"])
        print(f"Percentage increase: {pct_change:.1f}%")

    print("\n=== TRACES ANALYSIS ===")
    trace_data = scenario["traces"]["traces"]
    slow = traces.identify_slow_spans(trace_data, latency_threshold_ms=1000)
    print(f"Found {len(slow)} slow spans (>1s):")
    for span in slow:
        print(f"  - {span['service']}: {span['name']} ({span['duration_ms']}ms)")

    ranked = traces.rank_services_by_latency(trace_data)
    print(f"\nServices ranked by latency:")
    for service, latency in ranked:
        print(f"  - {service}: {latency}ms total")

    summaries = traces.summarize_trace_dependencies(trace_data)
    print(f"\nTrace summaries:")
    for trace_id, summary in summaries.items():
        status_label = "FAILED" if summary["error_flag"] else "OK"
        print(f"  {trace_id}: {summary['latency_ms']}ms {status_label} - {summary['service_chain']}")


if __name__ == "__main__":
    main()
