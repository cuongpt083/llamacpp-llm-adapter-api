# Gemini CLI Coding Task  
## Project: LLM Message Normalization Adapter for llama.cpp

---

# 1. Objective

Implement a **production-oriented OpenAI-compatible REST API adapter** that sits between agent frameworks (e.g., ZeroClaw) and a `llama.cpp` model server.

The adapter must:

- Accept OpenAI-compatible `/v1/chat/completions` requests
- Normalize messages according to **model family policies**
- Fix conversation role ordering issues
- Handle models with strict templates such as **Gemma**
- Forward normalized requests to `llama.cpp`
- Return responses transparently (including streaming)

Primary goal:

> Prevent template errors like  
> `"Conversation roles must alternate user/assistant/user/assistant"`

---

# 2. Technology Requirements

Language:

```
Python 3.11+
```

Framework:

```
FastAPI
```

HTTP client:

```
httpx
```

Testing:

```
pytest
```

Other libraries:

```
pydantic
uvicorn
structlog
```

---

# 3. Project Architecture

Gemini must generate the following project structure:

```
adapter/
│
├── app/
│   ├── main.py
│
│   ├── api/
│   │   ├── routes_chat.py
│   │   ├── routes_health.py
│   │   ├── routes_models.py
│   │   └── routes_debug.py
│
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── errors.py
│
│   ├── models/
│   │   ├── api_models.py
│   │   └── internal_messages.py
│
│   ├── policies/
│   │   ├── base.py
│   │   ├── passthrough.py
│   │   ├── gemma.py
│   │   └── registry.py
│
│   ├── normalizer/
│   │   ├── pipeline.py
│   │   ├── transforms.py
│   │   └── validators.py
│
│   ├── upstream/
│   │   ├── client.py
│   │   └── streaming.py
│
│   └── services/
│       └── model_registry.py
│
├── tests/
│   ├── test_gemma_policy.py
│   ├── test_normalization.py
│   └── test_chat_endpoint.py
│
├── requirements.txt
└── README.md
```

---

# 4. Public API Endpoints

## Health

### GET /healthz

Response:

```json
{
  "status": "ok"
}
```

---

### GET /readyz

Checks connectivity to upstream llama.cpp server.

Response:

```json
{
  "status": "ready",
  "upstream": "ok"
}
```

---

## Models

### GET /v1/models

Return upstream models plus adapter metadata.

Example:

```json
{
  "object": "list",
  "data": [
    {
      "id": "gemma-3-4b",
      "object": "model",
      "adapter_family": "gemma",
      "adapter_policy": "gemma-strict-v1"
    }
  ]
}
```

---

## Chat Completions

### POST /v1/chat/completions

Input:

```json
{
  "model": "gemma-3-4b",
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello"}
  ],
  "temperature": 0.7,
  "max_tokens": 256,
  "stream": false
}
```

Behavior:

1. Detect model family
2. Normalize messages
3. Validate conversation sequence
4. Forward request to llama.cpp
5. Return upstream response

---

## Debug Endpoint

### POST /v1/chat/completions:normalize

Used for debugging normalization.

Response example:

```json
{
  "family": "gemma",
  "policy": "gemma-strict-v1",
  "original_messages": [...],
  "normalized_messages": [...],
  "transform_log": [...],
  "validation": {
    "valid": true
  }
}
```

---

# 5. Message Data Model

## Internal Message

Gemini must implement the following internal structure:

```python
class InternalMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
```

Allowed roles internally:

```
system
developer
user
assistant
tool
function
observation
```

---

# 6. Policy System

Gemini must implement a **policy-driven normalization system**.

Policy interface:

```python
class MessagePolicy(ABC):

    family: str
    policy_name: str

    @abstractmethod
    def detect(self, model: str) -> bool:
        pass

    @abstractmethod
    def normalize(self, messages: List[InternalMessage]):
        pass

    @abstractmethod
    def validate(self, messages: List[InternalMessage]):
        pass
```

---

# 7. Default Policy

Implement:

