"""Shared building blocks used by both the CrewAI and LangGraph demo apps.

Each function maps to exactly one observability span kind so observent has
something concrete to instrument:

  retrieve_context  -> RETRIEVER  (in-memory keyword search)
  calculator        -> TOOL       (plain Python function)
  call_mcp_tool     -> MCP        (tool call over the MCP protocol)
  llm_service_chat  -> LLM        (remote shared service, separate process)
  direct_azure_chat -> LLM        (direct Azure OpenAI call via the openai SDK)

All Azure config comes from environment variables (see .env.example).
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

import httpx

# --- Retriever ----------------------------------------------------------------

_DOCS = {
    "refund": "Refunds are processed within 5-7 business days to the original payment method.",
    "shipping": "Standard shipping takes 3-5 business days; express takes 1-2 days.",
    "warranty": "All products carry a 1-year limited warranty covering manufacturing defects.",
    "returns": "Items can be returned within 30 days of delivery in original condition.",
}


def retrieve_context(query: str, k: int = 2) -> str:
    """RETRIEVER: naive keyword retriever over a tiny in-memory corpus."""
    words = set(re.findall(r"\w+", query.lower()))

    def score(key: str, text: str) -> int:
        hay = set(re.findall(r"\w+", f"{key} {text}".lower()))
        return len(words & hay)

    ranked = sorted(_DOCS.items(), key=lambda kv: score(kv[0], kv[1]), reverse=True)
    return "\n".join(f"- {text}" for _, text in ranked[:k])


# --- Tool ---------------------------------------------------------------------


def calculator(expression: str) -> str:
    """TOOL: evaluate a basic arithmetic expression safely."""
    if not re.fullmatch(r"[\d\s+\-*/().]+", expression or ""):
        return "Error: only numbers and + - * / ( ) are allowed."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307 - sanitized above
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"


# --- MCP ----------------------------------------------------------------------

_MCP_SERVER = str(Path(__file__).with_name("mcp_server.py"))


async def _call_mcp_async(tool: str, arguments: dict) -> str:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=[_MCP_SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
            return "".join(getattr(c, "text", "") for c in result.content)


def call_mcp_tool(tool: str, **arguments: str) -> str:
    """MCP: call a tool exposed by the local MCP stdio server (mcp_server.py)."""
    return asyncio.run(_call_mcp_async(tool, arguments))


# --- LLM (remote shared service) ----------------------------------------------

LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8001")


def llm_service_chat(prompt: str, system: str = "You are a helpful assistant.") -> str:
    """LLM (remote): call the shared FastAPI LLM service running as a separate process."""
    resp = httpx.post(
        f"{LLM_SERVICE_URL}/chat",
        json={"system": system, "prompt": prompt},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["content"]


# --- LLM (direct Azure OpenAI) ------------------------------------------------


def direct_azure_chat(prompt: str, system: str = "You are a helpful assistant.") -> str:
    """LLM (direct): call Azure OpenAI directly via the openai SDK + env vars."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )
    resp = client.chat.completions.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content or ""
