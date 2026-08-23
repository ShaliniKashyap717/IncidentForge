"""Tests for observability tools: logs, metrics, and traces."""

import pytest

from tools.observability.logs import count_errors, search_logs, summarize_events
from tools.observability.metrics import (
    calculate_percentage_change,
    compute_statistics,
    detect_spike,
    identify_anomaly_window,
)
from tools.observability.traces import (
    identify_bottleneck_services,
    identify_slow_spans,
    rank_services_by_latency,
    summarize_trace_dependencies,
)


# ==== LOG TESTS ====


class TestLogSearch:
    def test_search_by_query_substring(self):
        logs = [
            {"timestamp": "2026-08-21T12:00:00Z", "severity": "INFO", "service": "api", "message": "request started"},
            {"timestamp": "2026-08-21T12:01:00Z", "severity": "ERROR", "service": "api", "message": "connection timeout"},
        ]

        results = search_logs(logs, query="timeout")
        assert len(results) == 1
        assert results[0]["message"] == "connection timeout"

    def test_search_by_service(self):
        logs = [
            {"timestamp": "2026-08-21T12:00:00Z", "severity": "INFO", "service": "api", "message": "ok"},
            {"timestamp": "2026-08-21T12:01:00Z", "severity": "ERROR", "service": "db", "message": "error"},
        ]

        results = search_logs(logs, service="api")
        assert len(results) == 1
        assert results[0]["service"] == "api"

    def test_search_by_severity(self):
        logs = [
            {"timestamp": "2026-08-21T12:00:00Z", "severity": "INFO", "service": "api", "message": "ok"},
            {"timestamp": "2026-08-21T12:01:00Z", "severity": "ERROR", "service": "api", "message": "error"},
        ]

        results = search_logs(logs, severity="ERROR")
        assert len(results) == 1
        assert results[0]["severity"] == "ERROR"

    def test_search_combined_filters(self):
        logs = [
            {"timestamp": "2026-08-21T12:00:00Z", "severity": "INFO", "service": "api", "message": "ok"},
            {"timestamp": "2026-08-21T12:01:00Z", "severity": "ERROR", "service": "api", "message": "timeout"},
            {"timestamp": "2026-08-21T12:02:00Z", "severity": "ERROR", "service": "db", "message": "timeout"},
        ]

        results = search_logs(logs, service="api", severity="ERROR", query="timeout")
        assert len(results) == 1
        assert results[0]["service"] == "api"

    def test_search_case_insensitive(self):
        logs = [
            {"timestamp": "2026-08-21T12:00:00Z", "severity": "error", "service": "API", "message": "Timeout occurred"},
        ]

        results = search_logs(logs, service="api", severity="ERROR", query="TIMEOUT")
        assert len(results) == 1

    def test_search_empty_logs(self):
        results = search_logs([], query="test")
        assert results == []


class TestErrorCounting:
    def test_count_errors_all_severities(self):
        logs = [
            {"timestamp": "2026-08-21T12:00:00Z", "severity": "ERROR", "service": "api", "message": "error1"},
            {"timestamp": "2026-08-21T12:01:00Z", "severity": "WARN", "service": "api", "message": "warn1"},
            {"timestamp": "2026-08-21T12:02:00Z", "severity": "CRITICAL", "service": "api", "message": "critical1"},
            {"timestamp": "2026-08-21T12:03:00Z", "severity": "INFO", "service": "api", "message": "info1"},
        ]

        counts = count_errors(logs)
        assert counts["ERROR"] == 1
        assert counts["WARN"] == 1
        assert counts["CRITICAL"] == 1
        assert "INFO" not in counts

    def test_count_errors_by_service(self):
        logs = [
            {"timestamp": "2026-08-21T12:00:00Z", "severity": "ERROR", "service": "api", "message": "error1"},
            {"timestamp": "2026-08-21T12:01:00Z", "severity": "ERROR", "service": "api", "message": "error2"},
            {"timestamp": "2026-08-21T12:02:00Z", "severity": "ERROR", "service": "db", "message": "error3"},
        ]

        counts = count_errors(logs, service="api")
        assert counts["ERROR"] == 2

    def test_count_errors_empty(self):
        counts = count_errors([])
        assert counts == {}


