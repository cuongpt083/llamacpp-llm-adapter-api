import pytest
import respx
import httpx
from app.main import app

@pytest.mark.asyncio
async def test_chat_completions_gemma_flow():
    """Test full flow: client -> adapter (normalize) -> llama.cpp -> client."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Mock upstream llama.cpp
        mock_response = {
            "id": "chatcmpl-123",
            "choices": [{"message": {"role": "assistant", "content": "I am Gemma"}}]
        }
        
        with respx.mock:
            # We expect the adapter to call this URL (default config)
            respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
                return_value=httpx.Response(200, json=mock_response)
            )
            
            # Send request to adapter
            payload = {
                "model": "gemma-2b",
                "messages": [
                    {"role": "system", "content": "You are a bot"},
                    {"role": "user", "content": "Hello"}
                ]
            }
            
            response = await ac.post("/v1/chat/completions", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["choices"][0]["message"]["content"] == "I am Gemma"

@pytest.mark.asyncio
async def test_chat_completions_normalize_debug():
    """Test the debug :normalize endpoint."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "model": "gemma-2b",
            "messages": [
                {"role": "system", "content": "You are a bot"},
                {"role": "user", "content": "Hello"}
            ]
        }
        
        response = await ac.post("/v1/chat/completions:normalize", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["family"] == "gemma"
        assert len(data["normalized_messages"]) == 1
        assert data["normalized_messages"][0]["role"] == "user"
        assert "You are a bot" in data["normalized_messages"][0]["content"]

@pytest.mark.asyncio
async def test_health_endpoints():
    """Test healthz and readyz."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Healthz
        resp = await ac.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        
        # Readyz (requires upstream check)
        with respx.mock:
            respx.get("http://127.0.0.1:8080/health").mock(return_value=httpx.Response(200))
            resp = await ac.get("/readyz")
            assert resp.status_code == 200
            assert resp.json()["upstream"] == "ok"
