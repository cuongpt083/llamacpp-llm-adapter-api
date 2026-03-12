import httpx
import pytest
import respx

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_models_endpoint_enriches_route_tags():
    settings.FAST_MODEL = "gemma-3-4b"
    settings.DEEP_MODEL = "qwen3.5-2B"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        with respx.mock:
            respx.get("http://127.0.0.1:8080/v1/models").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "object": "list",
                        "data": [
                            {"id": "gemma-3-4b", "object": "model"},
                            {"id": "qwen3.5-2B", "object": "model"},
                        ],
                    },
                )
            )

            response = await ac.get("/v1/models")

            assert response.status_code == 200
            payload = response.json()
            assert payload["data"][0]["adapter_route_tags"] == ["fast"]
            assert payload["data"][1]["adapter_route_tags"] == ["deep"]
