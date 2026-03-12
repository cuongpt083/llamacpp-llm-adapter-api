from typing import List
from app.models.internal_messages import InternalMessage
from app.policies.base import MessagePolicy

class PassthroughPolicy(MessagePolicy):
    """
    Default policy that does no transformation.
    """

    @property
    def family(self) -> str:
        return "passthrough"

    @property
    def policy_name(self) -> str:
        return "passthrough-v1"

    def detect(self, model: str) -> bool:
        # This is typically the fallback, but can detect specific prefixes if needed
        return True

    def normalize(self, messages: List[InternalMessage]) -> List[InternalMessage]:
        return messages

    def validate(self, messages: List[InternalMessage]) -> bool:
        return True