class TestEventSummarization:
    def test_summarize_all_events(self):
        logs = [
            {"timestamp": "2026-08-21T12:00:00Z", "severity": "INFO", "service": "api", "message": "started"},
            {"timestamp": "2026-08-21T12:01:00Z", "severity": "ERROR", "service": "db", "message": "failed"},
        ]

        summaries = summarize_events(logs)
        assert len(summaries) == 2
        assert "2026-08-21T12:00:00Z [api] started" in summaries
        assert "2026-08-21T12:01:00Z [db] failed" in summaries

    def test_summarize_with_predicate(self):
        logs = [
            {"timestamp": "2026-08-21T12:00:00Z", "severity": "INFO", "service": "api", "message": "ok"},
            {"timestamp": "2026-08-21T12:01:00Z", "severity": "ERROR", "service": "db", "message": "error"},
        ]

        summaries = summarize_events(logs, predicate=lambda e: e.get("severity") == "ERROR")
        assert len(summaries) == 1
        assert "error" in summaries[0]


# ==== METRICS TESTS ====


class TestStatistics:
    def test_compute_statistics_basic(self):
        values = [10.0, 20.0, 30.0]
        stats = compute_statistics(values)

        assert stats["min"] == 10.0
        assert stats["max"] == 30.0
        assert stats["average"] == 20.0
        assert "stddev" in stats

    def test_compute_statistics_single_value(self):
        stats = compute_statistics([42.0])
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0
        assert stats["average"] == 42.0
        assert "stddev" not in stats

    def test_compute_statistics_empty(self):
        stats = compute_statistics([])
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0
        assert stats["average"] == 0.0


class TestSpikeDetection:
    def test_detect_spike_above_threshold(self):
        assert detect_spike(baseline=100.0, current=250.0, threshold_multiplier=2.0) is True

    def test_detect_spike_below_threshold(self):
        assert detect_spike(baseline=100.0, current=150.0, threshold_multiplier=2.0) is False

    def test_detect_spike_at_threshold(self):
        assert detect_spike(baseline=100.0, current=200.0, threshold_multiplier=2.0) is True

    def test_detect_spike_custom_multiplier(self):
        assert detect_spike(baseline=100.0, current=350.0, threshold_multiplier=3.0) is True
        assert detect_spike(baseline=100.0, current=250.0, threshold_multiplier=3.0) is False

    def test_detect_spike_zero_baseline(self):
        assert detect_spike(baseline=0.0, current=1.0) is True
        assert detect_spike(baseline=0.0, current=0.0) is False


class TestPercentageChange:
    def test_percentage_increase(self):
        change = calculate_percentage_change(before=100.0, after=150.0)
        assert change == 50.0

    def test_percentage_decrease(self):
        change = calculate_percentage_change(before=100.0, after=50.0)
        assert change == -50.0

    def test_percentage_no_change(self):
        change = calculate_percentage_change(before=100.0, after=100.0)
        assert change == 0.0

    def test_percentage_from_zero(self):
        change = calculate_percentage_change(before=0.0, after=100.0)
        assert change == 100.0

    def test_percentage_both_zero(self):
        change = calculate_percentage_change(before=0.0, after=0.0)
        assert change == 0.0


class TestAnomalyWindow:
    def test_identify_anomaly_window_spike(self):
        series = [
            {"timestamp": "2026-08-21T12:00:00Z", "value": 100},
            {"timestamp": "2026-08-21T12:01:00Z", "value": 110},
            {"timestamp": "2026-08-21T12:02:00Z", "value": 400},
            {"timestamp": "2026-08-21T12:03:00Z", "value": 450},
            {"timestamp": "2026-08-21T12:04:00Z", "value": 120},
        ]

        result = identify_anomaly_window(series, spike_threshold=2.0)
        assert result["start_idx"] == 2
        assert result["end_idx"] == 3
        assert result["max_value"] == 450
        assert result["baseline"] == 105.0

    def test_identify_anomaly_window_no_spike(self):
        series = [
            {"timestamp": "2026-08-21T12:00:00Z", "value": 100},
            {"timestamp": "2026-08-21T12:01:00Z", "value": 110},
            {"timestamp": "2026-08-21T12:02:00Z", "value": 120},
        ]

        result = identify_anomaly_window(series, spike_threshold=2.0)
        assert result["start_idx"] is None

    def test_identify_anomaly_window_empty(self):
        result = identify_anomaly_window([])
        assert result["start_idx"] is None


