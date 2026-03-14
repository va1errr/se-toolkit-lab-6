# Task 1 Plan: Call an LLM from Code

## LLM Provider and Model

- **Provider**: Qwen Code API (self-hosted on VM via `qwen-code-oai-proxy`)
- **Model**: `qwen3-coder-plus`
- **API Base**: Read from `LLM_API_BASE` in `.env.agent.secret`
- **API Key**: Read from `LLM_API_KEY` in `.env.agent.secret`

## Agent Structure

### Input
- Command-line argument: the user's question (`sys.argv[1]`)

### Output
- Single JSON line to stdout:
  ```json
  {"answer": "<LLM response>", "tool_calls": []}
  ```
- All debug/logging output goes to stderr (`print(..., file=sys.stderr)`)

### Implementation Steps

1. **Load environment variables**
   - Read `.env.agent.secret` using `python-dotenv` or manual parsing
   - Extract `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

2. **Parse command-line input**
   - Get question from `sys.argv[1]`
   - Handle missing argument with usage message to stderr

3. **Call LLM API**
   - Use `httpx` (already in dependencies) for HTTP POST
   - Endpoint: `{LLM_API_BASE}/chat/completions`
   - Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
   - Body: OpenAI-compatible format with model and messages

4. **Parse response and output JSON**
   - Extract `content` from response choices
   - Output `{"answer": "<content>", "tool_calls": []}` to stdout
   - Use `json.dumps()` for proper formatting

### Error Handling

- Missing API key → exit with error message to stderr
- Missing question argument → print usage to stderr, exit non-zero
- Network errors → catch exception, print to stderr, exit non-zero
- Invalid API response → catch exception, print to stderr, exit non-zero
- Timeout (>60s) → let httpx handle with timeout parameter

## Dependencies

- `httpx` — already in `pyproject.toml`
- `python-dotenv` — may need to add, or manually parse `.env` file

## Testing

- Run `agent.py "What is 2+2?"` and verify JSON output
- Check that `answer` field contains LLM response
- Check that `tool_calls` is an empty array
- Verify no debug output goes to stdout
