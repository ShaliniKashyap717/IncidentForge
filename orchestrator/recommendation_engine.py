"""Recommendation Engine: Deterministic logic for combining and ranking recommendations."""

from __future__ import annotations

from typing import Any

from models.finding import Finding
from models.hypothesis import Hypothesis
from models.recommendation import Recommendation


def combine_findings(findings: list[Finding]) -> dict[str, Any]:
    """Combine multiple findings into a single coherent summary.

    Args:
        findings: List of Finding objects from different agents.

    Returns:
        Dictionary with combined summary, consensus confidence, and notable findings.
    """
    if not findings:
        return {
            "summary": "No findings available.",
            "confidence": 0.0,
            "agent_count": 0,
            "findings_by_agent": [],
        }

    avg_confidence = sum(f.confidence for f in findings) / len(findings)
    agents = {f.agent for f in findings}

    findings_by_agent = [
        {
            "agent": f.agent,
            "summary": f.summary,
            "confidence": f.confidence,
            "hypothesis": f.hypothesis,
        }
        for f in findings
    ]

    return {
        "summary": f"Consensus from {len(agents)} agent(s): Multiple evidence sources identify system behavior anomalies.",
        "confidence": avg_confidence,
        "agent_count": len(agents),
        "findings_by_agent": findings_by_agent,
    }


def rank_recommendations(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Rank recommendations by confidence and urgency.

    Args:
        recommendations: List of Recommendation objects.

    Returns:
        List of recommendations sorted by confidence (highest first).
    """
    return sorted(recommendations, key=lambda r: r.confidence, reverse=True)


def merge_hypotheses(hypotheses: list[Hypothesis]) -> list[Hypothesis]:
    """Merge similar hypotheses, combining supporting evidence.

    Two hypotheses are considered similar if their descriptions overlap significantly
    (simple substring matching for now).

    Args:
        hypotheses: List of Hypothesis objects.

    Returns:
        List of deduplicated hypotheses with merged evidence.
    """
    if not hypotheses:
        return []

    merged: list[Hypothesis] = []

    for hyp in hypotheses:
        similar_idx = None

        for idx, merged_hyp in enumerate(merged):
            if _hypotheses_similar(hyp.description, merged_hyp.description):
                similar_idx = idx
                break

        if similar_idx is not None:
            merged[similar_idx] = _merge_two_hypotheses(merged[similar_idx], hyp)
        else:
            merged.append(hyp)

    return merged


def _hypotheses_similar(desc1: str, desc2: str, overlap_threshold: float = 0.4) -> bool:
    """Check if two hypothesis descriptions are similar.

    Uses a simple word overlap metric.

    Args:
        desc1: First hypothesis description.
        desc2: Second hypothesis description.
        overlap_threshold: Fraction of common words required (0.0 to 1.0).

    Returns:
        True if hypotheses are similar, False otherwise.
    """
    words1 = set(desc1.lower().split())
    words2 = set(desc2.lower().split())

    if not words1 or not words2:
        return desc1.lower() == desc2.lower()

    overlap = len(words1 & words2) / max(len(words1), len(words2))
    return overlap >= overlap_threshold


def _merge_two_hypotheses(hyp1: Hypothesis, hyp2: Hypothesis) -> Hypothesis:
    """Merge two similar hypotheses into one.

    Args:
        hyp1: First hypothesis.
        hyp2: Second hypothesis.

    Returns:
        Merged hypothesis with combined evidence and averaged confidence.
    """
    combined_confidence = (hyp1.confidence + hyp2.confidence) / 2

    combined_supporting = hyp1.supporting_evidence + hyp2.supporting_evidence
    combined_contradicting = hyp1.contradicting_evidence + hyp2.contradicting_evidence

    merged_description = f"{hyp1.description} (corroborated)"

    return Hypothesis(
        description=merged_description,
        confidence=combined_confidence,
        supporting_evidence=combined_supporting,
        contradicting_evidence=combined_contradicting,
        status="active",
    )


def detect_conflicting_conclusions(findings: list[Finding]) -> list[tuple[Finding, Finding]]:
    """Identify pairs of findings with contradictory hypotheses.

    Args:
        findings: List of Finding objects.

    Returns:
        List of tuples representing conflicting finding pairs.
    """
    conflicts: list[tuple[Finding, Finding]] = []

    for i, finding1 in enumerate(findings):
        for finding2 in findings[i + 1 :]:
            if _hypotheses_contradict(finding1.hypothesis, finding2.hypothesis):
                conflicts.append((finding1, finding2))

    return conflicts


def _hypotheses_contradict(hyp1: str, hyp2: str) -> bool:
    """Check if two hypotheses are contradictory.

    Simple heuristic: hypotheses with no word overlap are considered contradictory.

    Args:
        hyp1: First hypothesis string.
        hyp2: Second hypothesis string.

    Returns:
        True if hypotheses contradict, False otherwise.
    """
    words1 = set(hyp1.lower().split())
    words2 = set(hyp2.lower().split())

    if not words1 or not words2:
        return hyp1.lower() != hyp2.lower()

    overlap = len(words1 & words2) / max(len(words1), len(words2))
    return overlap < 0.2


def generate_composite_recommendation(
    findings: list[Finding],
    hypotheses: list[Hypothesis],
) -> Recommendation:
    """Generate a composite recommendation from multiple findings and hypotheses.

    Args:
        findings: List of findings from various agents.
        hypotheses: List of hypotheses being evaluated.

    Returns:
        A single composite Recommendation object.
    """
    if not findings:
        return Recommendation(
            action="Collect additional telemetry data.",
            rationale="No evidence available yet.",
            risk="Low",
            confidence=0.3,
            requires_approval=False,
        )

    avg_confidence = sum(f.confidence for f in findings) / len(findings)

    top_hypothesis = max(hypotheses, key=lambda h: h.confidence).description if hypotheses else "Unknown"

    action = f"Investigate {top_hypothesis} based on collected evidence."

    rationale = f"Multiple agents have identified consistent patterns with average confidence {avg_confidence:.2%}."

    risk = "Medium" if avg_confidence < 0.7 else "Low"

    requires_approval = avg_confidence < 0.8

    return Recommendation(
        action=action,
        rationale=rationale,
        risk=risk,
        confidence=avg_confidence,
        requires_approval=requires_approval,
    )
