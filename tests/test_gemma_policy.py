import pytest
from app.models.internal_messages import InternalMessage
from app.policies.gemma import GemmaPolicy

def test_gemma_system_folding():
    """Rule 1 & 2: Fold system/developer into first user."""
    policy = GemmaPolicy()
    messages = [
        InternalMessage(role="system", content="You are a helper"),
        InternalMessage(role="developer", content="Use python"),
        InternalMessage(role="user", content="Hello")
    ]
    normalized = policy.normalize(messages)
    
    assert len(normalized) == 1
    assert normalized[0].role == "user"
    assert "You are a helper" in normalized[0].content
    assert "Use python" in normalized[0].content
    assert "Hello" in normalized[0].content

def test_gemma_consecutive_merge():
    """Rule 4: Merge consecutive identical roles."""
    policy = GemmaPolicy()
    messages = [
        InternalMessage(role="user", content="Part 1"),
        InternalMessage(role="user", content="Part 2"),
        InternalMessage(role="assistant", content="Response"),
        InternalMessage(role="assistant", content="More response")
    ]
    normalized = policy.normalize(messages)
    
    assert len(normalized) == 2
    assert normalized[0].role == "user"
    assert normalized[0].content == "Part 1\n\nPart 2"
    assert normalized[1].role == "assistant"
    assert normalized[1].content == "Response\n\nMore response"

def test_gemma_tool_serialization():
    """Rule 3: Serialize unsupported roles (tool, observation)."""
    policy = GemmaPolicy()
    messages = [
        InternalMessage(role="user", content="Call tool"),
        InternalMessage(role="observation", content="Tool result", name="get_weather"),
        InternalMessage(role="assistant", content="It is sunny")
    ]
    normalized = policy.normalize(messages)
    
    # Observation should be merged into the preceding user message or serialized
    # Based on Gemma strict rules, we merge it into the previous user to keep alternation
    assert len(normalized) == 2
    assert normalized[0].role == "user"
    assert "[observation: get_weather]\nTool result" in normalized[0].content
    assert normalized[1].role == "assistant"

def test_gemma_alternation_validation():
    """Rule 5: Enforce strict user/assistant alternation."""
    policy = GemmaPolicy()
    
    # Valid alternation
    valid = [
        InternalMessage(role="user", content="hi"),
        InternalMessage(role="assistant", content="hello")
    ]
    assert policy.validate(valid) is True
    
    # Invalid: starts with assistant
    invalid_start = [
        InternalMessage(role="assistant", content="hi")
    ]
    assert policy.validate(invalid_start) is False
    
    # Invalid: consecutive roles (though normalize should have fixed this)
    invalid_consecutive = [
        InternalMessage(role="user", content="hi"),
        InternalMessage(role="user", content="hi again")
    ]
    assert policy.validate(invalid_consecutive) is False

def test_gemma_empty_message_removal():
    """Rule 6: Remove empty or whitespace-only messages."""
    policy = GemmaPolicy()
    messages = [
        InternalMessage(role="user", content="hi"),
        InternalMessage(role="assistant", content="  "),
        InternalMessage(role="user", content="next")
    ]
    normalized = policy.normalize(messages)
    
    # After stripping assistant, user + user are merged
    assert len(normalized) == 1
    assert normalized[0].role == "user"
    assert normalized[0].content == "hi\n\nnext"
