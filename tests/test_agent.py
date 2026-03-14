"""Regression tests for agent.py CLI.

These tests run agent.py as a subprocess and verify the JSON output structure.
Run with: uv run pytest tests/test_agent.py -v
"""

import json
import subprocess

import pytest


class TestAgentOutput:
    """Test that agent.py produces valid JSON with required fields."""

    @pytest.mark.asyncio
    async def test_agent_returns_valid_json_with_required_fields(self):
        """Test that agent.py outputs valid JSON with 'answer' and 'tool_calls' fields."""
        # Run agent.py with a simple question
        result = subprocess.run(
            ["uv", "run", "agent.py", "What is 2+2?"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Check exit code
        assert result.returncode == 0, f"Agent failed: {result.stderr}"

        # Parse stdout as JSON
        output = result.stdout.strip()
        data = json.loads(output)

        # Check required fields are present
        assert "answer" in data, "Missing 'answer' field in output"
        assert "tool_calls" in data, "Missing 'tool_calls' field in output"

        # Check field types
        assert isinstance(data["answer"], str), "'answer' should be a string"
        assert isinstance(data["tool_calls"], list), "'tool_calls' should be an array"

        # Check answer is non-empty
        assert len(data["answer"]) > 0, "'answer' should not be empty"
