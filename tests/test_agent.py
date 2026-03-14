"""Regression tests for agent.py."""

import json
import subprocess

import pytest


def test_agent_output_format():
    """Test that agent.py outputs valid JSON with required fields."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    output = json.loads(result.stdout)

    # Verify required fields
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"

    # Verify answer is non-empty
    assert output["answer"], "Answer should not be empty"


def test_merge_conflict_question():
    """Test that asking about merge conflicts uses read_file and references a git-related file."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    output = json.loads(result.stdout)

    # Verify tool_calls contains read_file
    assert len(output["tool_calls"]) > 0, "Expected at least one tool call"
    
    tool_names = [tc["tool"] for tc in output["tool_calls"]]
    assert "read_file" in tool_names, f"Expected 'read_file' in tool_calls, got: {tool_names}"

    # Verify source references a git-related .md file
    source = output.get("source", "")
    assert ".md" in source, f"Expected '.md' in source, got: {source}"
    # The source should mention git or conflict-related content
    assert "git" in source.lower() or "conflict" in source.lower(), f"Expected git or conflict reference in source, got: {source}"


def test_wiki_listing_question():
    """Test that asking about wiki files uses list_files."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "What files are in the wiki?"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    output = json.loads(result.stdout)

    # Verify tool_calls contains list_files
    assert len(output["tool_calls"]) > 0, "Expected at least one tool call"
    
    tool_names = [tc["tool"] for tc in output["tool_calls"]]
    assert "list_files" in tool_names, f"Expected 'list_files' in tool_calls, got: {tool_names}"
