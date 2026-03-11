import httpx
from typing import Dict, Any, AsyncGenerator, Optional

class UpstreamClient:
    """
    Client for forwarding requests to the llama.cpp server.
    """
    
    def __init__(self, base_url: str):
        # Normalize base_url to not have trailing slash
        self.base_url = base_url.rstrip("/")

    async def get(self, path: str) -> Dict[str, Any]:
        """Generic GET request to upstream."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}{path}")
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic POST request to upstream."""
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json=json_data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()

    async def post_stream(self, path: str, json_data: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
        """Generic streaming POST request to upstream."""
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}{path}",
                json=json_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n\n".encode("utf-8")

    # Legacy helper methods (refactored to use generic ones)
    async def complete(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.post("/v1/chat/completions", request_data)

    async def stream(self, request_data: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
        async for chunk in self.post_stream("/v1/chat/completions", request_data):
            yield chunk

    async def check_health(self) -> bool:
        """Check if upstream is healthy."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                # llama.cpp has /health endpoint
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
