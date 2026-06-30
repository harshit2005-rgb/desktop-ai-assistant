"""Executes registered MCP tools."""

from typing import Any

from mcp_client.registry import MCPRegistry


class MCPExecutor:

    def __init__(self, registry: MCPRegistry):
        self.registry = registry

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:

        tool = self.registry.get(tool_name)

        if tool is None:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }

        return tool.handler(**arguments)