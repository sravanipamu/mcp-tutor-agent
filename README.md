# mcp-tutor-agent

A small, complete example of an **AI agent that uses tools** — with a local
model, no API keys, and no cloud account.

You ask a question in the browser. The agent decides whether it needs a tool,
calls it over **MCP (Model Context Protocol)**, and answers using what came
back.

---

## The goal

Show the whole loop end to end, in code you can read in one sitting.

Most tool-calling examples hide the interesting part inside a framework. Here
every step is visible and in its own folder: the browser page, the agent loop,
the model wrapper, and both halves of MCP — the client *and* the server.

By the end you should be able to answer: how does a language model, which only
produces text, end up fetching a live price?

## Why this project

**Tool calling is the thing that makes an LLM useful.** A model alone cannot
tell you today's Bitcoin price — its knowledge is frozen at training time. It
needs to call something. MCP is the emerging standard for how models talk to
those tools, and the fastest way to understand a protocol is to run both ends
of it.

**It runs entirely on your machine.** The model is served by Ollama locally, so
there is no API key, no billing, and no request leaving your laptop except the
public price lookup itself. You can read, break and rebuild any part without
cost.

**It is deliberately small.** Six Python files, under 200 lines in total. Every
file is one idea. Nothing is abstracted "for later."

## What you get

A single input box at <http://127.0.0.1:9000>:

```
┌──────────────────────────────────────────────────┐
│  mcp-tutor-agent                                 │
│  Ask a question. The agent will call an MCP      │
│  tool when it needs one.                         │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ What is the price of bitcoin in inr?       │  │
│  └────────────────────────────────────────────┘  │
│  Press Enter to send                             │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ The current price of Bitcoin in INR is     │  │
│  │ approximately 7,812,216 INR. Please note   │  │
│  │ that cryptocurrency prices can fluctuate   │  │
│  │ rapidly.                                   │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

Three questions worth trying, because each takes a different path:

| Ask | What happens | Actual answer |
| --- | --- | --- |
| `What is the price of bitcoin in inr?` | model calls the MCP tool, then answers from live data | *"The current price of Bitcoin in INR is approximately 7,812,216 INR."* |
| `Who wrote Hamlet?` | no tool needed — the model answers directly | *"Hamlet was written by William Shakespeare."* |
| `What is the price of notacoin?` | the tool fails; the error goes back to the model, which explains it | *"I couldn't find the price of 'notacoin' using the available tools. Could you please check the spelling?"* |

That third one is the most interesting: a failing tool is not a crash. The
error becomes context, and the model turns it into a sentence.

---

## How to run it on your machine

### 1. Prerequisites

- **Python 3.10 or newer** — `python3 --version`
- **[Ollama](https://ollama.com/download)** — runs the model locally
- About **5 GB** of free disk for the model

### 2. Get the code and install

```bash
git clone <your-repo-url>
cd mcp-tutor-agent

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Pull the model

```bash
ollama pull qwen2.5:7b-instruct
```

This downloads ~4.7 GB, once. The model must support tool calling — if you swap
it in `src/llm/ollama.py`, pick another tool-capable model.

Check Ollama is serving: `curl http://localhost:11434` → `Ollama is running`

### 4. Start the two processes

They run in **two terminals**, both from the project root. The MCP server must
be up first, because the agent asks it for the tool list on every request.

```bash
# terminal 1 — MCP server, http://127.0.0.1:8000/sse
source venv/bin/activate
python -m src.mcp.server
```

```bash
# terminal 2 — web UI + API, http://127.0.0.1:9000
source venv/bin/activate
uvicorn main:app --reload --port 9000
```

### 5. Use it

Open <http://127.0.0.1:9000>, type a question, press Enter.

First answer takes a few seconds while the model loads into memory; after that
it is quick.

Prefer the terminal?

```bash
curl -X POST http://127.0.0.1:9000/chat -F "query=What is the price of bitcoin in inr?"
```
```json
{"answer":"The current price of Bitcoin in INR is approximately 7,812,216 INR."}
```

---

## How it works

```
  ui  ──POST /chat──▶  agent
                         │  1. ask mcp for the list of tools
                         │  2. send question + tools to the llm
                         │  3. llm replies "call get_crypto_price(bitcoin, inr)"
                         │  4. agent runs it via mcp  ──▶  CoinGecko
                         │  5. send question + result back to the llm
                         └──────────────────────────▶  answer  ──▶  ui
```

The model never touches the internet itself. It only ever says *which* tool it
wants; the agent is what actually calls it. That separation is the whole idea
behind MCP.

## Structure

One folder per layer — read them in any order:

```
mcp-tutor-agent/
├── main.py              FastAPI entrypoint: serves the UI, exposes POST /chat
├── requirements.txt
└── src/
    ├── ui/
    │   └── index.html   one input box — plain HTML/CSS/JS, no build step
    ├── agent/
    │   ├── chat_agent.py  the loop: list tools → ask LLM → run tool → ask again
    │   └── prompt.py      the instructions the LLM receives
    ├── llm/
    │   └── ollama.py      local model wrapper (qwen2.5:7b-instruct)
    └── mcp/
        ├── client.py      connects to the MCP server over SSE
        └── server.py      the MCP server, exposing get_crypto_price
```

Client and server both live here on purpose, so you can read both sides of the
protocol without switching repos.

## Add your own tool

Add a function to `src/mcp/server.py`:

```python
@mcp.tool(name="get_weather", description="Get the current weather for a city.")
def get_weather(city: str) -> str:
    ...
```

Restart the MCP server. That is the only change — the agent discovers the tool
automatically and no other file needs editing.

The `description` matters more than you would expect: it is the only thing the
model reads when deciding whether to call your tool. Be specific.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `Agent failed: ... Is the MCP server running?` | Terminal 1 is not running. Start `python -m src.mcp.server`. |
| `[Errno 48] address already in use` | Something already holds port 8000. Find it with `lsof -i :8000` and stop it. |
| `ModuleNotFoundError: No module named 'src'` | You ran from the wrong directory. Both commands must run from the project root. |
| Connection refused on port 11434 | Ollama is not running. Start it, then retry. |
| First request hangs for a long time | The model is loading into RAM. Normal once, on the first question. |
| `__pycache__` folders keep appearing | Python's bytecode cache. Harmless, and already git-ignored. |
