# mcp-tutor-agent

A small, readable example of an AI agent that calls tools over
**MCP (Model Context Protocol)** — with a local LLM and no cloud API keys.

Type a question in the browser. The agent asks the model what to do, the model
picks an MCP tool, the agent runs it and feeds the result back for a final
answer.

```
  ui  ──POST /chat──▶  agent  ──▶  llm   (Ollama, decides which tool)
                         │
                         └──────▶  mcp   (runs the tool, returns data)
                         │
                         └──▶ llm again ──▶ answer ──▶ ui
```

## Structure

Each folder is one layer, so you can read them in any order:

```
mcp-tutor-agent/
├── main.py              FastAPI entrypoint: serves the UI and POST /chat
├── requirements.txt
└── src/
    ├── ui/
    │   └── index.html   one input box, plain HTML/CSS/JS, no build step
    ├── agent/
    │   ├── chat_agent.py  the loop: list tools → ask LLM → run tool → ask again
    │   └── prompt.py      the prompt the LLM receives
    ├── llm/
    │   └── ollama.py      local model wrapper (qwen2.5:7b-instruct)
    └── mcp/
        ├── client.py      connects to the MCP server over SSE
        └── server.py      the MCP server, exposing get_crypto_price
```

The MCP **client** and **server** are both here on purpose: you can read both
halves of the protocol in one repo.

## Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# install and pull the model
ollama pull qwen2.5:7b-instruct
```

## Run

Two processes. The MCP server must be up first, since the agent lists its tools
on every request.

```bash
# terminal 1 — MCP server on http://127.0.0.1:8000/sse
python -m src.mcp.server

# terminal 2 — web UI + API on http://127.0.0.1:9000
uvicorn main:app --reload --port 9000
```

Run both from the project root, so `src` is importable.

## Try it

Open <http://127.0.0.1:9000>, type a question, press Enter.

| Ask this | What it shows |
| --- | --- |
| `What is the price of bitcoin in inr?` | the LLM calls the MCP tool |
| `Who wrote Hamlet?` | no tool needed — the LLM answers directly |
| `What is the price of notacoin?` | the tool fails, and you get a readable error |

Or call the API directly:

```bash
curl -X POST http://127.0.0.1:9000/chat -F "query=What is the price of bitcoin in inr?"
```

## Adding your own tool

Add a function to `src/mcp/server.py`:

```python
@mcp.tool(name="my_tool", description="What it does — the LLM reads this.")
def my_tool(arg: str) -> str:
    return "..."
```

Restart the MCP server. The agent discovers it automatically — no other file
needs to change. The `description` is how the model decides when to call it, so
make it specific.
