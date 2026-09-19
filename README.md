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
                         │
                         │  1. ask mcp: which tools exist?      ◀── every request
                         │  2. send prompt + tool list to llm
                         │  3. llm: "call get_crypto_price(bitcoin, inr)"
                         │  4. agent runs it via mcp  ──▶  CoinGecko
                         │  5. build a NEW prompt: query + result
                         │  6. send it to the llm again
                         └──────────────▶  answer  ──▶  ui
```

The model never touches the internet itself. It only ever says *which* tool it
wants; the agent is what actually calls it. That separation is the whole idea
behind MCP.

### Step by step

Follow one question through the system. Line numbers are in
`src/agent/chat_agent.py`.

**Step 1 — the agent asks the MCP server what tools exist.** ([line 13](src/agent/chat_agent.py#L13))

Before the model is involved at all, `list_mcp_tools()` fetches the tool list
and reshapes it into the JSON schema the model expects:

```
tools from MCP: ['get_crypto_price']
```

This happens on *every* request. It is why the MCP server must be running even
for a question that ends up needing no tool.

**Step 2 — the agent sends the prompt and the tool list to the LLM.** ([lines 27–29](src/agent/chat_agent.py#L27-L29))

`get_prompt(query)` builds a prompt holding the question and the placeholder
`Tool Result: No tool result available`. The tool list travels separately,
attached with `bind_tools`.

**Step 3 — the LLM replies in one of two ways.** ([line 31](src/agent/chat_agent.py#L31))

It either asks for a tool, or answers outright:

| Question | `tool_calls` | `content` |
| --- | --- | --- |
| *price of bitcoin in inr?* | `[('get_crypto_price', {'coin': 'bitcoin', 'currency': 'inr'})]` | `''` |
| *Who wrote Hamlet?* | `[]` | `'Hamlet was written by William Shakespeare.'` |

Notice the empty `content` in the first row. When the model wants a tool it
returns **no prose at all** — just the request. That emptiness is exactly what
`needs_tool_execution()` tests for.

**Step 4 — no tool call? Then the answer is already finished.** ([line 46](src/agent/chat_agent.py#L46))

The agent takes `content` and returns it. The MCP server is never called a
second time, and only one LLM round trip happened.

**Step 5 — a tool call? The agent calls the MCP server.** ([lines 33–38](src/agent/chat_agent.py#L33-L38))

It passes the name and arguments the model chose. Note `tool_calls[0]`: if the
model asks for several tools at once, only the first one runs.

**Step 6 — the MCP server runs the function and returns the result.** (`src/mcp/server.py`)

The server — not the model, and not the agent — is what actually reaches
CoinGecko. What comes back is a structured `CallToolResult`:

```
meta=None content=[TextContent(type='text', text='7797722', ...)]
structuredContent={'result': 7797722.0} isError=False
```

If the tool raises, this returns with `isError=True` instead of crashing. That
is why a nonsense coin produces a polite explanation rather than a stack trace.

**Step 7 — the agent builds a brand-new prompt containing the result.** ([line 40](src/agent/chat_agent.py#L40))

`get_prompt(query, tool_result)` produces a *fresh* prompt holding the original
question **and** the tool result. Nothing is appended to a conversation — there
is no message history here, just a new string. The prompt's instructions then
tell the model it must answer from the tool result.

**Step 8 — the LLM turns the raw result into a sentence.** ([lines 42–44](src/agent/chat_agent.py#L42-L44))

`7797722` becomes *"The current price of Bitcoin in INR is approximately
7,797,722 INR."* That answer goes back to the UI.

### What this deliberately leaves out

Kept simple on purpose — each of these is a good exercise:

- **One tool per question.** Only `tool_calls[0]` runs ([line 33](src/agent/chat_agent.py#L33)).
- **One round trip.** The agent never loops, so a question needing two tools in
  sequence cannot be answered. A real agent repeats steps 3–7 until the model
  stops asking for tools.
- **No memory.** Each request builds its prompt from scratch, so follow-up
  questions like *"and in usd?"* have no idea what came before.
- **Tools are still bound on the second call** ([line 42](src/agent/chat_agent.py#L42)). If
  the model asked for another tool there, `content` would be `''` and the user
  would see a blank answer.

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
