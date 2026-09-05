"""
Models representing remediation recommendations.
"""

from enum import Enum
from pydantic import BaseModel, Field


class RecommendationStatus(str, Enum):
    """Recommendation approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Recommendation(BaseModel):
    """
    A proposed action for mitigating or resolving an incident.
    """

    action: str

    rationale: str

    risk: str

    confidence: float = Field(ge=0.0, le=1.0)

    requires_approval: bool = True

    status: RecommendationStatus = RecommendationStatus.PENDING