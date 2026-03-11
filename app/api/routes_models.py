from fastapi import APIRouter
from app.core.config import settings
from app.policies.registry import registry

router = APIRouter()

@router.get("/models")
async def list_models():
    """
    List available models and their adapter metadata.
    """
    # In a real scenario, this would fetch from llama.cpp /v1/models
    # For now, we return metadata about the adapter's capabilities
    return {
        "object": "list",
        "data": [
            {
                "id": "gemma-3-4b",
                "object": "model",
                "adapter_family": "gemma",
                "adapter_policy": "gemma-strict-v1"
            },
            {
                "id": "llama-3-8b",
                "object": "model",
                "adapter_family": "passthrough",
                "adapter_policy": "passthrough-v1"
            }
        ]
    }
