from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.upstream.client import UpstreamClient

router = APIRouter()
upstream = UpstreamClient(base_url=settings.UPSTREAM_BASE_URL)

@router.get("/healthz")
async def healthz():
    """Liveness check."""
    return {"status": "ok"}

@router.get("/readyz")
async def readyz():
    """Readiness check: verifies connectivity to upstream."""
    is_ready = await upstream.check_health()
    if is_ready:
        return {"status": "ready", "upstream": "ok"}
    else:
        return Response(
            content='{"status": "not ready", "upstream": "unreachable"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
