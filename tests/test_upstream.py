import pytest
import respx
import httpx
import json
from app.upstream.client import UpstreamClient

@pytest.mark.asyncio
async def test_upstream_complete_success():
    """Verify that UpstreamClient correctly forwards a non-streaming request."""
    client = UpstreamClient(base_url="http://llama.cpp:8080")
    
    mock_response = {
        "id": "chatcmpl-123",
        "choices": [{"message": {"role": "assistant", "content": "hello"}}]
    }
    
    with respx.mock:
        respx.post("http://llama.cpp:8080/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        response_data = await client.complete({"model": "test", "messages": []})
        
        assert response_data["id"] == "chatcmpl-123"
        assert response_data["choices"][0]["message"]["content"] == "hello"

@pytest.mark.asyncio
async def test_upstream_streaming_success():
    """Verify that UpstreamClient handles SSE streaming."""
    client = UpstreamClient(base_url="http://llama.cpp:8080")
    
    # SSE stream format
    stream_content = (
        "data: " + json.dumps({"choices": [{"delta": {"content": "He"}}]}) + "\n\n"
        "data: " + json.dumps({"choices": [{"delta": {"content": "llo"}}]}) + "\n\n"
        "data: [DONE]\n\n"
    )
    
    with respx.mock:
        respx.post("http://llama.cpp:8080/v1/chat/completions").mock(
            return_value=httpx.Response(
                200, 
                content=stream_content.encode("utf-8"),
                headers={"Content-Type": "text/event-stream"}
            )
        )
        
        chunks = []
        async for chunk in client.stream({"model": "test", "stream": True}):
            chunks.append(chunk)
            
        assert len(chunks) == 3
        assert b"He" in chunks[0]
        assert b"llo" in chunks[1]
        assert b"[DONE]" in chunks[2]
