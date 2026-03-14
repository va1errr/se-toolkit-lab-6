# Agent Architecture

## Overview

This agent is a CLI tool that calls an LLM with tools to answer questions about the project documentation. It implements an **agentic loop** where the LLM can iteratively call tools (`read_file`, `list_files`) to gather information before providing a final answer.

## Architecture

```
User question (CLI arg)
    ↓
agent.py
    ↓
Agentic Loop:
  1. Build request with tools + messages
  2. Call LLM
  3. If tool_calls → execute tools, append results, go to 1
  4. If no tool_calls → extract answer + source, output JSON
    ↓
JSON output to stdout
```

## LLM Provider

**Provider:** Qwen Code API
- Self-hosted on VM via [qwen-code-oai-proxy](https://github.com/inno-se-toolkit/qwen-code-oai-proxy)
- OpenAI-compatible chat completions API
- 1000 free requests per day

**Model:** `qwen3-coder-plus`
- Strong coding capabilities
- Good tool calling support

**Configuration:**
- API Base: `http://localhost:42005/v1`
- API Key: stored in `.env.agent.secret`
- Model name: configurable in `.env.agent.secret`

## Tools

The agent exposes two tools as OpenAI-compatible function-calling schemas:

### `read_file`

Read contents of a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as a string, or an error message if:
- File doesn't exist
- Path is outside the project directory (security check)
- Path is not a file (e.g., a directory)

**Security:** Uses `validate_path()` to ensure the resolved path is within the project root. Rejects paths with `../` traversal.

### `list_files`

List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of file/directory names, or an error message if:
- Directory doesn't exist
- Path is outside the project directory (security check)
- Path is not a directory

**Security:** Same path validation as `read_file`.

## Agentic Loop

The agentic loop allows the LLM to iteratively gather information before answering:

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
        answer = response.content
        source = extract_source(tool_calls_log)
        return {"answer": answer, "source": source, "tool_calls": tool_calls_log}
```

### Key Design Decisions

1. **Message accumulation**: Tool results are appended as `tool` role messages, allowing the LLM to reason about previous results when deciding the next action.

2. **Termination conditions**:
   - **Normal**: LLM responds without tool calls (has enough information to answer)
   - **Max limit**: Reached 10 tool calls (prevents infinite loops)

3. **Tool call logging**: Every tool call is recorded with its arguments and result, enabling test verification and debugging.

## System Prompt Strategy

The system prompt guides the LLM's behavior:

```
You are a documentation assistant for a software engineering lab. You have access to tools that let you read files and list directories in the project repository.

Your task is to answer questions about the project by:
1. Using `list_files` to discover what files exist in the wiki directory
2. Using `read_file` to read relevant files and find specific information
3. Providing a clear answer with a source reference

When you provide your final answer, always include:
- The answer itself
- A source reference in the format: `wiki/filename.md#section-anchor`
```

### Why This Prompt Works

- **Tool usage guidance**: Explicitly tells the LLM when to use each tool
- **Source requirement**: Ensures answers are traceable to documentation
- **Stopping condition**: Implies the LLM should stop calling tools once it has enough information

## Path Security

### Threat Model

Users (or a malicious LLM) might attempt to access files outside the project directory using path traversal (e.g., `../../etc/passwd`).

### Mitigation Strategy

```python
PROJECT_ROOT = Path(__file__).parent.resolve()

def validate_path(relative_path: str) -> tuple[bool, Path | str]:
    full_path = (PROJECT_ROOT / relative_path).resolve()
    
    # Check if resolved path is within project root
    if not str(full_path).startswith(str(PROJECT_ROOT)):
        return False, "Error: Path traversal not allowed"
    
    return True, full_path
```

**How it works:**
1. Constructs the full path from project root
2. Resolves to canonical absolute path (follows symlinks, normalizes `..`)
3. Verifies the resolved path starts with the project root prefix

## Components

### `agent.py`

**Entry point:** `uv run agent.py "<question>"`

**Modules:**

1. **`Settings`** (pydantic-settings)
   - Loads configuration from `.env.agent.secret`
   - Fields: `llm_api_key`, `llm_api_base`, `llm_model`

2. **`get_tools()`**
   - Returns OpenAI-compatible tool schemas
   - Defines `read_file` and `list_files` with descriptions and parameters

3. **`validate_path()`**
   - Security check for path traversal attacks
   - Returns `(True, resolved_path)` or `(False, error_message)`

4. **`read_file()` / `list_files()`**
   - Tool implementations with path validation
   - Return file contents or error messages

5. **`execute_tool()`**
   - Dispatcher that calls the appropriate tool function
   - Handles unknown tool names

6. **`get_system_prompt()`**
   - Returns the system prompt that guides LLM behavior

7. **`build_request()`**
   - Constructs OpenAI-compatible request body with tools

8. **`call_llm()`**
   - Makes HTTP POST using `httpx`
   - 60 second timeout
   - Returns parsed JSON response

9. **`run_agentic_loop()`**
   - Core agentic loop implementation
   - Manages message history, tool execution, and termination

10. **`main()`**
    - Parses CLI arguments
    - Orchestrates the flow
    - Outputs JSON to stdout

## Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

- `answer` (string, required): The LLM's answer
- `source` (string, required): Wiki section reference (file path + section anchor)
- `tool_calls` (array, required): All tool calls made during the agentic loop

## How to Run

1. **Set up environment:**
   ```bash
   cp .env.agent.example .env.agent.secret
   # Edit .env.agent.secret with your API key and endpoint
   ```

2. **Run the agent:**
   ```bash
   uv run agent.py "How do you resolve a merge conflict?"
   ```

3. **Output:**
   ```json
   {"answer": "...", "source": "wiki/git-workflow.md#...", "tool_calls": [...]}
   ```

## Error Handling

- **HTTP errors**: Logged to stderr, exit code 1
- **Timeout (>60s)**: Logged to stderr, exit code 1
- **Invalid response**: Logged to stderr, exit code 1
- **Missing CLI argument**: Usage hint to stderr, exit code 1
- **Path traversal attempt**: Returns error message in tool result (doesn't crash)
- **File not found**: Returns error message in tool result

## Testing

Run the regression tests:
```bash
uv run pytest tests/test_agent.py -v
```

**Test coverage:**
- `test_agent_output_format`: Verifies JSON structure with required fields
- `test_merge_conflict_question`: Verifies `read_file` tool usage and source extraction
- `test_wiki_listing_question`: Verifies `list_files` tool usage

## Future Extensions (Task 3)

- Add `query_api` tool to query the FastAPI backend
- Enhanced source extraction with better section anchor detection
- Improved error handling for tool execution failures
