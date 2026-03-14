#!/usr/bin/env python3
"""Agent CLI - sends questions to an LLM and returns structured JSON answers."""

import json
import os
import sys

import httpx
from dotenv import load_dotenv


def load_env() -> None:
    """Load environment variables from .env.agent.secret."""
    env_path = os.path.join(os.path.dirname(__file__), ".env.agent.secret")
    load_dotenv(env_path)


def get_llm_config() -> dict[str, str]:
    """Get LLM configuration from environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    if not api_key:
        print("Error: LLM_API_KEY not set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    if not api_base:
        print("Error: LLM_API_BASE not set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    if not model:
        print("Error: LLM_MODEL not set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    return {"api_key": api_key, "api_base": api_base, "model": model}


def call_lllm(question: str, config: dict[str, str]) -> str:
    """Call the LLM API and return the answer."""
    url = f"{config['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": question}],
    }

    print(f"Calling LLM at {url}...", file=sys.stderr)

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract the answer from the response
            answer = data["choices"][0]["message"]["content"]
            return answer

    except httpx.TimeoutException:
        print("Error: LLM request timed out (>60s)", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"Error: HTTP request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, IndexError) as e:
        print(f"Error: Unexpected API response format: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    # Check command-line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load configuration
    load_env()
    config = get_llm_config()

    # Call LLM and get answer
    answer = call_lllm(question, config)

    # Output structured JSON to stdout
    result = {
        "answer": answer,
        "tool_calls": [],
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
