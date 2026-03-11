import pytest
from pydantic import ValidationError
from app.models.internal_messages import InternalMessage

from app.models.api_models import (
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    ChatCompletionMessage
)

def test_internal_message_valid_roles():
    """Test creating InternalMessage with all allowed roles."""
    allowed_roles = [
        "system",
        "developer",
        "user",
        "assistant",
        "tool",
        "function",
        "observation",
    ]
    for role in allowed_roles:
        msg = InternalMessage(role=role, content=f"Hello from {role}")
        assert msg.role == role
        assert msg.content == f"Hello from {role}"
        assert msg.name is None
        assert msg.tool_call_id is None

def test_internal_message_optional_fields():
    """Test InternalMessage with optional name and tool_call_id."""
    msg = InternalMessage(
        role="assistant",
        content="Thinking...",
        name="test_bot",
        tool_call_id="call_123"
    )
    assert msg.name == "test_bot"
    assert msg.tool_call_id == "call_123"

def test_internal_message_invalid_role():
    """Test that invalid roles raise ValidationError."""
    with pytest.raises(ValidationError):
        InternalMessage(role="invalid_role", content="Fail")

def test_internal_message_empty_content():
    """Test InternalMessage allows empty content (to be handled by normalizer later)."""
    msg = InternalMessage(role="user", content="")
    assert msg.content == ""

def test_openai_request_validation():
    """Test that OpenAIChatCompletionRequest validates model and messages."""
    # Valid request
    req = OpenAIChatCompletionRequest(
        model="gemma-2b",
        messages=[{"role": "user", "content": "hello"}]
    )
    assert req.model == "gemma-2b"
    assert len(req.messages) == 1
    assert req.messages[0].role == "user"

    # Missing model
    with pytest.raises(ValidationError):
        OpenAIChatCompletionRequest(messages=[])

    # Empty messages
    with pytest.raises(ValidationError):
        OpenAIChatCompletionRequest(model="test", messages=[])

def test_openai_response_structure():
    """Test OpenAIChatCompletionResponse structure."""
    resp = OpenAIChatCompletionResponse(
        id="chatcmpl-123",
        model="gemma-2b",
        choices=[{
            "index": 0,
            "message": {"role": "assistant", "content": "hi"},
            "finish_reason": "stop"
        }],
        usage={"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
    )
    assert resp.object == "chat.completion"
    assert resp.choices[0].message.role == "assistant"
