import httpx
import pytest
import respx

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_responses_endpoint_translates_string_input_to_chat_completion():
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "DeepSeek-R1-7B"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        with respx.mock:
            upstream_route = respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "id": "chatcmpl-100",
                        "model": "gemma-3-4b",
                        "choices": [
                            {"index": 0, "message": {"role": "assistant", "content": "Hello from adapter"}}
                        ],
                    },
                )
            )

            response = await ac.post(
                "/v1/responses",
                json={
                    "model": "client-default",
                    "input": "hello",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["object"] == "response"
            assert data["model"] == "gemma-3-4b"
            assert data["output_text"] == "Hello from adapter"

            sent_payload = upstream_route.calls.last.request.content.decode()
            assert '"model":"gemma-3-4b"' in sent_payload
            assert '"messages":[{"role":"user","content":"hello"}]' in sent_payload


@pytest.mark.asyncio
async def test_responses_endpoint_routes_deep_for_keyword_input():
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "DeepSeek-R1-7B"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        with respx.mock:
            upstream_route = respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "id": "chatcmpl-101",
                        "model": "DeepSeek-R1-7B",
                        "choices": [
                            {"index": 0, "message": {"role": "assistant", "content": "Deep answer"}}
                        ],
                    },
                )
            )

            response = await ac.post(
                "/v1/responses",
                json={
                    "model": "client-default",
                    "input": "please plan the architecture for this adapter",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["model"] == "DeepSeek-R1-7B"
            assert data["output_text"] == "Deep answer"

            sent_payload = upstream_route.calls.last.request.content.decode()
            assert '"model":"DeepSeek-R1-7B"' in sent_payload


@pytest.mark.asyncio
async def test_responses_endpoint_streaming_passthrough():
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "DeepSeek-R1-7B"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        stream_content = (
            'data: {"choices":[{"delta":{"content":"He"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"llo"}}]}\n\n'
            'data: [DONE]\n\n'
        )

        with respx.mock:
            upstream_route = respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    content=stream_content.encode("utf-8"),
                    headers={"Content-Type": "text/event-stream"},
                )
            )

            async with ac.stream(
                "POST",
                "/v1/responses",
                json={
                    "model": "client-default",
                    "input": "hello",
                    "stream": True,
                },
            ) as response:
                body = b""
                async for chunk in response.aiter_bytes():
                    body += chunk

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert b'data: {"choices":[{"delta":{"content":"He"}}]}' in body
            assert b'data: [DONE]' in body

            sent_payload = upstream_route.calls.last.request.content.decode()
            assert '"stream":true' in sent_payload
            assert '"model":"gemma-3-4b"' in sent_payload
