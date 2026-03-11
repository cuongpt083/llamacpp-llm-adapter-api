from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.upstream.client import UpstreamClient
import structlog

router = APIRouter()
logger = structlog.get_logger()
upstream = UpstreamClient(base_url=settings.UPSTREAM_BASE_URL)

@router.post("/completions")
async def completions(request: Request):
    """
    Proxy legacy text completions to llama.cpp.
    """
    payload = await request.json()
    
    # Handle Streaming
    if payload.get("stream"):
        return StreamingResponse(
            upstream.post_stream("/v1/completions", payload),
            media_type="text/event-stream"
        )
    
    # Handle Non-Streaming
    try:
        return await upstream.post("/v1/completions", payload)
    except Exception as e:
        logger.exception("Upstream completion error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"message": "Error communicating with upstream"}}
        )
