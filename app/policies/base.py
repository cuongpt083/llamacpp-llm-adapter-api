from abc import ABC, abstractmethod
from typing import List
from app.models.internal_messages import InternalMessage

class MessagePolicy(ABC):
    """
    Abstract base class for all message normalization policies.
    """
    
    @property
    @abstractmethod
    def family(self) -> str:
        """The model family this policy belongs to (e.g., 'gemma')."""
        pass

    @property
    @abstractmethod
    def policy_name(self) -> str:
        """The unique name of this policy (e.g., 'gemma-strict-v1')."""
        pass

    @abstractmethod
    def detect(self, model: str) -> bool:
        """Check if this policy should be applied to the given model string."""
        pass

    @abstractmethod
    def normalize(self, messages: List[InternalMessage]) -> List[InternalMessage]:
        """Apply normalization rules to the message sequence."""
        pass

    @abstractmethod
    def validate(self, messages: List[InternalMessage]) -> bool:
        """Validate that the message sequence is compatible with the model family."""
        pass
