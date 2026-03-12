# LLM Adapter for llama.cpp

## Overview

This project implements a **message normalization adapter** that sits between agent frameworks (such as ZeroClaw) and a `llama.cpp` model server. Its primary purpose is to ensure that requests sent to models follow the strict conversation templates expected by different model families.

Many modern LLMs enforce specific message role patterns. For example, some models require the conversation roles to strictly alternate (`user → assistant → user → assistant`). When frameworks generate prompts with additional roles such as `system`, `developer`, `tool`, or consecutive identical roles, the model server may reject the request.

This adapter solves that problem by **normalizing the conversation structure before forwarding requests to the model server**.

---

# Why This Adapter Exists

## Problem Background

Agent frameworks often produce rich conversation structures like:

```
system
developer
user
assistant
tool
observation
```

However, model inference servers — particularly `llama.cpp` when using strict chat templates — expect a simplified structure.

For example, Gemma models require:

```
user
assistant
user
assistant
```

and will throw runtime errors such as:

```
Conversation roles must alternate user/assistant/user/assistant
```

These errors occur because the model's **Jinja chat template validation fails** when unexpected roles or ordering appear.

### Typical Failure Scenario

Agent framework sends:

```json
[
  {"role": "system", "content": "You are a helpful assistant"},
  {"role": "user", "content": "Hello"},
  {"role": "user", "content": "Who is the current POTUS?"}
]
```

Gemma template requires alternating roles, so the request fails.

---

## Why Not Fix This in the Agent Framework?

Agent frameworks typically:

- support multiple models
- support tools and reasoning loops
- maintain richer conversation state

Changing the framework to satisfy each model's chat template would create **model-specific logic scattered throughout the system**.

Instead, we isolate this complexity in a **single adapter layer**.

---

# Adapter Responsibilities

The adapter performs the following functions:

### 1. Message Normalization

Convert arbitrary conversation structures into model-compatible sequences.

Example transformation:

Input:

```json
[
  {"role":"system","content":"You are helpful"},
  {"role":"user","content":"Hello"},
  {"role":"user","content":"Who is POTUS?"}
]
```

Normalized output:

```json
[
  {"role":"user","content":"You are helpful\n\nHello\n\nWho is POTUS?"}
]
```

---

### 2. Model-Specific Prompt Policies

Different model families have different prompt constraints.

Example policies:

| Model Family | Policy |
|---------------|--------|
| Gemma | Strict alternation |
| Llama | Allows system |
| Qwen | Allows tools |
| Mistral | Strict role ordering |

The adapter detects the model family and applies the appropriate transformation rules.

---

### 3. Validation

After normalization the adapter verifies that:

- the message order is valid
- unsupported roles are removed or serialized
- no empty messages remain
- the conversation alternates correctly

If validation fails, the adapter returns an error rather than sending a malformed request upstream.

---

### 4. Upstream Proxy

The adapter forwards the normalized request to `llama.cpp`.

Responsibilities include:

- forwarding parameters such as `temperature`, `max_tokens`
- preserving streaming responses
- mapping upstream errors to OpenAI-style responses

---

### 5. Debugging Support

A debug endpoint allows developers to inspect normalization results without calling the model.

Example:

```
POST /v1/chat/completions:normalize
```

Response:

- original messages
- normalized messages
- transformation log
- validation results

This greatly simplifies debugging prompt pipeline issues.

---

# Architecture Overview

```
Agent Framework (ZeroClaw)
            │
            │ OpenAI-compatible API
            ▼
+------------------------------------+
|      LLM Adapter Service           |
|------------------------------------|
| Request Parser                     |
| Model Family Detection             |
| Message Normalization Engine       |
| Policy Engine                      |
| Validation Engine                  |
| Upstream Proxy                     |
| Logging & Debug Tools              |
+------------------------------------+
            │
            │ normalized request
            ▼
        llama.cpp server
            │
            ▼
        LLM Model
```

---

# Core Components

## API Layer

Handles HTTP requests:

```
/healthz
/readyz
/v1/models
/v1/chat/completions
/v1/chat/completions:normalize
/v1/responses
```

---

## Policy Engine

Each model family implements a normalization policy.

Example:

```
gemma-strict-v1
passthrough-v1
```

Policies define:

- allowed roles
- message transformations
- validation rules

---

## Normalization Pipeline

Pipeline stages:

```
Parse Request
   ↓
Convert to Internal Messages
   ↓
Apply Policy Transformations
   ↓
Merge Messages
   ↓
Validate Conversation
   ↓
Build Upstream Request
```

---

## Upstream Client

Responsible for forwarding requests to `llama.cpp`.

Supports:

- JSON requests
- streaming SSE responses
- timeout handling

---

## Routing

The adapter can route each request to one of two logical modes:

- `FAST`
- `DEEP`

These logical modes are resolved to real upstream model ids from environment variables:

```env
FAST_MODEL=gemma-3-4b
DEEP_MODEL=qwen3.5-2B
```

Routing behavior:

- the client-provided `model` is accepted but not trusted for upstream routing
- the adapter classifies the request from observable prompt signals
- the upstream request uses the resolved real model name from env
- the final response returns the actual model name that processed the request
- both `/v1/chat/completions` and `/v1/responses` reuse the same routing and normalization flow

Typical `DEEP` triggers include:

- tool/function/observation roles
- code blocks
- coding or debugging keywords
- planning or reasoning keywords
- explicit multi-step instruction patterns

