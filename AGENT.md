# Agent Architecture

## Overview

This agent is a CLI tool that calls an LLM to answer questions. It forms the foundation for the agentic system that will be extended with tools in Tasks 2-3.

## Architecture

```
User question (CLI arg)
    ↓
agent.py
    ↓
Build OpenAI-compatible request
    ↓
HTTP POST to LLM API
    ↓
Parse response
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
- Good tool calling support (used in Task 2+)

**Configuration:**
- API Base: `http://localhost:42005/v1`
- API Key: stored in `.env.agent.secret`
- Model name: configurable in `.env.agent.secret`

## Components

### `agent.py`

**Entry point:** `uv run agent.py "<question>"`

**Modules:**

1. **`Settings`** (pydantic-settings)
   - Loads configuration from `.env.agent.secret`
   - Fields: `llm_api_key`, `llm_api_base`, `llm_model`
   - Type-safe environment variable handling

2. **`build_request()`**
   - Constructs OpenAI-compatible request body
   - System prompt: "You are a helpful assistant." (minimal for Task 1)
   - User message: the question from CLI

3. **`call_llm()`**
   - Makes HTTP POST using `httpx`
   - 60 second timeout
   - Raises on HTTP errors
   - Extracts answer from `choices[0].message.content`

4. **`main()`**
   - Parses CLI arguments
   - Orchestrates the flow
   - Outputs JSON to stdout
   - Logs debug info to stderr

## Output Format

```json
{"answer": "The LLM's response", "tool_calls": []}
```

- `answer`: string - the LLM's answer
- `tool_calls`: array - empty for Task 1, populated in Task 2+

## How to Run

1. **Set up environment:**
   ```bash
   cp .env.agent.example .env.agent.secret
   # Edit .env.agent.secret with your API key and endpoint
   ```

2. **Run the agent:**
   ```bash
   uv run agent.py "What does REST stand for?"
   ```

3. **Output:**
   ```json
   {"answer": "Representational State Transfer.", "tool_calls": []}
   ```

## Error Handling

- HTTP errors: logged to stderr, exit code 1
- Timeout (>60s): logged to stderr, exit code 1
- Invalid response: logged to stderr, exit code 1
- Missing CLI argument: usage hint to stderr, exit code 1

## Testing

Run the regression test:
```bash
uv run pytest tests/test_agent.py -v
```

## Future Extensions (Tasks 2-3)

- **Task 2:** Add tools (`read_file`, `list_files`, `query_api`)
- **Task 3:** Add agentic loop (repeated tool calls until answer found)
- Enhanced system prompt with domain knowledge
