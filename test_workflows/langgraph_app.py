"""LangGraph demo workflow.

Exercises every span kind as a simple linear pipeline so each step is easy to
follow:

  retrieve  -> retrieve_context        (RETRIEVER)
  calculate -> calculator              (TOOL)
  policy    -> company_policy via MCP  (MCP)
  draft     -> shared LLM service      (LLM #2, separate process)
  answer    -> direct Azure OpenAI     (LLM #1, the "agent" node)

Prereqs: start the LLM service first (see README), then:
  python langgraph_app.py
"""

from __future__ import annotations

import re
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

import building_blocks as bb

load_dotenv()


class State(TypedDict, total=False):
    question: str
    context: str
    calculation: str
    policy: str
    draft: str
    answer: str


def retrieve_node(state: State) -> State:
    return {"context": bb.retrieve_context(state["question"])}


def calculate_node(state: State) -> State:
    match = re.search(r"[\d.]+\s*[-+*/]\s*[\d.]+", state["question"])
    expr = match.group(0) if match else "1+1"
    return {"calculation": bb.calculator(expr)}


def policy_node(state: State) -> State:
    topic = next(
        (w for w in ("refund", "warranty", "shipping") if w in state["question"].lower()),
        "refund",
    )
    return {"policy": bb.call_mcp_tool("company_policy", topic=topic)}


def draft_node(state: State) -> State:
    prompt = (
        f"Question: {state['question']}\n"
        f"Context:\n{state.get('context', '')}\n"
        f"Policy: {state.get('policy', '')}\n"
        "Draft a one-paragraph helpful answer."
    )
    return {"draft": bb.llm_service_chat(prompt)}


def answer_node(state: State) -> State:
    prompt = (
        "Refine this draft into a final, concise customer answer.\n"
        f"Draft: {state.get('draft', '')}"
    )
    return {"answer": bb.direct_azure_chat(prompt)}


def build_graph():
    g = StateGraph(State)
    g.add_node("retrieve", retrieve_node)
    g.add_node("calculate", calculate_node)
    g.add_node("policy", policy_node)
    g.add_node("draft", draft_node)
    g.add_node("answer", answer_node)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "calculate")
    g.add_edge("calculate", "policy")
    g.add_edge("policy", "draft")
    g.add_edge("draft", "answer")
    g.add_edge("answer", END)
    return g.compile()


def main() -> None:
    question = input("Ask the LangGraph support workflow a question: ").strip()
    if not question:
        question = "What is the warranty policy and how long does shipping take?"
        print(f"(using default) {question}")
    final = build_graph().invoke({"question": question})
    print("\n=== LangGraph answer ===")
    print(final.get("answer", "(no answer)"))


if __name__ == "__main__":
    main()
