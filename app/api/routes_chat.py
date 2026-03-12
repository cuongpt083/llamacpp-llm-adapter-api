import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.models.api_models import OpenAIChatCompletionRequest
from app.normalizer.pipeline import NormalizationPipeline
from app.routing.router import PromptRouter
from app.routing.rules import strip_mode_hints
from app.upstream.client import UpstreamClient

router = APIRouter()
logger = structlog.get_logger()

# Instances (could be managed via dependency injection but keeping simple for MVP)
pipeline = NormalizationPipeline()
upstream = UpstreamClient(base_url=settings.UPSTREAM_BASE_URL)

NETWORK_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def build_router() -> PromptRouter:
    return PromptRouter(
        fast_model=settings.FAST_MODEL,
        deep_model=settings.DEEP_MODEL,
    )


def build_debug_response(client_requested_model: str, route_decision, normalization_result):
    return {
        "client_requested_model": client_requested_model,
        "route_label": route_decision.route_label,
        "route_reason": route_decision.reasons,
        "resolved_model": route_decision.resolved_model,
        "resolved_family": normalization_result.family,
        "family": normalization_result.family,
        "policy": normalization_result.policy,
        "original_messages": [m.model_dump(exclude_none=True) for m in normalization_result.original_messages],
        "normalized_messages": [m.model_dump(exclude_none=True) for m in normalization_result.normalized_messages],
        "transform_log": normalization_result.transform_log,
        "validation": {"valid": normalization_result.validation_result},
    }


def build_upstream_payload(request: OpenAIChatCompletionRequest, normalization_result):
    upstream_payload = request.model_dump(exclude_unset=True)
    upstream_payload["model"] = normalization_result.model
    upstream_payload["messages"] = [m.model_dump(exclude_none=True) for m in normalization_result.normalized_messages]
    return upstream_payload


async def send_with_optional_failover(request: OpenAIChatCompletionRequest, route_decision, normalization_result):
    try:
        response_data = await upstream.complete(build_upstream_payload(request, normalization_result))
        response_data["model"] = route_decision.resolved_model
        return response_data
    except NETWORK_ERRORS as exc:
        if request.stream:
            raise exc

        fallback_label = "deep" if route_decision.route_label == "fast" else "fast"
        fallback_model = settings.DEEP_MODEL if fallback_label == "deep" else settings.FAST_MODEL
        fallback_normalization = pipeline.process(model=fallback_model, messages=request.messages)

        if not fallback_normalization.validation_result:
            raise exc

        response_data = await upstream.complete(build_upstream_payload(request, fallback_normalization))
        response_data["model"] = fallback_model
        return response_data

@router.post("/chat/completions")
async def chat_completions(request: OpenAIChatCompletionRequest):
    """
    Standard OpenAI-compatible Chat Completions endpoint with normalization.
    """
    try:
        sanitized_messages = strip_mode_hints(request.messages)
        route_decision = build_router().route(
            client_requested_model=request.model,
            messages=request.messages,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"message": str(exc)}},
        ) from exc

    sanitized_request = request.model_copy(update={"messages": sanitized_messages})
    result = pipeline.process(model=route_decision.resolved_model, messages=sanitized_messages)
    
    if not result.validation_result:
        logger.error(
            "Normalization validation failed",
            client_requested_model=request.model,
            resolved_model=route_decision.resolved_model,
            family=result.family,
            policy=result.policy,
        )
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
    
    if settings.LOG_NORMALIZED_REQUESTS:
        logger.info(
            "Forwarding normalized request",
            client_requested_model=request.model,
            resolved_model=route_decision.resolved_model,
            route_label=route_decision.route_label,
            route_reasons=route_decision.reasons,
            family=result.family,
            msg_count=len(result.normalized_messages),
        )

    if request.stream:
        return StreamingResponse(
            upstream.stream(build_upstream_payload(sanitized_request, result)),
            media_type="text/event-stream"
        )
    
    try:
        response_data = await send_with_optional_failover(sanitized_request, route_decision, result)
        return response_data
    except Exception as exc:
        logger.exception("Upstream error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"message": "Error communicating with upstream llama.cpp server"}}
        )

@router.post("/chat/completions:normalize")
async def chat_completions_normalize(request: OpenAIChatCompletionRequest):
    """
    Debug endpoint to inspect normalization without calling upstream.
    """
    try:
        sanitized_messages = strip_mode_hints(request.messages)
        route_decision = build_router().route(
            client_requested_model=request.model,
            messages=request.messages,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"message": str(exc)}},
        ) from exc

    result = pipeline.process(model=route_decision.resolved_model, messages=sanitized_messages)
    return build_debug_response(request.model, route_decision, result)
