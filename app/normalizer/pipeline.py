from typing import List, Dict, Any
from pydantic import BaseModel
from app.models.internal_messages import InternalMessage, InternalRole
from app.models.api_models import ChatCompletionMessage
from app.policies.registry import registry

class NormalizationResult(BaseModel):
    family: str
    policy: str
    model: str
    original_messages: List[ChatCompletionMessage]
    normalized_messages: List[InternalMessage]
    transform_log: List[str]
    validation_result: bool

class NormalizationPipeline:
    """
    Orchestrates the conversion and normalization of messages.
    """
    
    def process(self, model: str, messages: List[ChatCompletionMessage]) -> NormalizationResult:
        transform_log = []
        
        # 1. Detect Policy
        policy = registry.get_policy_for_model(model)
        transform_log.append(f"Detected policy: {policy.policy_name} for model: {model}")
        
        # 2. Convert to Internal Messages
        internal_messages = self._convert_to_internal(messages)
        transform_log.append(f"Converted {len(messages)} API messages to internal format")
        
        # 3. Apply Normalization
        normalized = policy.normalize(internal_messages)
        transform_log.append(f"Applied normalization: {len(internal_messages)} -> {len(normalized)} messages")
        
        # 4. Validate
        is_valid = policy.validate(normalized)
        transform_log.append(f"Validation result: {is_valid}")
        
        return NormalizationResult(
            family=policy.family,
            policy=policy.policy_name,
            model=model,
            original_messages=messages,
            normalized_messages=normalized,
            transform_log=transform_log,
            validation_result=is_valid
        )

    def _convert_to_internal(self, messages: List[ChatCompletionMessage]) -> List[InternalMessage]:
        internal = []
        for m in messages:
            # Map API roles to internal roles
            # OpenAI roles: system, user, assistant, tool, function
            # Internal roles: system, developer, user, assistant, tool, function, observation
            
            role_map = {
                "system": "system",
                "developer": "developer",
                "user": "user",
                "assistant": "assistant",
                "tool": "tool",
                "function": "function"
            }
            
            internal_role: InternalRole = role_map.get(m.role, "user") # Default to user if unknown
            
            internal.append(InternalMessage(
                role=internal_role,
                content=m.content or "",
                name=m.name,
                tool_call_id=m.tool_call_id
            ))
        return internal
