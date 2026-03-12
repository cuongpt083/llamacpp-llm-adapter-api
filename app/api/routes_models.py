from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.upstream.client import UpstreamClient
from app.policies.registry import registry

router = APIRouter()
upstream = UpstreamClient(base_url=settings.UPSTREAM_BASE_URL)

@router.get("/models")
async def list_models():
    """
    List available models from upstream and enrich with adapter metadata.
    """
    try:
        # Fetch from llama.cpp /v1/models
        upstream_data = await upstream.get("/v1/models")
        
        # Enrich each model with adapter info
        if "data" in upstream_data:
            for model_info in upstream_data["data"]:
                model_id = model_info.get("id", "")
                policy = registry.get_policy_for_model(model_id)
                model_info["adapter_family"] = policy.family
                model_info["adapter_policy"] = policy.policy_name
                route_tags = []
                if model_id == settings.FAST_MODEL:
                    route_tags.append("fast")
                if model_id == settings.DEEP_MODEL:
                    route_tags.append("deep")
                model_info["adapter_route_tags"] = route_tags
                
        return upstream_data
    except Exception:
        # Fallback if upstream is down
        return {
            "object": "list",
            "data": []
        }
