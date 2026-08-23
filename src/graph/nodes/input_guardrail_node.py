import re
import logging

from src.graph.state.agentstate import AgentState

logger = logging.getLogger(__name__)

PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous instructions",
    r"disregard\s+(all\s+)?previous instructions",
    r"forget\s+(all\s+)?previous instructions",
    r"reveal\s+(the\s+)?system prompt",
    r"show\s+(me\s+)?your\s+system prompt",
    r"act\s+as\s+(an?\s+)?unrestricted",
    r"jailbreak",
)


def contains_prompt_injection(text: str) -> bool:
    """Return whether text contains common prompt-injection instructions."""
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in PROMPT_INJECTION_PATTERNS
    )

def input_guardrail_node(state: AgentState) -> dict:
    """Check the current user query for common prompt-injection patterns."""
    logger.info("Running input guardrail node to check for prompt-injection patterns.")
    try:
        user_text = state.get("user_query", "")
        if not isinstance(user_text, str):
            raise TypeError("user_query must be a string")

        is_safe = not contains_prompt_injection(user_text)
    except Exception:
        logger.exception("Input guardrail evaluation failed")
        return {
            "is_input_safe": False,
            "error": True,
        }

    if not is_safe:
        logger.warning("Security flag: prompt-injection pattern detected.")

    return {"is_input_safe": is_safe}