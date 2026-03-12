from typing import List, Optional

from pydantic import BaseModel


class RouteDecision(BaseModel):
    client_requested_model: Optional[str]
    route_label: str
    resolved_model: str
    reasons: List[str]
    fallback_eligible: bool = True
