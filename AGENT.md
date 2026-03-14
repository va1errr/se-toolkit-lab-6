# Agent Architecture

## Overview

This project implements a CLI agent (`agent.py`) that answers questions using an LLM. The agent receives a question via command-line argument, sends it to an LLM API, and returns a structured JSON response.

## LLM Provider

- **Provider**: Qwen Code API (self-hosted on VM via `qwen-code-oai-proxy`)
- **Model**: `qwen3-coder-plus`
- **API Format**: OpenAI-compatible chat completions API

## How It Works

```
User question (CLI arg) → agent.py → LLM API → JSON response
```

### Flow

1. **Input**: User provides a question as command-line argument:
   ```bash
   uv run agent.py "What does REST stand for?"
   ```

2. **Environment Loading**: The agent loads configuration from `.env.agent.secret`:
   - `LLM_API_KEY` — API authentication key
   - `LLM_API_BASE` — Base URL of the LLM API endpoint
   - `LLM_MODEL` — Model name to use

3. **API Call**: The agent makes an HTTP POST request to `{LLM_API_BASE}/chat/completions` with:
   - Authorization header with Bearer token
   - JSON body containing model and messages

4. **Output**: The agent outputs a single JSON line to stdout:
   ```json
   {"answer": "Representational State Transfer.", "tool_calls": []}
   ```

## Output Format

The response is always valid JSON with two fields:

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's response to the question |
| `tool_calls` | array | Empty array (will be populated in Task 2+) |

## Error Handling

- **Missing API key**: Prints error to stderr, exits with non-zero code
- **Missing question argument**: Prints usage to stderr, exits with non-zero code
- **Network errors**: Prints error to stderr, exits with non-zero code
- **Timeout (>60s)**: Prints error to stderr, exits with non-zero code
- **Invalid API response**: Prints error to stderr, exits with non-zero code

All debug and error output goes to **stderr**. Only the JSON result goes to **stdout**.

## How to Run

### Prerequisites

1. Set up Qwen Code API on your VM (see `wiki/qwen.md`)
2. Create `.env.agent.secret` with your credentials:
   ```bash
   cp .env.agent.example .env.agent.secret
   # Edit with your API key and endpoint
   ```

### Usage

```bash
uv run agent.py "Your question here"
```

### Example

```bash
$ uv run agent.py "What is the capital of France?"
{"answer": "The capital of France is Paris.", "tool_calls": []}
```

## Dependencies

- `httpx` — HTTP client for API calls
- `python-dotenv` — Environment variable loading from `.env` file

## File Structure

```
/root/se-toolkit-lab-6/
├── agent.py              # Main agent CLI
├── .env.agent.secret     # LLM configuration (gitignored)
├── AGENT.md              # This documentation
└── plans/
    └── task-1.md         # Implementation plan
```
