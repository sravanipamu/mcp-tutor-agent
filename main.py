from fastapi import FastAPI, HTTPException, Form
from agent import ChatAgent

app = FastAPI()

chat_agent = ChatAgent()

@app.post("/chat")
async def chat(
    query: str = Form(...)
):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = await chat_agent.run(query)

    return {
        "answer": result
    }