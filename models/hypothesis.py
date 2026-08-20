"""
Models representing candidate root-cause hypotheses.
"""

from pydantic import BaseModel, Field

from models.evidence import Evidence


class Hypothesis(BaseModel):
    """
    A candidate explanation for an incident.
    """

    description: str

    confidence: float = Field(ge=0.0, le=1.0)

    supporting_evidence: list[Evidence] = Field(
        default_factory=list
    )

    contradicting_evidence: list[Evidence] = Field(
        default_factory=list
    )

    status: str = "active"