#!/usr/bin/env python3
"""
Agent CLI - Calls an LLM with tools to answer questions.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
"""

import json
import re
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


# Project root for path security
PROJECT_ROOT = Path(__file__).parent.resolve()

# Maximum tool calls per question
MAX_TOOL_CALLS = 10


def get_tools() -> list[dict]:
    """Return OpenAI-compatible tool schemas for function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read contents of a file from the project repository. Use this to find specific information in documentation files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what files exist in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki')"
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    ]


def validate_path(relative_path: str) -> tuple[bool, Path | str]:
    """
    Validate that a path is within the project directory.
    
    Returns:
        (True, resolved_path) if valid
        (False, error_message) if invalid
    """
    try:
        # Construct full path and resolve to canonical form
        full_path = (PROJECT_ROOT / relative_path).resolve()
        
        # Check if resolved path is within project root
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return False, "Error: Path traversal not allowed - cannot access files outside project directory"
        
        return True, full_path
    except Exception as e:
        return False, f"Error: Invalid path - {e}"


def read_file(path: str) -> str:
    """
    Read a file from the project repository.
    
    Args:
        path: Relative path from project root
        
    Returns:
        File contents or error message
    """
    is_valid, result = validate_path(path)
    if not is_valid:
        return result  # type: ignore
    
    file_path = result  # type: ignore
    
    if not file_path.exists():
        return f"Error: File not found: {path}"
    
    if not file_path.is_file():
        return f"Error: Not a file: {path}"
    
    try:
        return file_path.read_text()
    except Exception as e:
        return f"Error: Could not read file - {e}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.
    
    Args:
        path: Relative directory path from project root
        
    Returns:
        Newline-separated listing or error message
    """
    is_valid, result = validate_path(path)
    if not is_valid:
        return result  # type: ignore
    
    dir_path = result  # type: ignore
    
    if not dir_path.exists():
        return f"Error: Directory not found: {path}"
    
    if not dir_path.is_dir():
        return f"Error: Not a directory: {path}"
    
    try:
        entries = sorted(dir_path.iterdir())
        names = [entry.name for entry in entries]
        return "\n".join(names)
    except Exception as e:
        return f"Error: Could not list directory - {e}"


def execute_tool(tool_name: str, args: dict) -> str:
    """
    Execute a tool and return its result.
    
    Args:
        tool_name: Name of the tool to execute
        args: Arguments for the tool
        
    Returns:
        Tool result as a string
    """
    if tool_name == "read_file":
        return read_file(args.get("path", ""))
    elif tool_name == "list_files":
        return list_files(args.get("path", ""))
    else:
        return f"Error: Unknown tool: {tool_name}"


def get_system_prompt() -> str:
    """Return the system prompt that guides the LLM's behavior."""
    return """You are a documentation assistant for a software engineering lab. You have access to tools that let you read files and list directories in the project repository.

Your task is to answer questions about the project by:
1. Using `list_files` to discover what files exist in the wiki directory
2. Using `read_file` to read relevant files and find specific information
3. Providing a clear answer with a source reference

When you provide your final answer, always include:
- The answer itself
- A source reference in the format: `wiki/filename.md#section-anchor`

The source reference should point to the specific file and section that contains the answer. Use markdown-style anchors (lowercase, hyphens instead of spaces).

Stop calling tools once you have enough information to answer the question."""


def build_request(question: str, settings: Settings, messages: list[dict] | None = None) -> dict:
    """Build the OpenAI-compatible request body with tools."""
    if messages is None:
        messages = [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": question},
        ]
    
    return {
        "model": settings.llm_model,
        "messages": messages,
        "tools": get_tools(),
    }


def call_llm(request_body: dict, settings: Settings) -> dict:
    """
    Make HTTP POST to LLM API and return the full response.
    
    Returns:
        Parsed JSON response from the LLM
        
    Raises:
        httpx.HTTPStatusError: On HTTP error
        Exception: On other errors
    """
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }

    print(f"Calling LLM at {url}...", file=sys.stderr)

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=request_body)
        response.raise_for_status()

    return response.json()


def call_llm_safe(request_body: dict, settings: Settings) -> dict | None:
    """
    Call LLM with error handling. Returns None on failure.
    """
    try:
        return call_llm(request_body, settings)
    except Exception as e:
        print(f"LLM call failed: {e}", file=sys.stderr)
        return None