# ==== TRACE TESTS ====


class TestSlowSpans:
    def test_identify_slow_spans(self):
        traces = [
            {
                "trace_id": "t1",
                "slow_spans": [
                    {"service": "api", "name": "request", "duration_ms": 1500},
                    {"service": "db", "name": "query", "duration_ms": 500},
                ],
            },
            {
                "trace_id": "t2",
                "slow_spans": [
                    {"service": "cache", "name": "miss", "duration_ms": 1200},
                ],
            },
        ]

        slow = identify_slow_spans(traces, latency_threshold_ms=1000.0)
        assert len(slow) == 2
        assert slow[0]["service"] == "api"
        assert slow[1]["service"] == "cache"

    def test_identify_slow_spans_threshold(self):
        traces = [
            {
                "trace_id": "t1",
                "slow_spans": [
                    {"service": "api", "name": "request", "duration_ms": 500},
                    {"service": "db", "name": "query", "duration_ms": 2000},
                ],
            },
        ]

        slow = identify_slow_spans(traces, latency_threshold_ms=1000.0)
        assert len(slow) == 1
        assert slow[0]["service"] == "db"

    def test_identify_slow_spans_empty(self):
        slow = identify_slow_spans([])
        assert slow == []


class TestBottleneckServices:
    def test_identify_bottleneck_services(self):
        traces = [
            {
                "trace_id": "t1",
                "slow_spans": [
                    {"service": "api", "name": "request", "duration_ms": 1000},
                    {"service": "db", "name": "query", "duration_ms": 2000},
                ],
            },
            {
                "trace_id": "t2",
                "slow_spans": [
                    {"service": "db", "name": "query", "duration_ms": 1800},
                ],
            },
        ]

        bottlenecks = identify_bottleneck_services(traces)
        assert "db" in bottlenecks
        assert bottlenecks["db"]["total_time_ms"] == 3800.0
        assert bottlenecks["db"]["occurrence_count"] == 2
        assert bottlenecks["db"]["avg_duration_ms"] == 1900.0

    def test_identify_bottleneck_services_empty(self):
        bottlenecks = identify_bottleneck_services([])
        assert bottlenecks == {}


class TestRankServices:
    def test_rank_services_by_latency(self):
        traces = [
            {
                "trace_id": "t1",
                "slow_spans": [
                    {"service": "api", "name": "request", "duration_ms": 1000},
                    {"service": "db", "name": "query", "duration_ms": 3000},
                ],
            },
        ]

        ranked = rank_services_by_latency(traces)
        assert len(ranked) == 2
        assert ranked[0] == ("db", 3000.0)
        assert ranked[1] == ("api", 1000.0)


class TestTraceSummaries:
    def test_summarize_trace_dependencies(self):
        traces = [
            {
                "trace_id": "t1",
                "latency_ms": 5000,
                "status": "error",
                "dependencies": ["checkout-api", "payment-api", "db"],
            },
            {
                "trace_id": "t2",
                "latency_ms": 200,
                "status": "ok",
                "dependencies": ["checkout-api", "cache"],
            },
        ]

        summaries = summarize_trace_dependencies(traces)
        assert summaries["t1"]["latency_ms"] == 5000
        assert summaries["t1"]["status"] == "error"
        assert summaries["t1"]["error_flag"] is True
        assert summaries["t1"]["service_chain"] == "checkout-api -> payment-api -> db"
        assert summaries["t2"]["error_flag"] is False

    def test_summarize_trace_dependencies_empty(self):
        summaries = summarize_trace_dependencies([])
        assert summaries == {}
