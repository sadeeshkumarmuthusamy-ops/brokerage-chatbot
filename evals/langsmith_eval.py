"""Run LangSmith evaluations against the live chatbot HTTP endpoint."""

from __future__ import annotations

import sys
import uuid
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
from langsmith import Client, evaluate

# Allow this file to run as `python evals/langsmith_eval.py` from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.eval_settings import settings

DATASET_NAME = settings.langsmith_dataset
API_URL = settings.chatbot_api_url

SEED_EXAMPLES = [
    {
        "inputs": {"question": "What is the brokerage fee for vendor ABC today?"},
        "outputs": {
            "expected_keywords": ["brokerage"],
            "expected_human_in_loop": False,
        },
    },
    {
        "inputs": {"question": "How long has item X been here?"},
        "outputs": {
            "expected_keywords": ["item"],
            "expected_human_in_loop": False,
        },
    },
    {
        "inputs": {"question": "Update item size for SKU-990 to Large."},
        "outputs": {
            "expected_keywords": [],
            "expected_human_in_loop": True,
        },
    },
    {
            "inputs": {"question": "list the top 5 vendors by highest number of items"},
            "outputs": {
                "expected_keywords": [],
                "expected_human_in_loop": True,
            },
        },
        {
                    "inputs": {"question": "update the US vendors to MX"},
                    "outputs": {
                        "expected_keywords": [],
                        "expected_human_in_loop": True,
                    },
                },
]


def ensure_dataset(client: Client) -> str:
    """Create the smoke dataset once and return its name."""
    if not client.has_dataset(dataset_name=DATASET_NAME):
        client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Smoke tests for the brokerage chatbot API.",
        )
        client.create_examples(
            dataset_name=DATASET_NAME,
            inputs=[example["inputs"] for example in SEED_EXAMPLES],
            outputs=[example["outputs"] for example in SEED_EXAMPLES],
        )
    return DATASET_NAME


def check_api_available() -> None:
    """Fail before creating an experiment when the local API is not running."""
    parsed_url = urlsplit(API_URL)
    health_url = f"{parsed_url.scheme}://{parsed_url.netloc}/openapi.json"
    try:
        response = requests.get(health_url, timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(
            f"Chatbot API is unavailable at {API_URL}. "
            "Start it with: uvicorn src.api.server:app --host 127.0.0.1 --port 8000"
        ) from exc


def chatbot_api_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Adapt a LangSmith example into the chatbot API request contract."""
    started_at = time.perf_counter()
    response = requests.post(
        API_URL,
        json={
            "session_id": f"langsmith-{uuid.uuid4()}",
            "text": inputs["question"],
            "human_in_loop": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    result = response.json()
    result["_latency_ms"] = round((time.perf_counter() - started_at) * 1000, 2)
    return result


def api_contract_is_valid(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    required_fields = {"response", "human_in_loop", "decision_data"}
    missing_fields = required_fields - outputs.keys()
    return {
        "key": "api_contract_is_valid",
        "score": not missing_fields,
        "value": {"missing_fields": sorted(missing_fields)},
    }


def response_length_metric(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response_length = len(str(outputs.get("response", "")).strip())
    return {
        "key": "response_length_characters",
        "score": response_length,
        "value": response_length,
    }


def latency_metric(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    latency_ms = float(outputs.get("_latency_ms", 0))
    return {
        "key": "latency_ms",
        "score": latency_ms,
        "value": latency_ms,
    }


def response_is_present(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = str(outputs.get("response", "")).strip()
    return {
        "key": "response_is_present",
        "score": bool(response),
        "comment": "The API returned a non-empty response." if response else "Empty response.",
    }


def response_contains_expected_keywords(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected = (reference_outputs or {}).get("expected_keywords", [])
    response = str(outputs.get("response", "")).casefold()
    missing = [keyword for keyword in expected if keyword.casefold() not in response]
    return {
        "key": "response_contains_expected_keywords",
        "score": not missing,
        "value": {"missing": missing},
        "comment": "All expected markers found." if not missing else f"Missing: {missing}",
    }


def human_in_loop_matches_expectation(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected = bool((reference_outputs or {}).get("expected_human_in_loop", False))
    actual = bool(outputs.get("human_in_loop", False))
    return {
        "key": "human_in_loop_matches_expectation",
        "score": actual == expected,
        "value": {"expected": expected, "actual": actual},
    }


def main() -> None:
    if not settings.langsmith_api_key:
        raise SystemExit(
            "LANGSMITH_API_KEY must be set in the repository .env before running the evaluation."
        )

    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    check_api_available()
    client = Client(api_key=settings.langsmith_api_key)
    dataset_name = ensure_dataset(client)
    results = evaluate(
        chatbot_api_target,
        data=dataset_name,
        evaluators=[
            api_contract_is_valid,
            response_length_metric,
            latency_metric,
            response_is_present,
            response_contains_expected_keywords,
            human_in_loop_matches_expectation,
        ],
        experiment_prefix="brokerage-chatbot-api",
        metadata={"api_url": API_URL, "project": settings.langsmith_project},
        client=client,
    )
    print(results)
    print(f"View the experiment in LangSmith project: {settings.langsmith_project}")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        print(f"Chatbot API request failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
