# Task 1 Plan: Call an LLM from Code

## LLM Provider and Model

**Provider:** Qwen Code API (running locally on VM)
- Uses OpenAI-compatible chat completions API
- 1000 free requests per day
- No credit card required

**Model:** `qwen3-coder-plus`
- Strong tool calling capabilities (will be used in Task 2)
- Good code understanding

**Configuration:**
- API Base: `http://localhost:42005/v1`
- API Key: loaded from `.env.agent.secret`
- Model: loaded from `.env.agent.secret`

## Agent Structure

### Components

1. **Configuration Loader**
   - Read environment variables from `.env.agent.secret`
   - Use `pydantic-settings` (already in dependencies) for type-safe config
   - Fields: `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

2. **HTTP Client**
   - Use `httpx` (async HTTP client, already in dependencies)
   - POST to `{LLM_API_BASE}/chat/completions`
   - Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
   - Timeout: 60 seconds

3. **Request Builder**
   - Build OpenAI-compatible request body:
     ```json
     {
       "model": "qwen3-coder-plus",
       "messages": [
         {"role": "system", "content": "You are a helpful assistant."},
         {"role": "user", "content": "<question from CLI>"}
       ]
     }
     ```

4. **Response Parser**
   - Extract `choices[0].message.content` from API response
   - Format output as JSON: `{"answer": "...", "tool_calls": []}`

5. **CLI Entry Point**
   - Parse command-line argument (the question)
   - Call the agent
   - Print JSON to stdout
   - Print debug logs to stderr
   - Exit code 0 on success

### Data Flow

```
CLI argument (question)
    ↓
Build request (system + user messages)
    ↓
HTTP POST to LLM API
    ↓
Parse response (extract answer)
    ↓
Output JSON to stdout
```

### Error Handling

- HTTP errors (non-2xx): log to stderr, exit with code 1
- Timeout (>60s): log to stderr, exit with code 1
- Invalid JSON response: log to stderr, exit with code 1
- Missing answer in response: log to stderr, exit with code 1

### Testing

- Run `agent.py "What is 2+2?"` 
- Parse stdout as JSON
- Verify `answer` field exists and is non-empty
- Verify `tool_calls` field exists and is an array

## Files to Create

1. `plans/task-1.md` - this plan
2. `agent.py` - the agent CLI
3. `AGENT.md` - documentation
4. `tests/test_agent.py` - regression test (1 test)
5. `.env.agent.secret` - configuration (copy from `.env.agent.example`)
