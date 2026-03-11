import httpx
from typing import Dict, Any, AsyncGenerator

class UpstreamClient:
    """
    Client for forwarding requests to the llama.cpp server.
    """
    
    def __init__(self, base_url: str):
        # Normalize base_url to not have trailing slash
        self.base_url = base_url.rstrip("/")
        self.chat_endpoint = f"{self.base_url}/v1/chat/completions"

    async def complete(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a non-streaming completion request.
        """
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                self.chat_endpoint,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()

    async def stream(self, request_data: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
        """
        Send a streaming completion request and yield SSE chunks.
        """
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream(
                "POST",
                self.chat_endpoint,
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n\n".encode("utf-8")
