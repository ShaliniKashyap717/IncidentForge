"""
Models representing the investigation process.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from models.finding import Finding
from models.hypothesis import Hypothesis


class Investigation(BaseModel):
    """
    Tracks the progress and results of an incident investigation.
    """

    started_at: datetime

    findings: list[Finding] = Field(
        default_factory=list
    )

    hypotheses: list[Hypothesis] = Field(
        default_factory=list
    )

    investigation_steps: list[str] = Field(
        default_factory=list
    )