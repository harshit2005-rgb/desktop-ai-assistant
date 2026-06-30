def format_project(result: dict) -> str:
    """
    Convert scanned project metadata into rich context for the AI.
    """

    mcp_servers = result.get("mcp_servers", [])
    services = result.get("services", [])

    return f"""
PROJECT CONTEXT

Project Name:
{result.get("project_name", "Unknown")}

Project Type:
Desktop AI Assistant

Primary Language:
{result.get("language", "Unknown")}

Framework:
{result.get("framework", "Unknown")}

Package Manager:
{result.get("package_manager", "Unknown")}

AI Provider:
{result.get("ai_provider", "Unknown")}

Entry Point:
{", ".join(result.get("entry_points", []))}

Important Files:
{", ".join(result.get("important_files", []))}

Top Level Directories:
{", ".join(result.get("top_level_dirs", []))}

Detected MCP Servers:
{chr(10).join("- " + server for server in mcp_servers)}

Detected Services:
{chr(10).join("- " + service for service in services)}

ARCHITECTURE NOTES

This project follows a modular Model Context Protocol (MCP) architecture.

Each major capability is implemented as an independent MCP server.

The Agent Service orchestrates these MCP servers to execute user requests.

The application uses PySide6 for the desktop interface.

The AI provider powers reasoning and natural language understanding.

TASK FOR THE AI

Explain:

1. What this project does.
2. Why MCP is used.
3. How requests flow through the system.
4. Responsibilities of the major folders.
5. Responsibilities of the important services.
6. How the architecture could scale in the future.

Do NOT simply repeat the metadata.
Provide an architectural explanation suitable for a software engineering manager.
ARCHITECTURE NOTES

MCP in this project refers to the Model Context Protocol developed by Anthropic.

The Model Context Protocol is used as a standard interface between the AI agent and modular tool servers.

Each capability (Filesystem, Browser, Gmail, Teams, Documents, Applications and Project Analysis) is implemented as an independent MCP server.

The Agent Service discovers and orchestrates these MCP tools to satisfy user requests.
"""
