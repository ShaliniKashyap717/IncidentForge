"""
Models representing remediation recommendations.
"""

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    """
    A proposed action for mitigating or resolving an incident.
    """

    action: str

    rationale: str

    risk: str

    confidence: float = Field(ge=0.0, le=1.0)

    requires_approval: bool = True