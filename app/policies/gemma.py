from typing import List
from app.models.internal_messages import InternalMessage
from app.policies.base import MessagePolicy

class GemmaPolicy(MessagePolicy):
    """
    Normalization policy for Gemma model family.
    Strictly alternates user and assistant roles.
    """

    @property
    def family(self) -> str:
        return "gemma"

    @property
    def policy_name(self) -> str:
        return "gemma-strict-v1"

    def detect(self, model: str) -> bool:
        return model.lower().startswith("gemma")

    def normalize(self, messages: List[InternalMessage]) -> List[InternalMessage]:
        # 1. Strip empty/whitespace messages
        messages = [m for m in messages if m.content and m.content.strip()]

        if not messages:
            return []

        # 2. Serialize unsupported roles and fold into adjacent user/assistant
        processed_messages: List[InternalMessage] = []
        for msg in messages:
            if msg.role in ["system", "developer"]:
                # We will handle folding system into the first user later
                processed_messages.append(msg)
            elif msg.role in ["tool", "function", "observation"]:
                # Serialize and append as a marker that will be merged
                name_str = f": {msg.name}" if msg.name else ""
                serialized_content = f"[{msg.role}{name_str}]\n{msg.content}"
                processed_messages.append(InternalMessage(role="user", content=serialized_content))
            else:
                processed_messages.append(msg)

        if not processed_messages:
            return []

        # 3. Handle System Folding
        # If the first message(s) are system/developer, fold them into the first 'user' message
        # If no user message exists, create one
        final_messages: List[InternalMessage] = []
        system_buffer = []
        
        # Collect initial system/developer messages
        idx = 0
        while idx < len(processed_messages) and processed_messages[idx].role in ["system", "developer"]:
            system_buffer.append(processed_messages[idx].content)
            idx += 1
        
        if system_buffer:
            system_content = "\n\n".join(system_buffer)
            if idx < len(processed_messages) and processed_messages[idx].role == "user":
                # Fold into existing first user
                processed_messages[idx].content = f"{system_content}\n\n{processed_messages[idx].content}"
            else:
                # Create a new user message at the front
                new_user = InternalMessage(role="user", content=system_content)
                processed_messages.insert(idx, new_user)
            
            # Remove the folded system messages
            processed_messages = processed_messages[idx:]

        # 4. Merge Consecutive Roles
        merged_messages: List[InternalMessage] = []
        for msg in processed_messages:
            # Map system/developer to user if they appear late (though usually handled above)
            role = "user" if msg.role in ["system", "developer"] else msg.role
            
            if not merged_messages or merged_messages[-1].role != role:
                merged_messages.append(InternalMessage(role=role, content=msg.content))
            else:
                merged_messages[-1].content += f"\n\n{msg.content}"

        return merged_messages

    def validate(self, messages: List[InternalMessage]) -> bool:
        """
        Gemma Validation Rules:
        1. Must alternate user/assistant/user...
        2. Must start with 'user' (per most strict llama.cpp templates for Gemma)
        """
        if not messages:
            return True # Empty is technically valid but rare
            
        if messages[0].role != "user":
            return False
            
        for i in range(1, len(messages)):
            if messages[i].role == messages[i-1].role:
                return False
            if messages[i].role not in ["user", "assistant"]:
                return False
                
        return True
