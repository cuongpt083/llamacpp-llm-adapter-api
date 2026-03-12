from app.models.api_models import ChatCompletionMessage
from app.routing.router import PromptRouter


def test_router_defaults_to_fast_for_simple_chat():
    router = PromptRouter(fast_model="gemma-3-4b", deep_model="qwen3.5-2B")

    decision = router.route(
        client_requested_model="gpt-4o",
        messages=[ChatCompletionMessage(role="user", content="hello there")],
    )

    assert decision.route_label == "fast"
    assert decision.resolved_model == "gemma-3-4b"
    assert decision.reasons == ["default:fast"]


def test_router_routes_deep_for_english_coding_keywords():
    router = PromptRouter(fast_model="gemma-3-4b", deep_model="qwen3.5-2B")

    decision = router.route(
        client_requested_model="gpt-4o",
        messages=[ChatCompletionMessage(role="user", content="please help me debug this traceback")],
    )

    assert decision.route_label == "deep"
    assert decision.resolved_model == "qwen3.5-2B"
    assert "matched_keyword:traceback" in decision.reasons


def test_router_routes_deep_for_vietnamese_keywords_without_diacritics():
    router = PromptRouter(fast_model="gemma-3-4b", deep_model="qwen3.5-2B")

    decision = router.route(
        client_requested_model="gpt-4o",
        messages=[ChatCompletionMessage(role="user", content="hay lap ke hoach refactor API nay")],
    )

    assert decision.route_label == "deep"
    assert decision.resolved_model == "qwen3.5-2B"
    assert any(reason.startswith("matched_keyword:") for reason in decision.reasons)


def test_router_routes_deep_for_tool_roles():
    router = PromptRouter(fast_model="gemma-3-4b", deep_model="qwen3.5-2B")

    decision = router.route(
        client_requested_model="gpt-4o",
        messages=[
            ChatCompletionMessage(role="user", content="check status"),
            ChatCompletionMessage(role="tool", content="service ok"),
        ],
    )

    assert decision.route_label == "deep"
    assert decision.resolved_model == "qwen3.5-2B"
    assert "matched_role:tool" in decision.reasons
