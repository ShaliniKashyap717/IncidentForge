"""
Structured findings produced by specialized engineering agents.
"""

from pydantic import BaseModel, Field

from models.evidence import Evidence


class Finding(BaseModel):
    """
    A structured conclusion produced by an investigation agent.
    """

    agent: str
    summary: str
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)

    evidence: list[Evidence] = Field(default_factory=list)

    next_actions: list[str] = Field(default_factory=list)