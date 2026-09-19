# mcp-tutor-agent

A local AI tutor: a FastAPI chat agent backed by a local Ollama model that calls
tools over MCP (Model Context Protocol).

## Layout

| File | Purpose |
| --- | --- |
| `main.py` | FastAPI app exposing `POST /chat` |
| `agent.py` | Agent loop: list tools → ask LLM → run tool → ask LLM again |
| `llm_ollama.py` | Ollama chat model wrapper (`qwen2.5:7b-instruct`) |
| `mcp_client.py` | MCP SSE client (lists and calls tools) |
| `mcp_server.py` | MCP server exposing the `get_crypto_price` tool |
| `prompt.py` | Prompt template |

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct
```

## Run

The MCP server must be running before the API, since the agent lists its tools
on every request.

```bash
# terminal 1 — MCP server on http://127.0.0.1:8000/sse
python mcp_server.py

# terminal 2 — API on http://127.0.0.1:9000
uvicorn main:app --reload --port 9000
```

## Try it

```bash
curl -X POST http://127.0.0.1:9000/chat -F "query=What is the price of bitcoin in inr?"
```
