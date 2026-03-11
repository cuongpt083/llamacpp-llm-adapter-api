from fastapi import APIRouter, Response, status
import httpx
from app.core.config import settings

router = APIRouter()

@router.get("/healthz")
async def healthz():
    """Liveness check."""
    return {"status": "ok"}

@router.get("/readyz")
async def readyz():
    """Readiness check: verifies connectivity to upstream."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # llama.cpp typically has /health or we can just try to reach it
            # Using /health as a proxy for readiness
            resp = await client.get(f"{settings.UPSTREAM_BASE_URL}/health")
            if resp.status_code == 200:
                return {"status": "ready", "upstream": "ok"}
            else:
                return Response(
                    content='{"status": "not ready", "upstream": "error"}',
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    media_type="application/json"
                )
    except Exception:
        return Response(
            content='{"status": "not ready", "upstream": "unreachable"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
