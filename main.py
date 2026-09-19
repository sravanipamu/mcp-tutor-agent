from pathlib import Path

from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import FileResponse

from src.agent.chat_agent import ChatAgent

app = FastAPI()

chat_agent = ChatAgent()

INDEX_FILE = Path(__file__).parent / "src" / "ui" / "index.html"

@app.get("/")
async def index():
    return FileResponse(INDEX_FILE)

@app.post("/chat")
async def chat(
    query: str = Form(...)
):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = await chat_agent.run(query)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Agent failed: {error}. Is the MCP server running on http://127.0.0.1:8000/sse?"
        )

    return {
        "answer": result
    }
