from typing import Any, List

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.routes_chat import chat_completions
from app.models.api_models import ChatCompletionMessage, OpenAIChatCompletionRequest

router = APIRouter()


def _extract_text_from_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    parts.append(text)
        return "\n\n".join(part for part in parts if part)
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or "")
    return str(content)


def _translate_input_to_messages(payload: dict[str, Any]) -> List[ChatCompletionMessage]:
    messages: List[ChatCompletionMessage] = []

    instructions = payload.get("instructions")
    if instructions:
        messages.append(ChatCompletionMessage(role="system", content=str(instructions)))

    input_value = payload.get("input", "")
    if isinstance(input_value, str):
        messages.append(ChatCompletionMessage(role="user", content=input_value))
        return messages

    if isinstance(input_value, list):
        for item in input_value:
            if isinstance(item, str):
                messages.append(ChatCompletionMessage(role="user", content=item))
                continue
            if isinstance(item, dict):
                role = item.get("role", "user")
                content = _extract_text_from_content(item.get("content"))
                messages.append(ChatCompletionMessage(role=role, content=content))

    return messages


def _build_chat_request_from_response_payload(payload: dict[str, Any]) -> OpenAIChatCompletionRequest:
    messages = _translate_input_to_messages(payload)
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"message": "responses.input must produce at least one message"}},
        )

    return OpenAIChatCompletionRequest(
        model=payload.get("model", ""),
        messages=messages,
        temperature=payload.get("temperature", 0.7),
        max_tokens=payload.get("max_output_tokens"),
        stream=payload.get("stream", False),
        top_p=payload.get("top_p", 1.0),
        user=payload.get("user"),
    )


def _translate_chat_completion_to_response(chat_response: dict[str, Any]) -> dict[str, Any]:
    choices = chat_response.get("choices") or []
    assistant_message = choices[0].get("message", {}) if choices else {}
    output_text = assistant_message.get("content", "") or ""

    return {
        "id": chat_response.get("id", "resp-adapter"),
        "object": "response",
        "created": chat_response.get("created", 0),
        "model": chat_response.get("model"),
        "status": "completed",
        "output": [
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": output_text,
                        "annotations": [],
                    }
                ],
            }
        ],
        "output_text": output_text,
        "usage": chat_response.get("usage", {}),
    }


@router.post("/responses")
async def responses(request: Request):
    payload = await request.json()
    chat_request = _build_chat_request_from_response_payload(payload)

    if chat_request.stream:
        chat_stream = await chat_completions(chat_request)
        if not isinstance(chat_stream, StreamingResponse):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error": {"message": "Unexpected streaming response type"}},
            )
        return StreamingResponse(
            chat_stream.body_iterator,
            media_type="text/event-stream",
        )

    chat_response = await chat_completions(chat_request)
    if not isinstance(chat_response, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"message": "Unexpected upstream response type"}},
        )

    return _translate_chat_completion_to_response(chat_response)
