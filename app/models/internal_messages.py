from typing import Optional, Literal
from pydantic import BaseModel, Field

# Allowed roles internally
InternalRole = Literal[
    "system",
    "developer",
    "user",
    "assistant",
    "tool",
    "function",
    "observation",
]

class InternalMessage(BaseModel):
    """
    Internal message representation used by the normalization pipeline.
    """
    role: InternalRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