```
passthrough-v1
```

Behavior:

- No transformation
- Forward messages unchanged

Used for non-strict models.

---

# 8. Gemma Policy

Implement policy:

```
gemma-strict-v1
```

Rules:

---

## Rule 1 — Fold system into first user

Input:

```json
[
 {"role":"system","content":"You are helpful"},
 {"role":"user","content":"Hello"}
]
```

Output:

```json
[
 {"role":"user","content":"You are helpful\n\nHello"}
]
```

---

## Rule 2 — Fold developer into user

Treat `developer` role the same as `system`.

---

## Rule 3 — Serialize unsupported roles

Unsupported roles:

```
tool
function
observation
```

Convert them to text blocks:

```
[tool]
content
```

---

## Rule 4 — Merge consecutive roles

Example:

Input:

```
user
user
```

Output:

```
user
```

Merged content separated by:

```
\n\n
```

---

## Rule 5 — Enforce alternation

Final message order must be:

```
user
assistant
user
assistant
```

If alternation cannot be satisfied:

Return HTTP 422.

---

## Rule 6 — Remove empty messages

Messages containing only whitespace must be removed.

---

# 9. Model Family Detection

Implement mapping:

```python
MODEL_PREFIX_FAMILY = {
    "gemma": "gemma",
    "llama": "passthrough",
    "qwen": "passthrough"
}
```

Detection rule:

```
model.startswith(prefix)
```

---

# 10. Upstream Client

Adapter must forward requests to llama.cpp server.

Default upstream URL:

```
http://127.0.0.1:8080
```

Forward path:

```
/v1/chat/completions
```

Implementation requirements:

- Use `httpx.AsyncClient`
- Preserve request parameters
- Support streaming responses

---

# 11. Streaming Support

If request contains:

```
"stream": true
```

Adapter must:

- Forward request
- Passthrough SSE stream
- Not buffer the entire response

Content type:

```
text/event-stream
```

---

# 12. Error Format

All errors must follow:

```json
{
  "error": {
    "type": "normalization_error",
    "code": "INVALID_MESSAGE_SEQUENCE",
    "message": "Messages cannot be normalized into valid sequence"
  }
}
```

---

# 13. Logging

Gemini must implement structured JSON logs using `structlog`.

Required fields:

```
timestamp
request_id
path
model
family
policy
duration_ms
```

Optional:

```
normalized_messages
```

---

# 14. Configuration

Implement environment-based config.

Example:

```
UPSTREAM_BASE_URL=http://127.0.0.1:8080
ENABLE_DEBUG_ENDPOINTS=true
LOG_NORMALIZED_REQUESTS=true
```

---

# 15. Unit Tests

Gemini must implement tests.

---

## Test 1 — System folding

Input:

```
system + user
```

Expected:

```
single user message
```

---

## Test 2 — Merge user messages

Input:

```
user
user
```

Expected:

```
single merged user
```

---

## Test 3 — Tool serialization

Input:

```
user
tool
assistant
```

Expected normalized conversation.

---

## Test 4 — Alternation validation

Invalid order:

```
assistant
assistant
```

Expected:

```
HTTP 422
```

---

## Test 5 — Streaming passthrough

Ensure adapter forwards SSE without corruption.

---

# 16. README Requirements

Gemini must generate a README explaining:

- architecture
- API endpoints
- running instructions
- environment variables
- testing instructions

Example run command:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

# 17. Acceptance Criteria

The implementation is considered complete if:

- Adapter accepts OpenAI-compatible requests
- Gemma role errors are automatically fixed
- `/v1/chat/completions` works with llama.cpp
- Streaming responses function correctly
- Debug normalization endpoint works
- Unit tests pass
- Code structure matches the required architecture

---

# 18. Implementation Guidance for Gemini

When generating code:

1. Write **clean modular code**
2. Avoid large monolithic files
3. Use **type hints everywhere**
4. Implement **async HTTP requests**
5. Add **clear docstrings**
6. Ensure **pytest coverage for normalization logic**

---

# End of Task Specification
