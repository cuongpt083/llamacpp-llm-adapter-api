from typing import List

from app.models.api_models import ChatCompletionMessage
from app.routing.models import RouteDecision
from app.routing.rules import CODE_BLOCK_PATTERN, DEEP_KEYWORDS, DEEP_ROLE_TRIGGERS, MULTISTEP_PATTERNS, normalize_text


class PromptRouter:
    def __init__(self, fast_model: str, deep_model: str):
        self.fast_model = fast_model
        self.deep_model = deep_model

    def route(self, client_requested_model: str | None, messages: List[ChatCompletionMessage]) -> RouteDecision:
        reasons: List[str] = []

        for message in messages:
            if message.role in DEEP_ROLE_TRIGGERS:
                reasons.append(f"matched_role:{message.role}")
                return RouteDecision(
                    client_requested_model=client_requested_model,
                    route_label="deep",
                    resolved_model=self.deep_model,
                    reasons=reasons,
                )

        full_text = "\n".join(message.content or "" for message in messages)
        if CODE_BLOCK_PATTERN.search(full_text):
            reasons.append("matched_pattern:code_block")
            return RouteDecision(
                client_requested_model=client_requested_model,
                route_label="deep",
                resolved_model=self.deep_model,
                reasons=reasons,
            )

        normalized_text = normalize_text(full_text)

        for keyword in DEEP_KEYWORDS:
            if keyword in normalized_text:
                reasons.append(f"matched_keyword:{keyword}")
                return RouteDecision(
                    client_requested_model=client_requested_model,
                    route_label="deep",
                    resolved_model=self.deep_model,
                    reasons=reasons,
                )

        for pattern in MULTISTEP_PATTERNS:
            if pattern in normalized_text:
                reasons.append(f"matched_pattern:{pattern}")
                return RouteDecision(
                    client_requested_model=client_requested_model,
                    route_label="deep",
                    resolved_model=self.deep_model,
                    reasons=reasons,
                )

        return RouteDecision(
            client_requested_model=client_requested_model,
            route_label="fast",
            resolved_model=self.fast_model,
            reasons=["default:fast"],
        )
