from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from app.models.api_models import OpenAIChatCompletionRequest
from app.normalizer.pipeline import NormalizationPipeline
from app.upstream.client import UpstreamClient
from app.core.config import settings
import structlog

router = APIRouter()
logger = structlog.get_logger()

# Instances (could be managed via dependency injection but keeping simple for MVP)
pipeline = NormalizationPipeline()
upstream = UpstreamClient(base_url=settings.UPSTREAM_BASE_URL)

@router.post("/chat/completions")
async def chat_completions(request: OpenAIChatCompletionRequest):
    """
    Standard OpenAI-compatible Chat Completions endpoint with normalization.
    """
    # 1. Normalize
    result = pipeline.process(model=request.model, messages=request.messages)
    
    if not result.validation_result:
        logger.error("Normalization validation failed", family=result.family, policy=result.policy)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "type": "normalization_error",
                    "code": "INVALID_MESSAGE_SEQUENCE",
                    "message": "Messages cannot be normalized into a valid sequence for this model."
                }
            }
        )
    
    # 2. Reconstruct request for upstream
    upstream_payload = request.dict(exclude_unset=True)
    upstream_payload["messages"] = [m.dict(exclude_none=True) for m in result.normalized_messages]
    
    if settings.LOG_NORMALIZED_REQUESTS:
        logger.info("Forwarding normalized request", 
                   model=request.model, 
                   family=result.family, 
                   msg_count=len(result.normalized_messages))

    # 3. Handle Streaming
    if request.stream:
        return StreamingResponse(
            upstream.stream(upstream_payload),
            media_type="text/event-stream"
        )
    
    # 4. Handle Non-Streaming
    try:
        response_data = await upstream.complete(upstream_payload)
        return response_data
    except Exception as e:
        logger.exception("Upstream error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"message": "Error communicating with upstream llama.cpp server"}}
        )

@router.post("/chat/completions:normalize")
async def chat_completions_normalize(request: OpenAIChatCompletionRequest):
    """
    Debug endpoint to inspect normalization without calling upstream.
    """
    return pipeline.process(model=request.model, messages=request.messages)
