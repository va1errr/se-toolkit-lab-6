# Task 2: The Documentation Agent - Implementation Plan

## Overview

This task extends the agent from Task 1 with two tools (`read_file`, `list_files`) and implements an agentic loop that allows the LLM to call tools iteratively until it can answer the user's question.

## Tool Schemas

### Approach

Define tool schemas as OpenAI-compatible function definitions. Each schema includes:
- `name`: The tool name (e.g., `read_file`, `list_files`)
- `description`: What the tool does and when to use it
- `parameters`: JSON Schema defining required/optional arguments

### Schema Definitions

**`read_file`**:
```json
{
  "name": "read_file",
  "description": "Read contents of a file from the project repository",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative path from project root"}
    },
    "required": ["path"]
  }
}
```

**`list_files`**:
```json
{
  "name": "list_files",
  "description": "List files and directories at a given path",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative directory path from project root"}
    },
    "required": ["path"]
  }
}
```

### Implementation

Add a `get_tools()` function that returns the list of tool schemas. Pass these in the LLM request using the `tools` parameter.

## Agentic Loop

### Loop Structure

```python
messages = [system_prompt, user_question]
tool_calls_log = []

for iteration in range(MAX_TOOL_CALLS):  # max 10
    response = call_llm(messages, tools)
    
    if response has tool_calls:
        for tool_call in tool_calls:
            result = execute_tool(tool_call)
            tool_calls_log.append({tool, args, result})
            messages.append({"role": "tool", "content": result})
    else:
        # LLM provided final answer
        answer = extract_answer(response)
        source = extract_source(response)
        return {"answer": answer, "source": source, "tool_calls": tool_calls_log}
```

### Key Components

1. **Message accumulation**: Each tool result is appended as a `tool` role message so the LLM can reason about it
2. **Termination conditions**:
   - LLM responds without tool calls (has answer)
   - Reached 10 tool calls (max limit)
3. **Output extraction**: Parse the final LLM response to extract `answer` and `source`

## Path Security

### Threat

Users (or a malicious LLM) might try to access files outside the project directory using paths like `../../etc/passwd`.

### Validation Strategy

1. **Resolve to absolute path**: Use `Path.resolve()` to get the canonical absolute path
2. **Check prefix**: Verify the resolved path starts with the project root directory
3. **Reject traversal**: If the path escapes the project root, return an error message

### Implementation

```python
PROJECT_ROOT = Path(__file__).parent.resolve()

def validate_path(relative_path: str) -> tuple[bool, Path | str]:
    """Validate path is within project directory."""
    try:
        full_path = (PROJECT_ROOT / relative_path).resolve()
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return False, "Error: Path traversal not allowed"
        return True, full_path
    except Exception as e:
        return False, f"Error: {e}"
```

## System Prompt Strategy

The system prompt should guide the LLM to:
1. Use `list_files` to discover wiki files when unsure where information is
2. Use `read_file` to read relevant files and find answers
3. Always include a source reference (file path + section anchor) in the answer
4. Stop calling tools once enough information is gathered to answer

## Output Format

```json
{
  "answer": "The answer extracted from wiki content",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Testing Strategy

Two regression tests:

1. **Test merge conflict question**:
   - Input: `"How do you resolve a merge conflict?"`
   - Expect: `read_file` in tool_calls, `wiki/git-workflow.md` in source

2. **Test wiki listing question**:
   - Input: `"What files are in the wiki?"`
   - Expect: `list_files` in tool_calls

## Files to Modify

- `agent.py`: Add tool definitions, agentic loop, path validation
- `AGENT.md`: Document tools, loop, and system prompt strategy
- `tests/test_agent.py`: Add 2 new test functions
