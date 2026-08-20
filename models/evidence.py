"""
Data models representing evidence collected during an incident investigation.
"""

from enum import Enum

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    LOG = "log"
    METRIC = "metric"
    TRACE = "trace"
    CODE = "code"
    DEPLOYMENT = "deployment"
    DATABASE = "database"
    DOCUMENTATION = "documentation"
    SECURITY = "security"


class Evidence(BaseModel):
    """
    A single piece of evidence collected during an investigation.
    """

    type: EvidenceType
    source: str = Field(description="System or tool that produced the evidence.")
    description: str
    timestamp: str | None = None
    relevance: float = Field(ge=0.0, le=1.0)