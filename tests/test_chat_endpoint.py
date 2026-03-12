import pytest
import respx
import httpx
from app.main import app
from app.core.config import settings

@pytest.mark.asyncio
async def test_chat_completions_gemma_flow():
    """Test full flow: client -> adapter (normalize) -> llama.cpp -> client."""
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "qwen3.5-2B"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Mock upstream llama.cpp
        mock_response = {
            "id": "chatcmpl-123",
            "model": "gemma-3-4b",
            "choices": [{"message": {"role": "assistant", "content": "I am Gemma"}}]
        }
        
        with respx.mock:
            # We expect the adapter to call this URL (default config)
            respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
                return_value=httpx.Response(200, json=mock_response)
            )
            
            # Send request to adapter
            payload = {
                "model": "client-side-default",
                "messages": [
                    {"role": "system", "content": "You are a bot"},
                    {"role": "user", "content": "Hello"}
                ]
            }
            
            response = await ac.post("/v1/chat/completions", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["choices"][0]["message"]["content"] == "I am Gemma"
            assert data["model"] == "gemma-3-4b"

@pytest.mark.asyncio
async def test_chat_completions_normalize_debug():
    """Test the debug :normalize endpoint."""
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "qwen3.5-2B"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "model": "client-side-default",
            "messages": [
                {"role": "system", "content": "You are a bot"},
                {"role": "user", "content": "Hello"}
            ]
        }
        
        response = await ac.post("/v1/chat/completions:normalize", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["client_requested_model"] == "client-side-default"
        assert data["route_label"] == "fast"
        assert data["resolved_model"] == "gemma-3-4b"
        assert data["family"] == "gemma"
        assert len(data["normalized_messages"]) == 1
        assert data["normalized_messages"][0]["role"] == "user"
        assert "You are a bot" in data["normalized_messages"][0]["content"]


@pytest.mark.asyncio
async def test_chat_completions_routes_deep_and_returns_resolved_model():
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "qwen3.5-2B"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        mock_response = {
            "id": "chatcmpl-456",
            "model": "qwen3.5-2B",
            "choices": [{"message": {"role": "assistant", "content": "debug result"}}],
        }

        with respx.mock:
            upstream_route = respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
                return_value=httpx.Response(200, json=mock_response)
            )

            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "user", "content": "please debug this traceback for me"}
                ],
            }

            response = await ac.post("/v1/chat/completions", json=payload)

            assert response.status_code == 200
            assert upstream_route.called
            assert upstream_route.calls.last.request.content
            assert response.json()["model"] == "qwen3.5-2B"


@pytest.mark.asyncio
async def test_chat_completions_fails_over_on_network_error_for_non_streaming():
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "qwen3.5-2B"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        with respx.mock:
            route = respx.post("http://127.0.0.1:8080/v1/chat/completions")
            route.side_effect = [
                httpx.ConnectError("upstream down"),
                httpx.Response(
                    200,
                    json={
                        "id": "chatcmpl-789",
                        "model": "qwen3.5-2B",
                        "choices": [{"message": {"role": "assistant", "content": "fallback ok"}}],
                    },
                ),
            ]

            payload = {
                "model": "client-default",
                "messages": [{"role": "user", "content": "hello"}],
            }

            response = await ac.post("/v1/chat/completions", json=payload)

            assert response.status_code == 200
            assert route.call_count == 2
            assert response.json()["model"] == "qwen3.5-2B"


@pytest.mark.asyncio
async def test_chat_completions_strips_mode_hint_before_upstream():
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "qwen3.5-2B"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        with respx.mock:
            upstream_route = respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "id": "chatcmpl-999",
                        "model": "gemma-3-4b",
                        "choices": [{"message": {"role": "assistant", "content": "forced fast"}}],
                    },
                )
            )

            payload = {
                "model": "client-default",
                "messages": [{"role": "user", "content": "[mode:FAST] please debug this traceback"}],
            }

            response = await ac.post("/v1/chat/completions", json=payload)

            assert response.status_code == 200
            assert response.json()["model"] == "gemma-3-4b"
            sent_payload = upstream_route.calls.last.request.content.decode()
            assert '"model":"gemma-3-4b"' in sent_payload
            assert "[mode:FAST]" not in sent_payload


@pytest.mark.asyncio
async def test_chat_completions_rejects_conflicting_mode_hints():
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "qwen3.5-2B"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "model": "client-default",
            "messages": [
                {"role": "user", "content": "[mode:FAST] hello"},
                {"role": "user", "content": "[mode:DEEP] world"},
            ],
        }

        response = await ac.post("/v1/chat/completions", json=payload)

        assert response.status_code == 422

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
