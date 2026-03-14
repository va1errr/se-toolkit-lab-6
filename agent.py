#!/usr/bin/env python3
"""
Agent CLI - Calls an LLM to answer questions.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "tool_calls": []}
"""

import json
import sys
from pathlib import Path

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from .env.agent.secret."""

    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env.agent.secret")

    llm_api_key: str
    llm_api_base: str
    llm_model: str = "qwen3-coder-plus"


def build_request(question: str, settings: Settings) -> dict:
    """Build the OpenAI-compatible request body."""
    return {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
    }


def call_lllm(request_body: dict, settings: Settings) -> str:
    """Make HTTP POST to LLM API and extract the answer."""
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }

    print(f"Calling LLM at {url}...", file=sys.stderr)

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=request_body)
        response.raise_for_status()

    data = response.json()
    answer = data["choices"][0]["message"]["content"]
    return answer


def main():
    """Entry point: parse args, call LLM, output JSON."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load configuration
    settings = Settings()
    print(f"Using model: {settings.llm_model}", file=sys.stderr)

    # Build request and call LLM
    request_body = build_request(question, settings)
    answer = call_lllm(request_body, settings)

    # Output result as JSON
    result = {"answer": answer, "tool_calls": []}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
