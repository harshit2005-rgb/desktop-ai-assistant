"""Registry for all available MCP tools."""

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class MCPTool:
    name: str
    description: str
    server: str
    handler: Callable[..., dict[str, Any]]


class MCPRegistry:
    """Stores all available MCP tools."""

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}

    def register(
        self,
        name: str,
        description: str,
        server: str,
        handler: Callable[..., dict[str, Any]],
    ) -> None:

        self._tools[name] = MCPTool(
            name=name,
            description=description,
            server=server,
            handler=handler,
        )

    def get(self, name: str) -> MCPTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[MCPTool]:
        return list(self._tools.values())