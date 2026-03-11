import pytest
from app.normalizer.pipeline import NormalizationPipeline
from app.models.api_models import ChatCompletionMessage

def test_normalization_pipeline_gemma():
    """Verify end-to-end normalization for Gemma model."""
    pipeline = NormalizationPipeline()
    
    # Input with system, user, and tool
    messages = [
        ChatCompletionMessage(role="system", content="Be helpful"),
        ChatCompletionMessage(role="user", content="Tell me weather"),
        ChatCompletionMessage(role="tool", content="Sunny in Saigon", tool_call_id="call_1")
    ]
    
    result = pipeline.process(model="gemma-3-4b", messages=messages)
    
    assert result.family == "gemma"
    assert result.policy == "gemma-strict-v1"
    assert len(result.normalized_messages) == 1
    assert result.normalized_messages[0].role == "user"
    assert "Be helpful" in result.normalized_messages[0].content
    assert "Sunny in Saigon" in result.normalized_messages[0].content
    assert result.validation_result is True

def test_normalization_pipeline_passthrough():
    """Verify passthrough for unknown models."""
    pipeline = NormalizationPipeline()
    
    messages = [
        ChatCompletionMessage(role="system", content="Be helpful"),
        ChatCompletionMessage(role="user", content="Tell me weather")
    ]
    
    result = pipeline.process(model="gpt-4o", messages=messages)
    
    assert result.family == "passthrough"
    assert len(result.normalized_messages) == 2
    assert result.normalized_messages[0].role == "system"