If no deep trigger matches, the adapter defaults to `FAST`.

## Responses API Compatibility

The adapter supports `POST /v1/responses` as a compatibility layer on top of the chat completions pipeline.

Non-streaming behavior:

- translates `responses.input` into chat messages
- reuses routing, normalization, and upstream forwarding
- wraps the final chat-completion result into a minimal Responses API-style object

Streaming behavior:

- accepts `stream=true` on `/v1/responses`
- translates the request into streaming chat completions internally
- returns `text/event-stream`
- currently uses minimal SSE pass-through compatibility mode rather than a full Responses API event-schema mapper

Current scope:

- intended to work with clients that expect `/v1/responses` to exist
- optimized for compatibility and delivery speed
- non-streaming response objects are wrapped
- streaming responses are proxied as SSE from the underlying chat-completions path

---

## Smart Pole Best Practices

When gathering requirements and designing new features for this adapter, use SMART POLE before writing code.

Recommended workflow:

1. Start with `brainstorming` when the request is still fuzzy.
2. Use `sp-coding-agent` to score readiness across the SP categories before implementation.
3. Fill missing SP-atoms, especially `A` and `O`, before coding:
   - `A` Aim: exact behavior, acceptance criteria, response contract
   - `O` Outline: authorized scope, refactor permission, boundaries
4. Capture the agreed rules in the implementation plan or design doc.
5. Only after the plan is explicit, move to `test-driven-development` and implement against failing tests first.

Practical lessons from this project:

- Do not start coding while routing behavior is still ambiguous.
- Make the model contract explicit early:
  - whether the adapter trusts the client `model`
  - which env vars resolve real upstream model ids
  - what `model` should be returned in the final response
- Separate logical routing labels such as `FAST` and `DEEP` from actual upstream model names.
- Prefer observable routing rules over vague semantic intent:
  - roles
  - code blocks
  - deterministic keywords and phrases
  - multi-step patterns
- Clarify whether refactoring is authorized before changing package structure.
- Confirm dependency constraints up front, for example "no new deps unless necessary".
- Record reviewer preferences early, such as maintainability, documentation clarity, and architectural cleanliness.
- Update the implementation plan once SP-atoms are resolved, so execution and review use the same contract.

Minimal SP checklist for this adapter:

- `S`: follow existing FastAPI and test patterns
- `M`: confirm team familiarity with FastAPI and routing/failover tasks
- `A`: define routing, failback, normalization, and response semantics
- `R`: define dependency and deployment constraints
- `T`: define delivery urgency
- `P`: define reviewer priorities
- `O`: define file and refactor scope
- `L`: confirm runtime stack and environment assumptions
- `E`: provide sample prompts, expected route decisions, or anti-examples

In practice, this means the plan should be updated before implementation, and tests should be written before production code changes.

---

# Example Request Flow

1. Client sends request

```
POST /v1/chat/completions
```

2. Adapter detects model family:

```
gemma
```

3. Normalization rules applied:

- fold system message
- merge user messages
- enforce alternation

4. Adapter forwards normalized request to llama.cpp.

5. Response returned to client.

---

# Supported Model Families (Initial)

| Family | Policy |
|------|------|
| gemma | gemma-strict-v1 |
| default | passthrough-v1 |

Future families may include:

- llama
- qwen
- mistral
- command-r

---

# Advantages of This Architecture

### Centralized Compatibility Layer

All model quirks handled in one place.

---

### Framework Independence

Works with:

- ZeroClaw
- LangChain
- custom agents
- any OpenAI-compatible client

---

### Safer Prompt Handling

Prevents runtime errors from invalid conversation structures.

---

### Easier Debugging

Normalization debugging endpoint helps inspect transformations.

---

# Future Enhancements

## Model Metadata Detection

Instead of detecting family from model name, the adapter can inspect:

```
tokenizer.chat_template
```

returned by the model server.

---

## Tool Role Support

Future versions may convert structured tool calls into model-compatible formats.

---

## Multi-Upstream Routing

Adapter could route requests to different backends:

```
llama.cpp
vLLM
TGI
OpenAI
```

---

## Prompt Template Engine

Adapter could support model-specific prompt templating.

Example:

```
Gemma format
ChatML format
Llama format
```

---

## Rate Limiting

Add per-client or per-model rate limits.

---

## Observability

Integration with monitoring systems:

- Prometheus
- OpenTelemetry
- Grafana

Metrics could include:

```
request latency
normalization failures
model usage
token counts
```

---

## Policy Plugins

Policies could become dynamic plugins.

Example:

```
/policies/gemma
/policies/llama
/policies/qwen
```

---

# Running the Adapter

Start server:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Example configuration:

```
UPSTREAM_BASE_URL=http://127.0.0.1:8080
FAST_MODEL=gemma-3-4b
DEEP_MODEL=qwen3.5-2B
ENABLE_ROUTING=true
ENABLE_DEBUG_ENDPOINTS=true
```

---

# Example Client Configuration

Point OpenAI-compatible clients to the adapter:

```
http://localhost:8000/v1
```

Instead of directly calling:

```
http://localhost:8080/v1
```

---

# Conclusion

This adapter provides a **robust compatibility layer between agent frameworks and LLM inference servers**.

It ensures that:

- conversation structures are valid
- model-specific prompt rules are respected
- upstream errors are avoided
- debugging and observability are improved

By isolating prompt normalization into a dedicated service, the overall system becomes **more reliable, extensible, and model-agnostic**.
