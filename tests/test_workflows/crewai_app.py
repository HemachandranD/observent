"""CrewAI demo workflow.

Exercises every span kind in one simple, linear agent run:

  agent      -> CrewAI Agent
  retriever  -> retrieve_context tool
  tool       -> calculator tool
  MCP        -> company_policy tool (backed by the MCP server)
  LLM #1     -> direct Azure OpenAI, via the agent's native CrewAI LLM
  LLM #2     -> the shared LLM service (separate process), via a tool

Prereqs: start the LLM service first (see README), then:
  python crewai_app.py
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# CrewAI talks to Azure through litellm, which reads AZURE_API_* env names.
# Map our single set of AZURE_OPENAI_* vars onto them so there is one source.
os.environ.setdefault("AZURE_API_KEY", os.environ.get("AZURE_OPENAI_API_KEY", ""))
os.environ.setdefault("AZURE_API_BASE", os.environ.get("AZURE_OPENAI_ENDPOINT", ""))
os.environ.setdefault(
    "AZURE_API_VERSION", os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
)

from crewai import LLM, Agent, Crew, Process, Task  # noqa: E402
from crewai.tools import tool  # noqa: E402

import building_blocks as bb  # noqa: E402


@tool("retrieve_context")
def retrieve_tool(query: str) -> str:
    """Retrieve relevant support documents for the query."""
    return bb.retrieve_context(query)


@tool("calculator")
def calculator_tool(expression: str) -> str:
    """Evaluate a basic arithmetic expression like '12 * (3 + 4)'."""
    return bb.calculator(expression)


@tool("company_policy")
def policy_tool(topic: str) -> str:
    """Look up official company policy for a topic via the MCP server."""
    return bb.call_mcp_tool("company_policy", topic=topic)


@tool("ask_llm_service")
def llm_service_tool(prompt: str) -> str:
    """Ask the shared LLM service (a separate process) to draft text."""
    return bb.llm_service_chat(prompt)


def build_crew(question: str) -> Crew:
    # is_litellm=True forces CrewAI's litellm path (Azure OpenAI) instead of the
    # native "azure" provider, which is Azure AI Inference and needs an extra package.
    llm = LLM(model=f"azure/{os.environ['AZURE_OPENAI_DEPLOYMENT']}", is_litellm=True)

    agent = Agent(
        role="Customer Support Specialist",
        goal="Answer the customer's question accurately using your tools.",
        backstory="A meticulous support agent who always checks policy and context first.",
        tools=[retrieve_tool, calculator_tool, policy_tool, llm_service_tool],
        llm=llm,
        verbose=True,
    )

    task = Task(
        description=(
            f"The customer asks: '{question}'.\n"
            "1. Use retrieve_context to gather relevant support context.\n"
            "2. Use company_policy to look up the official policy.\n"
            "3. If any number-crunching is needed, use the calculator.\n"
            "4. Use ask_llm_service to draft a friendly summary.\n"
            "5. Return a final, concise answer."
        ),
        expected_output="A concise, friendly answer grounded in policy and context.",
        agent=agent,
    )

    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)


def main() -> None:
    question = input("Ask the CrewAI support agent a question: ").strip()
    if not question:
        question = "How long do refunds take and what is the official refund policy?"
        print(f"(using default) {question}")
    result = build_crew(question).kickoff()
    print("\n=== CrewAI answer ===")
    print(result)


if __name__ == "__main__":
    main()
