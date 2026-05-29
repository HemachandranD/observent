"""Shared LLM service - a separate FastAPI process that wraps Azure OpenAI.

Both the CrewAI app and the LangGraph app call this over HTTP, so it shows up
as a distinct cross-service LLM span. Internally it uses the raw openai
AzureOpenAI client, configured purely from environment variables.

Run:  uvicorn llm_service:app --port 8001
  or: python llm_service.py
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from openai import AzureOpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="observent demo LLM service")


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )


class ChatRequest(BaseModel):
    prompt: str
    system: str = "You are a helpful assistant."


class ChatResponse(BaseModel):
    content: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    resp = _client().chat.completions.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        messages=[
            {"role": "system", "content": req.system},
            {"role": "user", "content": req.prompt},
        ],
    )
    return ChatResponse(content=resp.choices[0].message.content or "")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("LLM_SERVICE_PORT", "8001")))
