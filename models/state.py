from pydantic import BaseModel, Field

from models.incident import Incident
from models.investigation import Investigation
from models.recommendation import Recommendation


class IncidentState(BaseModel):
    """
    Shared state passed throughout an incident investigation.
    """

    incident: Incident

    investigation: Investigation

    recommendations: list[Recommendation] = Field(
        default_factory=list
    )