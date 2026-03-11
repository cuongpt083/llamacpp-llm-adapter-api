from fastapi import APIRouter, Request, HTTPException, status
from app.core.config import settings
from app.upstream.client import UpstreamClient
import structlog

router = APIRouter()
logger = structlog.get_logger()
upstream = UpstreamClient(base_url=settings.UPSTREAM_BASE_URL)

@router.post("/embeddings")
async def embeddings(request: Request):
    """
    Proxy embeddings requests to llama.cpp.
    """
    payload = await request.json()
    try:
        return await upstream.post("/v1/embeddings", payload)
    except Exception as e:
        logger.exception("Upstream embeddings error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"message": "Error communicating with upstream"}}
        )
