"""
Core incident model.
"""

from enum import Enum

from pydantic import BaseModel, Field


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"


class Incident(BaseModel):
    """
    Represents a production incident under investigation.
    """

    id: str

    title: str

    description: str

    severity: IncidentSeverity

    affected_services: list[str] = Field(
        default_factory=list
    )

    status: IncidentStatus = IncidentStatus.DETECTED