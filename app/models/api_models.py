from typing import List, Optional, Any, Dict, Literal
from pydantic import BaseModel, Field, validator

class ChatCompletionMessage(BaseModel):
    role: str
    content: Optional[str] = ""
    name: Optional[str] = None
    tool_calls: Optional[List[Any]] = None
    tool_call_id: Optional[str] = None

class OpenAIChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None
    top_p: Optional[float] = 1.0
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    user: Optional[str] = None

    @validator("messages")
    def messages_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("messages must not be empty")
        return v

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatCompletionMessage
    finish_reason: Optional[str] = "stop"

class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class OpenAIChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: 0) # Placeholder
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage
