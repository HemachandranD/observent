"""Minimal MCP stdio server exposing one tool, for the demo workflows.

Both apps spawn this over stdio (see building_blocks.call_mcp_tool) and call
`company_policy`, which gives observent a real MCP span to capture.

Run standalone for inspection:  python mcp_server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("observent-demo-mcp")

_POLICIES = {
    "refund": "Refunds require an order ID and are approved by a human within 24 hours.",
    "warranty": "Warranty claims need proof of purchase dated within the last 12 months.",
    "shipping": "International shipping may add 7-10 business days plus customs fees.",
}


@mcp.tool()
def company_policy(topic: str) -> str:
    """Return the official company policy for a given topic."""
    return _POLICIES.get(topic.lower().strip(), f"No official policy found for '{topic}'.")


if __name__ == "__main__":
    mcp.run()
