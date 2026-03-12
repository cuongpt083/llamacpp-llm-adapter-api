# Gemini CLI Coding Task  
## Project: LLM Message Normalization & Routing Adapter for llama.cpp  
### Spec Version: v1.2

---

# 1. Objective

Implement a **production-oriented OpenAI-compatible REST API adapter** that sits between agent frameworks (e.g., ZeroClaw) and a `llama.cpp` model server.

The adapter must:

- Accept OpenAI-compatible `/v1/chat/completions` requests
- **Automatically route requests between two models based on prompt complexity**
- Normalize messages according to **model family policies**
- Fix conversation role ordering issues
- Handle models with strict templates such as **Gemma**
- Forward normalized requests to `llama.cpp`
- Return responses transparently (including streaming)

Primary goal:

> Prevent template errors like  
> `"Conversation roles must alternate user/assistant/user/assistant"`

Secondary goal:

> Automatically select the appropriate model (Gemma or Qwen) depending on task complexity.

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
│   ├── routing/
│   │   ├── router.py
│   │   ├── rules.py
│   │   └── models.py
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
│   ├── test_router.py
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
      "adapter_policy": "gemma-strict-v1",
      "adapter_route_tags": ["fast"]
    }
  ]
}
```

---

## Chat Completions

### POST /v1/chat/completions

Input example:

```json
{
  "model": "any-client-default",
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

1. Convert messages to internal format
2. **Route request using rule-based router**
3. Resolve target model (`FAST_MODEL` or `DEEP_MODEL`)
4. Detect family of resolved model
5. Normalize messages according to policy
6. Validate conversation sequence
7. Forward request to llama.cpp
8. Return upstream response

Important:

The adapter **ignores the model provided by the client for routing purposes**.

However it must still be logged as:

```
client_requested_model
```

The adapter must:

- load the actual upstream model names from environment configuration
- map requests to logical route modes `FAST` or `DEEP`
- construct the upstream request using the resolved real model name
- return the **actual resolved model name** in the final API response so clients can continue the conversation using the real model that handled the request

---

## Debug Endpoint

### POST /v1/chat/completions:normalize

Used for debugging normalization.

Response example:

```json
{
  "client_requested_model": "gpt-4o",
  "route_label": "deep",
  "route_reason": ["matched_keyword:debug"],
  "resolved_model": "qwen2.5-coder-7b-instruct",
  "resolved_family": "qwen",
  "policy": "passthrough-v1",
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

Internal representation:

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

# 6. Routing System

A **rule-based router** determines whether a request should use the fast model or the deep reasoning model.

Routing is applied to **every request**.

Router output:

```python
class RouteDecision(BaseModel):
    client_requested_model: Optional[str]
    route_label: str
    resolved_model: str
    reasons: List[str]
    fallback_eligible: bool
```

Mapping:

```
fast  -> FAST_MODEL
deep  -> DEEP_MODEL
```

Configuration:

```
FAST_MODEL=gemma-3-4b
DEEP_MODEL=qwen2.5-coder-7b-instruct
```

---

# 7. Routing Rules

Route to **deep reasoning model (Qwen)** if any of the following is true:

Routing must use a **strict observable rule list only**.

- Do not use semantic inference-only routing.
- Do not route based on prompt length alone.
- If no explicit trigger matches, default to `FAST`.
- Normalize text before keyword matching:
  - lowercase all prompt text
  - collapse repeated whitespace
  - support both Vietnamese with diacritics and common non-diacritic variants
  - prefer phrase matching over single-token matching when possible

### Tool usage

Presence of roles:

```
tool
function
observation
```

---

### Code detection

Code block pattern:

```
```
code
```
```

---

### Coding / implementation signals

English keywords and phrases such as:

```
code
write code
implement
implementation
refactor
debug
bug
fix bug
traceback
stack trace
exception
error log
unit test
test case
endpoint
api route
```

Vietnamese keywords and phrases such as:

```
lập trình
viet code
viết code
viết mã
triển khai
cài đặt
tái cấu trúc
refactor
gỡ lỗi
sửa lỗi
lỗi
ngoại lệ
log lỗi
kiểm thử
ca kiểm thử
```

---

### Debug signals

Keywords such as:

```
debug
bug
fix
refactor
implement
traceback
stack trace
exception
error log
```

Vietnamese debug keywords such as:

```
gỡ lỗi
sửa lỗi
lỗi
ngoại lệ
vết lỗi
log lỗi
truy vết
```

---

### Planning / reasoning signals

Keywords such as:

```
step by step
plan
planning
design
architecture
trade-off
compare approaches
root cause
investigate
analyze
```

Vietnamese keywords such as:

```
từng bước
từng bước một
kế hoạch
ke hoach
lập kế hoạch
thiết kế
thiet ke
kiến trúc
kien truc
đánh đổi
danh doi
so sánh phương án
so sanh phuong an
nguyên nhân gốc
nguyen nhan goc
điều tra
dieu tra
phân tích
phan tich
```

---

### Research / reporting signals

English keywords and phrases such as:

```
research
investigate
analyze
analysis
report
write a report
findings
benchmark
compare approaches
root cause
```

Vietnamese keywords and phrases such as:

```
nghiên cứu
nghien cuu
tìm hiểu
tim hieu
khảo sát
khao sat
phân tích
phan tich
báo cáo
bao cao
tổng hợp
tong hop
so sánh
so sanh
đánh giá
danh gia
nguyên nhân gốc
nguyen nhan goc
```

---

### Multi-step instructions

Requests that clearly require multiple sequential tasks.

Observable examples:

```
first ... then ...
step 1 / step 2
compare and recommend
review then implement
trước tiên ... sau đó ...
bước 1 / bước 2
so sánh rồi đề xuất
xem xét rồi triển khai
```

Typical task families that should route to `DEEP` when matched by explicit observable triggers:

- coding
- thinking
- brainstorming
- researching
- reporting

Typical task families that should route to `FAST` when no deep trigger matches:

- chit-chat
- language tasks
- simple Q&A
- lightweight "use RAG or not" classification

Typical explicit `FAST` hints, useful for logging but not required for default routing:

English:

```
hello
hi
thanks
translate
translation
what does this mean
define
quick question
```

Vietnamese:

```
xin chào
chào
cảm ơn
dịch
dịch giúp
nghĩa là gì
định nghĩa
hỏi nhanh
```

---

If none of these rules match:

Route to **fast model (Gemma)**.

---

# 8. Policy System

Implement policy-driven normalization.

Interface:

```python
class MessagePolicy(ABC):

    family: str
    policy_name: str

    def detect(self, model: str) -> bool: ...
    def normalize(self, messages: List[InternalMessage]): ...
    def validate(self, messages: List[InternalMessage]): ...
```

---

# 9. Default Policy

```
passthrough-v1
```

Behavior:

- No transformation
- Forward messages unchanged

Used for non-strict models.

---

# 10. Gemma Policy

```
gemma-strict-v1
```

Rules:

### Fold system into first user

```
system + user -> user
```

---

### Fold developer into user

Developer treated like system.

---

### Serialize unsupported roles

```
tool
function
observation
```

Example serialization:

```
[tool]
content
```

---

### Merge consecutive roles

```
user + user -> user
```

Separator:

```
\n\n
```

---

### Enforce alternation

Final order must be:

```
user assistant user assistant
```

Otherwise return HTTP 422.

---

### Remove empty messages

Whitespace-only messages removed.

---

# 11. Model Family Detection

Mapping:

```python
MODEL_PREFIX_FAMILY = {
    "gemma": "gemma",
    "llama": "passthrough",
    "qwen": "passthrough"
}
```

Rule:

```
model.startswith(prefix)
```

Family detection occurs **after routing**.

---

# 12. Upstream Client

Forward requests to llama.cpp server.

Default upstream URL:

```
http://127.0.0.1:8080
```

Forward path:

```
/v1/chat/completions
```

Requirements:

- Use `httpx.AsyncClient`
- Preserve parameters
- Support streaming
- Allow retry/failback

---

# 13. Failback Behavior

Failback applies **only to non-streaming requests**.

Allowed when:

```
network error
connect timeout
read timeout
connection reset
```

If initial model fails:

```
fast -> deep
deep -> fast
```

No failback for:

```
stream=true
validation errors
4xx request errors
```

Failback must preserve the same logical behavior contract:

- first attempt uses the routed logical mode and its resolved real model name
- fallback swaps to the alternate logical mode and alternate resolved real model name
- the adapter should re-run family detection and normalization for the fallback model before retrying upstream

---

# 14. Streaming Support

If request contains:

```
"stream": true
```

Adapter must:

- Route normally
- Forward request
- Passthrough SSE stream
- **Disable failback**

Content type:

```
text/event-stream
```

---

# 15. Logging

Structured JSON logs using `structlog`.

Required fields:

```
timestamp
request_id
path
client_requested_model
resolved_model
route_label
family
policy
duration_ms
```

Optional:

```
route_reasons
normalized_messages
fallback_attempted
```

---

# 16. Configuration

Environment-based config.

Example:

```
UPSTREAM_BASE_URL=http://127.0.0.1:8080

FAST_MODEL=gemma-3-4b
DEEP_MODEL=qwen3.5-2B

ENABLE_ROUTING=true
ENABLE_DEBUG_ENDPOINTS=true
LOG_NORMALIZED_REQUESTS=true
```

Dependency and delivery constraints:

- use open-source libraries only
- prefer existing SDK libraries already aligned with the current stack
- add no new dependencies unless necessary
- code and config changes are allowed because the adapter is in an early development cycle
- keep deployment and runtime-related delivery changes inside the Python app where practical

---

# 17. Unit Tests

Required tests.

### Router tests

```
simple prompt -> fast
code block -> deep
tool role -> deep
debug keyword -> deep
```

---

### Normalization tests

```
system folding
merge user messages
tool serialization
alternation validation
```

---

### Endpoint tests

```
client model ignored for routing
failback on network error
streaming passthrough
debug endpoint output
```

---

# 18. README Requirements

README must explain:

- adapter architecture
- routing system
- normalization policies
- environment configuration
- running instructions
- testing instructions

Run command:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

# 19. Acceptance Criteria

Implementation is complete if:

- Adapter accepts OpenAI-compatible requests
- Router correctly selects Gemma or Qwen
- Gemma normalization prevents role errors
- Streaming responses work
- Failback works for non-streaming
- Debug endpoint shows routing metadata
- Upstream request uses the resolved real model name from env
- Final response returns the actual resolved model name that processed the request
- Unit tests pass
- Code structure matches architecture

Implementation preferences collected during SMART POLE clarification:

- target delivery window: one day with AI coding agents
- the team is familiar with FastAPI and AI coding agents such as Codex and AntiGravity
- reviewer priority: clear documentation, understandable code, maintainability, and architectural cleanliness

---

# End of Task Specification v1.2