def extract_section_anchor(text: str, filename: str) -> str:
    """
    Try to extract a section anchor from the text based on the filename.
    
    This is a best-effort function to find relevant section headers.
    """
    # Look for markdown headers that might be relevant
    headers = re.findall(r'^#+\s+(.+)$', text, re.MULTILINE)
    
    # Common keywords for section matching
    keywords = ['merge', 'conflict', 'resolve', 'file', 'list', 'wiki', 'directory']
    
    for header in headers:
        header_lower = header.lower()
        for keyword in keywords:
            if keyword in header_lower:
                # Convert header to anchor format
                anchor = header.lower().replace(' ', '-').replace(',', '').replace('.', '')
                return f"{filename}#{anchor}"
    
    # Default to just the filename if no specific section found
    return filename


def run_agentic_loop(question: str, settings: Settings) -> dict:
    """
    Run the agentic loop: call LLM, execute tools, repeat until answer found.
    
    Args:
        question: User's question
        settings: Configuration settings
        
    Returns:
        Result dict with answer, source, and tool_calls
    """
    # Initialize messages with system prompt and user question
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": question},
    ]
    
    tool_calls_log = []
    
    for iteration in range(MAX_TOOL_CALLS):
        print(f"\n[Iteration {iteration + 1}/{MAX_TOOL_CALLS}]", file=sys.stderr)

        # Build request and call LLM
        request_body = build_request(question, settings, messages)
        response_data = call_llm_safe(request_body, settings)
        
        # Handle LLM failure
        if response_data is None:
            print("LLM call failed, returning partial result", file=sys.stderr)
            break

        # Extract the assistant message
        assistant_message = response_data["choices"][0]["message"]
        content = assistant_message.get("content", "")
        tool_calls = assistant_message.get("tool_calls", [])
        
        print(f"LLM response: tool_calls={len(tool_calls)}, content_length={len(content) if content else 0}", file=sys.stderr)
        
        # Check if LLM wants to call tools
        if tool_calls:
            # First, append the assistant's message with tool_calls
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls
            })
            
            # Execute each tool call
            for tool_call in tool_calls:
                function = tool_call["function"]
                tool_name = function["name"]
                tool_args = json.loads(function["arguments"])

                print(f"Executing tool: {tool_name}({tool_args})", file=sys.stderr)

                # Execute the tool
                result = execute_tool(tool_name, tool_args)

                # Log the tool call
                tool_calls_log.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result
                })

                # Append tool result to messages for the LLM to see
                # OpenAI format: role="tool", tool_call_id, content
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", "unknown"),
                    "content": result
                })

            # Continue the loop - LLM will reason about tool results
            continue
        else:
            # LLM provided a final answer (no tool calls)
            print("LLM provided final answer", file=sys.stderr)
            
            # Extract source from the answer or from tool calls
            source = "wiki"  # Default source
            
            # Try to find a source reference in the content
            if tool_calls_log:
                # Look for the last read_file call to determine source
                for tc in reversed(tool_calls_log):
                    if tc["tool"] == "read_file":
                        file_path = tc["args"].get("path", "wiki")
                        # Try to extract a section anchor from the content
                        anchor = extract_section_anchor(tc["result"], file_path)
                        source = anchor
                        break
            
            return {
                "answer": content,
                "source": source,
                "tool_calls": tool_calls_log
            }
    
    # Reached max tool calls - return whatever we have
    print("Reached max tool calls, returning partial result", file=sys.stderr)
    
    # Try to extract an answer from the last tool results
    source = "wiki"
    if tool_calls_log:
        for tc in reversed(tool_calls_log):
            if tc["tool"] == "read_file":
                file_path = tc["args"].get("path", "wiki")
                anchor = extract_section_anchor(tc["result"], file_path)
                source = anchor
                break
    
    # If we have no answer from LLM, construct one from tool results
    answer = content if content else "I reached the maximum number of tool calls. Please refine your question."
    
    return {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_log
    }


def main():
    """Entry point: parse args, run agentic loop, output JSON."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load configuration
    settings = Settings()
    print(f"Using model: {settings.llm_model}", file=sys.stderr)

    # Run the agentic loop
    result = run_agentic_loop(question, settings)

    # Output result as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()
