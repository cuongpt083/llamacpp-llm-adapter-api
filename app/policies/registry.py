from typing import Dict, List, Type, Optional
from app.policies.base import MessagePolicy
from app.policies.gemma import GemmaPolicy
from app.policies.passthrough import PassthroughPolicy

class PolicyRegistry:
    """
    Registry for all message normalization policies.
    """
    def __init__(self):
        self._policies: List[MessagePolicy] = []
        self._default_policy = PassthroughPolicy()
        
        # Initial registration
        # Order matters: more specific policies first
        self.register(GemmaPolicy())
        self.register(self._default_policy)

    def register(self, policy: MessagePolicy):
        """Register a new policy."""
        # Append to the end, but we will iterate and take first match
        # To make specific policies win, we should either insert at 0
        # or have the default at the very end.
        self._policies.append(policy)

    def get_policy_for_model(self, model: str) -> MessagePolicy:
        """Find the best policy for a given model string."""
        for policy in self._policies:
            # Skip the default passthrough during specific detection
            if policy.policy_name == "passthrough-v1":
                continue
            if policy.detect(model):
                return policy
        return self._default_policy

    def get_policy_by_name(self, name: str) -> Optional[MessagePolicy]:
        """Get a policy by its unique name."""
        for policy in self._policies:
            if policy.policy_name == name:
                return policy
        return None

# Singleton instance
registry = PolicyRegistry()
