"""Agent service that routes natural language requests to desktop MCP tools."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from groq import Groq
from services.intent_router import intent_router
from services.project_scanner import get_project_context
from services.project_formatter import format_project
from mcp_client.registry import MCPRegistry
from mcp_client.executor import MCPExecutor

from config.settings import (
    DEFAULT_MODEL,
    MAX_TOOL_LOOPS,
    MAX_TOOL_CONTENT_FOR_LLM,
    MAX_RECENT_CONTEXT,
    SYSTEM_PROMPT,
)

from mcp_servers.application_server import (
    list_running_applications_impl,
    open_application_impl,
)
from mcp_servers.browser_server import (
    open_browser_impl,
    google_search_impl,
    
)
from mcp_servers.teams_server import (
    open_teams_impl,
    open_teams_web_impl,
    open_teams_calendar_impl,
    open_teams_chat_impl,
)
from mcp_servers.document_server import (
    read_file_impl,
    search_file_content_impl,
    summarize_file_impl,
)
from mcp_servers.filesystem_server import (
    find_file_impl,
    get_file_info_impl,
    list_directory_impl,
    open_file_impl,
)
from mcp_servers.gmail_server import (
    attach_and_send_email_impl,
    draft_email_impl,
    read_email_impl,
    read_recent_emails_impl,
    search_emails_impl,
    send_email_impl,
)
from mcp_servers.project_server import (
    scan_project_impl,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Response returned to the UI after a user request is processed."""

    assistant_message: str
    tool_results: list[dict[str, Any]]
    memory_snapshot: dict[str, Any]


@dataclass
class ConversationMemory:
    """Small in-process context store for follow-up desktop workflows."""

    last_file_opened: str | None = None
    last_file_read: str | None = None
    last_file_summarized: str | None = None
    last_searched_file: str | None = None
    last_search_query: str | None = None
    last_search_results: list[str] | None = None
    last_folder_analyzed: str | None = None
    last_recipient: str | None = None
    last_email_subject: str | None = None
    last_draft: str | None = None
    last_attachment: str | None = None
    last_sent_email: dict[str, Any] | None = None
    recent_contacts: list[dict[str, Any]] | None = None
    pending_email_action: dict[str, Any] | None = None
    recent_emails: list[dict[str, Any]] | None = None
    sent_emails: list[dict[str, Any]] | None = None
    drafts: list[dict[str, Any]] | None = None
    last_action: str | None = None
    current_workflow: str | None = None
    recent_context: list[str] | None = None

    def __post_init__(self) -> None:
        if self.last_search_results is None:
            self.last_search_results = []
        if self.recent_context is None:
            self.recent_context = []
        if self.recent_emails is None:
            self.recent_emails = []
        if self.sent_emails is None:
            self.sent_emails = []
        if self.drafts is None:
            self.drafts = []
        if self.recent_contacts is None:
            self.recent_contacts = []

    def remember(self, item: str) -> None:
        """Append concise conversation context."""
        assert self.recent_context is not None
        self.recent_context.append(item)
        del self.recent_context[:-MAX_RECENT_CONTEXT]

    def snapshot(self) -> dict[str, Any]:
        """Return data safe for UI display and LLM context."""
        return {
            "last_file_opened": self.last_file_opened,
            "last_file_read": self.last_file_read,
            "last_file_summarized": self.last_file_summarized,
            "last_searched_file": self.last_searched_file,
            "last_folder_analyzed": self.last_folder_analyzed,
            "last_recipient": self.last_recipient,
            "last_email_subject": self.last_email_subject,
            "last_draft": self.last_draft,
            "last_attachment": self.last_attachment,
            "last_sent_email": self.last_sent_email,
            "recent_contacts": list(self.recent_contacts or []),
            "pending_email_action": self.pending_email_action,
            "recent_emails": list(self.recent_emails or []),
            "sent_emails": list(self.sent_emails or []),
            "drafts": list(self.drafts or []),
            "last_action": self.last_action,
            "current_workflow": self.current_workflow,
            "recent_context": list(self.recent_context or []),
        }


class AgentService:
    """Groq-backed desktop assistant with MCP tool execution."""

    def __init__(self) -> None:
        load_dotenv()
        self.model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
        self.client: Groq | None = None
        api_key = os.getenv("GROQ_API_KEY")

        if api_key and not api_key.startswith("your_"):
            self.client = Groq(api_key=api_key)
        else:
            logger.warning("GROQ_API_KEY is not set; using local rule-based fallback")

        # Initialize MCP registry and executor before any tool registration
        self.registry = MCPRegistry()
        self.executor = MCPExecutor(self.registry)

        self.tool_functions: dict[str, Callable[..., dict[str, Any]]] = {
            "scan_project": scan_project_impl,
            "find_file": find_file_impl,
            "list_directory": list_directory_impl,
            "open_file": open_file_impl,
            "get_file_info": get_file_info_impl,
            "open_application": open_application_impl,
            "open_browser": open_browser_impl,
            "google_search": google_search_impl,
            "list_running_applications": list_running_applications_impl,
            "read_file": read_file_impl,
            "summarize_file": summarize_file_impl,
            "search_file_content": search_file_content_impl,
            "send_email": send_email_impl,
            "draft_email": draft_email_impl,
            "read_recent_emails": read_recent_emails_impl,
            "search_emails": search_emails_impl,
            "read_email": read_email_impl,
            "attach_and_send_email": attach_and_send_email_impl,
            "open_teams": open_teams_impl,
            "open_teams_web": open_teams_web_impl,
            "open_teams_calendar": open_teams_calendar_impl,
            "open_teams_chat": open_teams_chat_impl,
        }

        # Register all tools into the MCP registry
        for name, handler in self.tool_functions.items():
            self.registry.register(
                name=name,
                description=name.replace("_", " "),
                server="local",
                handler=handler,
            )

        self.tools = self._build_tool_schemas()
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.memory = ConversationMemory()

    def handle_message(self, user_message: str) -> AgentResult:
        """Process a user request and return assistant text plus tool outputs."""
        if not user_message.strip():
            return AgentResult("Please enter a command.", [], self.memory.snapshot())

        self.memory.current_workflow = self._classify_workflow(user_message)
        self.memory.remember(f"User: {user_message}")
        confirmation_result = self._maybe_execute_pending_email(user_message)
        if confirmation_result is not None:
            return confirmation_result

        if self.client is None:
            return self._handle_without_llm(user_message)
        # Try routing simple commands before calling the LLM.
        route = intent_router.route(user_message, memory=self.memory)

        if route is not None:
            tool_name = route["tool"]
            arguments = route["arguments"]

            # Project Explanation Workflow
            if tool_name == "project_explanation":
                return self._handle_project_explanation()

            # Handle error responses from intent router (e.g., invalid search result index)
            if tool_name == "error":
                error_message = arguments.get("message", "An error occurred.")
                return AgentResult(error_message, [], self.memory.snapshot())

            result = self._execute_tool(tool_name, arguments)

            if tool_name == "find_file" and result.get("success"):
                self.memory.last_search_query = arguments["filename"]
                self.memory.last_search_results = result.get("matches", [])

            self._update_memory_from_tool(tool_name, arguments, result)

            assistant_message = self._summarize_tool_result(tool_name, result)

            # Custom formatting for file search results
            if tool_name == "find_file" and result.get("success"):
                matches = result.get("matches", [])
                preview = "\n".join(
                    f"{i + 1}. {path}"
                    for i, path in enumerate(matches[:3])
                )
                assistant_message = (
                    f"Found {len(matches)} matching file(s) for "
                    f"'{arguments['filename']}'.\n\n"
                    f"Top Matches:\n\n"
                    f"{preview}\n\n"
                    f"Showing {min(3, len(matches))} of {len(matches)} results.\n\n"
                    f"You can now say:\n"
                    f"• open 1\n"
                    f"• info 2\n"
                    f"• summarize 3"
                )

            return AgentResult(
                assistant_message,
                [
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                        "result": result,
                    }
                ],
                self.memory.snapshot(),
            )


        self._add_memory_context_message()
        self.messages.append({"role": "user", "content": user_message})
        tool_results: list[dict[str, Any]] = []

        try:
            for _ in range(MAX_TOOL_LOOPS):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools,
                    tool_choice="auto",
                    temperature=0.1,
                )
                assistant_message = response.choices[0].message
                self.messages.append(assistant_message.model_dump(exclude_none=True))

                tool_calls = assistant_message.tool_calls or []
                if not tool_calls:
                    content = assistant_message.content or ""
                    self.memory.remember(f"Assistant: {content[:500]}")
                    return AgentResult(content, tool_results, self.memory.snapshot())

                for tool_call in tool_calls:
                    name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments or "{}")
                    arguments = self._resolve_contextual_arguments(name, arguments)
                    result = self._execute_tool(name, arguments)
                    tool_results.append({"tool": name, "arguments": arguments, "result": result})
                    self._update_memory_from_tool(name, arguments, result)
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": self._json_for_llm(result),
                        }
                    )

            return AgentResult(
                "I reached the tool-call limit while handling that request. "
                "Please try a more specific command.",
                tool_results,
                self.memory.snapshot(),
            )
        except Exception as exc:  # noqa: BLE001 - API and tool errors surface broadly.
            logger.exception("Agent request failed")
            return AgentResult(f"Error while processing request: {exc}", tool_results, self.memory.snapshot())

    def _execute_tool(self, name: str, arguments: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]:
        """Execute a registered local MCP tool implementation."""
        if name in {"send_email", "attach_and_send_email"} and not confirmed:
            self.memory.pending_email_action = {"tool": name, "arguments": dict(arguments)}
            self._remember_email_arguments(arguments)
            return {
                "success": False,
                "requires_confirmation": True,
                "status": "pending_confirmation",
                "message": "Email send prepared. Ask the user for explicit confirmation before sending.",
                "preview": self._format_email_preview(name, arguments),
            }

        func = self.tool_functions.get(name)
        if func is None:
            logger.error("Unknown tool requested: %s", name)
            return {"success": False, "error": f"Unknown tool: {name}"}

        try:
            logger.info("Executing tool %s with arguments %s", name, arguments)

            if arguments is None:
                arguments = {}

            return func(**arguments)
        except TypeError as exc:
            logger.exception("Invalid arguments for tool %s", name)
            return {"success": False, "error": f"Invalid arguments for {name}: {exc}"}
        except Exception as exc:  # noqa: BLE001 - keep UI responsive on tool failure.
            logger.exception("Tool %s failed", name)
            return {"success": False, "error": str(exc)}

    def _maybe_execute_pending_email(self, user_message: str) -> AgentResult | None:
        """Send a pending email only after explicit confirmation."""
        pending = self.memory.pending_email_action
        if not pending:
            return None

        lower = user_message.strip().lower()
        if any(phrase in lower for phrase in ("cancel", "do not send", "don't send", "discard")):
            self.memory.pending_email_action = None
            self.memory.remember("Pending email send cancelled")
            return AgentResult("Cancelled the pending email. Nothing was sent.", [], self.memory.snapshot())

        confirmed = any(
            phrase in lower
            for phrase in (
                "yes send",
                "send it",
                "send it now",
                "confirm",
                "confirmed",
                "go ahead",
                "looks good",
                "send now",
            )
        )
        if not confirmed:
            return None

        name = pending.get("tool")
        arguments = pending.get("arguments", {})
        result = self._execute_tool(name, arguments, confirmed=True)
        self.memory.pending_email_action = None
        self._update_memory_from_tool(name, arguments, result)
        tool_results = [{"tool": name, "arguments": arguments, "result": result}]

        if result.get("success"):
            return AgentResult(
                f"Email sent to {result.get('recipient')} with message id {result.get('message_id')}.",
                tool_results,
                self.memory.snapshot(),
            )
        return AgentResult(f"Unable to send the pending email: {result.get('error')}", tool_results, self.memory.snapshot())

    def _remember_email_arguments(self, arguments: dict[str, Any]) -> None:
        """Store reusable email fields in memory."""
        if arguments.get("recipient"):
            recipient = arguments["recipient"]
            self.memory.last_recipient = recipient
            # track recent contacts (simple dedupe by address/name)
            contact = {"recipient": recipient}
            # remove any existing identical entries
            self.memory.recent_contacts = [c for c in (self.memory.recent_contacts or []) if c.get("recipient") != recipient]
            self.memory.recent_contacts.insert(0, contact)
            del self.memory.recent_contacts[20:]
        if arguments.get("subject"):
            self.memory.last_email_subject = arguments["subject"]
        if arguments.get("file_path"):
            self.memory.last_attachment = arguments["file_path"]

    @staticmethod
    def _format_email_preview(tool_name: str, arguments: dict[str, Any]) -> str:
        """Create a confirmation preview for pending sends."""
        attachment = arguments.get("file_path")
        lines = [
            "Recipient:",
            str(arguments.get("recipient", "")),
            "",
            "Subject:",
            str(arguments.get("subject", "")),
            "",
            "Body:",
            str(arguments.get("body", "")),
        ]
        if tool_name == "attach_and_send_email" and attachment:
            lines.extend(["", "Attachment:", str(attachment)])
        lines.extend(["", "Do you want me to send this email?"])
        return "\n".join(lines)

    def _handle_without_llm(self, user_message: str) -> AgentResult:
        """Best-effort local fallback for common desktop commands."""
        text = user_message.strip()
        lower = text.lower()
        tool_results: list[dict[str, Any]] = []

        if any(phrase in lower for phrase in ("latest emails", "recent emails", "show my emails", "show emails")):
            count_match = re.search(r"\b(\d{1,2})\b", lower)
            count = int(count_match.group(1)) if count_match else 10
            result = self._execute_tool("read_recent_emails", {"count": count})
            tool_results.append({"tool": "read_recent_emails", "arguments": {"count": count}, "result": result})
            self._update_memory_from_tool("read_recent_emails", {"count": count}, result)
            return AgentResult(self._format_email_list(result), tool_results, self.memory.snapshot())

        if lower.startswith("search emails") or lower.startswith("search gmail"):
            query = text.split(" ", 2)[2].strip() if len(text.split(" ", 2)) > 2 else ""
            result = self._execute_tool("search_emails", {"query": query})
            tool_results.append({"tool": "search_emails", "arguments": {"query": query}, "result": result})
            self._update_memory_from_tool("search_emails", {"query": query}, result)
            return AgentResult(self._format_email_list(result), tool_results, self.memory.snapshot())

        doc_path = self._extract_document_path(text)
        if doc_path and any(word in lower for word in ("summarize", "summary", "explain", "read")):
            mode = self._extract_summary_mode(lower)
            result = self._execute_tool("summarize_file", {"path": doc_path, "mode": mode})
            tool_results.append({"tool": "summarize_file", "arguments": {"path": doc_path, "mode": mode}, "result": result})
            self._update_memory_from_tool("summarize_file", {"path": doc_path, "mode": mode}, result)
            return AgentResult(self._format_local_summary(result), tool_results, self.memory.snapshot())

        if "search" in lower or lower.startswith("find mentions") or lower.startswith("find all references"):
            target = doc_path or self.memory.last_file_read or self.memory.last_file_summarized
            query = self._extract_search_query(text)
            if target and query:
                result = self._execute_tool("search_file_content", {"path": target, "query": query})
                tool_results.append({"tool": "search_file_content", "arguments": {"path": target, "query": query}, "result": result})
                self._update_memory_from_tool("search_file_content", {"path": target, "query": query}, result)
                return AgentResult(self._format_local_search(result), tool_results, self.memory.snapshot())

        if "email" in lower and any(word in lower for word in ("draft", "write", "compose")):
            target = doc_path or self.memory.last_file_summarized or self.memory.last_file_read
            if target:
                result = self._execute_tool("summarize_file", {"path": target, "mode": "email brief"})
                tool_results.append(
                    {"tool": "summarize_file", "arguments": {"path": target, "mode": "email brief"}, "result": result}
                )
                self._update_memory_from_tool("summarize_file", {"path": target, "mode": "email brief"}, result)
                return AgentResult(self._draft_local_email(result, text), tool_results, self.memory.snapshot())

        if lower.startswith("open ") and not any(word in lower for word in ("file", "folder", "resume")):
            app_name = text[5:].strip()
            result = self._execute_tool("open_application", {"app_name": app_name})
            tool_results.append({"tool": "open_application", "arguments": {"app_name": app_name}, "result": result})
            self._update_memory_from_tool("open_application", {"app_name": app_name}, result)
            return AgentResult(self._summarize_tool_result("open_application", result), tool_results, self.memory.snapshot())

        if lower.startswith("find "):
            filename = text[5:].strip()
            result = self._execute_tool("find_file", {"filename": filename})
            tool_results.append({"tool": "find_file", "arguments": {"filename": filename}, "result": result})
            self._update_memory_from_tool("find_file", {"filename": filename}, result)
            return AgentResult(self._summarize_tool_result("find_file", result), tool_results, self.memory.snapshot())

        if "latest resume" in lower:
            result = self._execute_tool("find_file", {"filename": "resume"})
            tool_results.append({"tool": "find_file", "arguments": {"filename": "resume"}, "result": result})
            latest = self._latest_path(result.get("matches", []))
            if latest and lower.startswith("open"):
                open_result = self._execute_tool("open_file", {"path": latest})
                tool_results.append({"tool": "open_file", "arguments": {"path": latest}, "result": open_result})
                self._update_memory_from_tool("open_file", {"path": latest}, open_result)
                return AgentResult(self._summarize_tool_result("open_file", open_result), tool_results, self.memory.snapshot())
            return AgentResult(
                f"Latest resume match: {latest}" if latest else "No resume files found.",
                tool_results,
                self.memory.snapshot(),
            )

        if "running" in lower and "app" in lower:
            result = self._execute_tool("list_running_applications", {})
            tool_results.append({"tool": "list_running_applications", "arguments": {}, "result": result})
            self._update_memory_from_tool("list_running_applications", {}, result)
            return AgentResult(self._summarize_tool_result("list_running_applications", result), tool_results, self.memory.snapshot())

        return AgentResult(
            "GROQ_API_KEY is not configured. I can still handle simple commands like "
            "'Open VS Code', 'Find resume.pdf', 'Summarize /path/to/report.pdf', "
            "and 'Search /path/to/notes.md for Groq'.",
            [],
            self.memory.snapshot(),
        )

    def _add_memory_context_message(self) -> None:
        """Inject current memory as non-user context for this turn."""
        context = {
            "role": "system",
            "content": "Current assistant memory/context:\n" + json.dumps(self.memory.snapshot(), indent=2),
        }
        self.messages.append(context)
        if len(self.messages) > 40:
            self.messages = [self.messages[0], *self.messages[-39:]]

    def _resolve_contextual_arguments(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Fill obvious pronoun-based path arguments from memory."""
        if name not in {
            "read_file",
            "summarize_file",
            "search_file_content",
            "open_file",
            "get_file_info",
            "attach_and_send_email",
        }:
            return arguments

        path_key = "file_path" if name == "attach_and_send_email" else "path"
        path = str(arguments.get(path_key, "")).strip().lower()
        if path and path not in {"it", "this", "that", "this file", "that file", "the file", "the document"}:
            return arguments

        remembered = (
            self.memory.last_file_summarized
            or self.memory.last_file_read
            or self.memory.last_file_opened
            or self.memory.last_searched_file
        )
        if remembered:
            arguments = dict(arguments)
            arguments[path_key] = remembered
        return arguments

    def _update_memory_from_tool(self, name: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
        """Update context memory after successful tool execution."""
        self.memory.last_action = name

        if name == "list_directory" and result.get("success"):
            self.memory.last_folder_analyzed = result.get("path") or arguments.get("path")
        elif name == "open_file" and result.get("success"):
            self.memory.last_file_opened = result.get("path") or arguments.get("path")
        elif name == "read_file" and result.get("success"):
            metadata = result.get("metadata", {})
            self.memory.last_file_read = metadata.get("path") or arguments.get("path")
        elif name == "summarize_file" and result.get("success"):
            self.memory.last_file_summarized = result.get("path") or arguments.get("path")
            self.memory.last_file_read = self.memory.last_file_summarized
        elif name == "search_file_content" and result.get("success"):
            self.memory.last_searched_file = result.get("path") or arguments.get("path")
            self.memory.last_file_read = self.memory.last_searched_file
        elif name == "draft_email" and result.get("success"):
            self._remember_email_arguments(arguments)
            self.memory.last_draft = result.get("draft_id")
            assert self.memory.drafts is not None
            self.memory.drafts.append(
                {
                    "draft_id": result.get("draft_id"),
                    "recipient": result.get("recipient") or arguments.get("recipient"),
                    "subject": result.get("subject") or arguments.get("subject"),
                }
            )
            del self.memory.drafts[:-10]
        elif name in {"send_email", "attach_and_send_email"} and result.get("success"):
            self._remember_email_arguments(arguments)
            assert self.memory.sent_emails is not None
            sent_item = {
                "message_id": result.get("message_id"),
                "recipient": result.get("recipient") or arguments.get("recipient"),
                "subject": result.get("subject") or arguments.get("subject"),
                "attachment": result.get("attachment") or arguments.get("file_path"),
            }
            self.memory.sent_emails.append(sent_item)
            self.memory.last_sent_email = sent_item
            del self.memory.sent_emails[:-10]
        elif name == "read_recent_emails" and result.get("success"):
            assert self.memory.recent_emails is not None
            self.memory.recent_emails = result.get("emails", [])[:10]
        elif name == "search_emails" and result.get("success"):
            assert self.memory.recent_emails is not None
            self.memory.recent_emails = result.get("emails", [])[:10]
        elif name == "read_email" and result.get("success"):
            assert self.memory.recent_emails is not None
            self.memory.recent_emails = [result, *self.memory.recent_emails[:9]]

        if result.get("success"):
            subject = (
                result.get("path")
                or result.get("message_id")
                or result.get("draft_id")
                or result.get("application")
                or result.get("query")
                or arguments.get("path")
                or arguments.get("recipient")
                or arguments.get("filename")
                or name
            )
            self.memory.remember(f"Tool {name} succeeded: {subject}")
        else:
            self.memory.remember(f"Tool {name} failed: {result.get('error', 'unknown error')}")

    @staticmethod
    def _json_for_llm(result: dict[str, Any]) -> str:
        """Serialize tool output for the model with a hard size bound."""
        serialized = json.dumps(result, default=str)
        if len(serialized) <= MAX_TOOL_CONTENT_FOR_LLM:
            return serialized
        truncated_result = dict(result)
        if isinstance(truncated_result.get("content"), str):
            truncated_result["content"] = truncated_result["content"][:MAX_TOOL_CONTENT_FOR_LLM]
        truncated_result["llm_payload_truncated"] = True
        return json.dumps(truncated_result, default=str)[:MAX_TOOL_CONTENT_FOR_LLM]

    @staticmethod
    def _classify_workflow(message: str) -> str:
        """Classify the visible workflow for the UI context panel."""
        lower = message.lower()
        if any(word in lower for word in ("gmail", "inbox", "latest emails", "recent emails", "search emails")):
            return "Gmail reading/search"
        if any(word in lower for word in ("email", "send", "draft", "mail")):
            return "Email workflow"
        if "summarize all" in lower or "folder" in lower:
            return "Folder document analysis"
        if any(word in lower for word in ("summarize", "summary", "explain")):
            return "Document summarization"
        if any(word in lower for word in ("risk", "architecture", "tell me", "question", "answer")):
            return "Document question answering"
        if "search" in lower or "mentions" in lower or "references" in lower:
            return "Document content search"
        return "Desktop command"

    @staticmethod
    def _extract_document_path(message: str) -> str | None:
        """Best-effort path extraction for local no-LLM fallback."""
        quoted = re.findall(r"['\"]([^'\"]+\.(?:txt|md|pdf|docx|csv|json|py))['\"]", message, flags=re.IGNORECASE)
        if quoted:
            return quoted[0]

        matches = re.findall(r"((?:~|/|\w|\.|-|_|\s)+\.(?:txt|md|pdf|docx|csv|json|py))", message, flags=re.IGNORECASE)
        if not matches:
            return None
        candidate = matches[-1].strip()
        for prefix in ("summarize ", "explain ", "read ", "search "):
            if candidate.lower().startswith(prefix):
                candidate = candidate[len(prefix) :].strip()
        return candidate

    @staticmethod
    def _extract_summary_mode(message: str) -> str:
        """Infer summary style from user text."""
        for mode in ("technical", "beginner", "executive", "bullet point", "one paragraph"):
            if mode in message:
                return mode
        return "standard"

    @staticmethod
    def _extract_search_query(message: str) -> str | None:
        """Infer search query from common no-LLM fallback phrasings."""
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", message)
        if quoted:
            return quoted[-1]
        lowered = message.lower()
        for marker in ("mentions of", "references to", " for ", " query "):
            if marker in lowered:
                return message[lowered.rfind(marker) + len(marker) :].strip()
        return None

    @staticmethod
    def _format_local_summary(result: dict[str, Any]) -> str:
        """Render local fallback summary in the requested production format."""
        if not result.get("success"):
            return result.get("error", "Unable to summarize the file.")
        summary = result.get("summary", {})
        key_points = summary.get("key_points", [])
        actions = summary.get("action_items", [])
        return (
            "Summary\n"
            f"{summary.get('summary', 'No summary available.')}\n\n"
            "Key Points\n"
            + ("\n".join(f"- {item}" for item in key_points) if key_points else "- None found")
            + "\n\nImportant Information\n"
            + ", ".join(summary.get("important_terms", []) or ["None found"])
            + "\n\nAction Items\n"
            + ("\n".join(f"- {item}" for item in actions) if actions else "- None found")
            + "\n\nConclusion\n"
            + summary.get("conclusion", "No conclusion available.")
        )

    @staticmethod
    def _format_local_search(result: dict[str, Any]) -> str:
        """Render local fallback search results."""
        if not result.get("success"):
            return result.get("error", "Unable to search the file.")
        if not result.get("matches"):
            return f"No matches found for {result.get('query')!r}."
        lines = [f"Found {result.get('count')} match(es) for {result.get('query')!r}:"]
        for match in result["matches"][:10]:
            lines.append(f"- Line {match['line_number']}: {match['line']}")
        return "\n".join(lines)

    @staticmethod
    def _format_email_list(result: dict[str, Any]) -> str:
        """Render Gmail list/search results for local fallback."""
        if not result.get("success"):
            return result.get("error", "Unable to read Gmail.")
        emails = result.get("emails", [])
        if not emails:
            return "No matching emails found."
        lines = [f"Found {len(emails)} email(s):"]
        for email in emails[:10]:
            lines.append(
                f"- {email.get('date', '')} | {email.get('sender', '')} | "
                f"{email.get('subject', '')} | id: {email.get('message_id', '')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _draft_local_email(result: dict[str, Any], user_request: str) -> str:
        """Draft an email preview from local summary output."""
        if not result.get("success"):
            return result.get("error", "Unable to read the document for an email draft.")
        summary = result.get("summary", {})
        recipient = "Manager" if "manager" in user_request.lower() else "Recipient"
        points = summary.get("key_points", [])[:4]
        body_points = "\n".join(f"- {point}" for point in points) if points else "- Summary attached below."
        return (
            "Email Preview\n\n"
            f"Subject: Summary of {Path(result.get('path', 'the document')).name}\n\n"
            f"Hi {recipient},\n\n"
            "I reviewed the document and summarized the main points below:\n\n"
            f"{body_points}\n\n"
            f"Conclusion: {summary.get('conclusion', 'No conclusion available.')}\n\n"
            "Best,\n"
            "[Your Name]\n\n"
            "This is only a draft preview. I will not send it without confirmation."
        )

    @staticmethod
    def _latest_path(paths: list[str]) -> str | None:
        """Choose the most recently modified path from a list."""
        existing = [Path(path).expanduser() for path in paths if Path(path).expanduser().exists()]
        if not existing:
            return None
        return str(max(existing, key=lambda path: path.stat().st_mtime))

    @staticmethod
    def _summarize_tool_result(tool_name: str, result: dict[str, Any]) -> str:
        """Create readable text for fallback tool execution."""
        if not result.get("success"):
            return result.get("error", "The tool failed.")

        if tool_name == "find_file":
            matches = result.get("matches", [])
            if not matches:
                return "No matching files found."
            preview = "\n".join(matches[:10])
            suffix = "" if len(matches) <= 10 else f"\n...and {len(matches) - 10} more."
            return f"Found {len(matches)} match(es):\n{preview}{suffix}"

        if tool_name == "list_running_applications":
            apps = result.get("applications", [])
            return f"Running applications: {', '.join(apps)}" if apps else "No running applications found."

        return result.get("message", json.dumps(result, indent=2))

    @staticmethod
    def _build_tool_schemas() -> list[dict[str, Any]]:
        """Build Groq/OpenAI-compatible tool schemas for local MCP tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "scan_project",
                    "description": "Scan a project directory and return structured metadata including language, framework, package manager, entry points, and important files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the project directory (defaults to current directory)",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "find_file",
                    "description": "Search Desktop, Documents, and Downloads recursively for matching file paths.",
                    "parameters": {
                        "type": "object",
                        "properties": {"filename": {"type": "string"}},
                        "required": ["filename"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "Return files and folders in a directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "open_file",
                    "description": "Open a file or folder using the operating system default application.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_file_info",
                    "description": "Return file name, size, created date, and modified date.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "open_application",
                    "description": "Open applications such as Chrome, VS Code, Spotify, and Terminal on macOS.",
                    "parameters": {
                        "type": "object",
                        "properties": {"app_name": {"type": "string"}},
                        "required": ["app_name"],
                    },
                },
            },
            {
    "type": "function",
    "function": {
        "name": "open_browser",
        "description": (
            "Open a website in a browser. "
            "Use this whenever the user asks to open a URL or website."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Website URL such as github.com or https://google.com",
                }
            },
            "required": ["url"],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "google_search",
        "description": "Search Google for a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                }
            },
            "required": ["query"],
        },
    },
},
                
{
    "type": "function",
    "function": {
        "name": "list_running_applications",
                    "description": "Return currently running GUI applications on macOS.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": (
                        "Read supported documents (txt, md, pdf, docx, csv, json, py) and return text content "
                        "plus metadata. Use before summarizing or answering questions about document contents."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "summarize_file",
                    "description": (
                        "Create a local extractive summary preview for a supported document. Prefer read_file "
                        "when Groq should produce a richer summary in the requested style."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "mode": {
                                "type": "string",
                                "description": "Summary style such as standard, technical, beginner, executive, bullet point, one paragraph.",
                            },
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_file_content",
                    "description": "Search inside a supported document and return matching lines with context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "query": {"type": "string"},
                        },
                        "required": ["path", "query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "draft_email",
                    "description": "Create a Gmail draft email. Use for composition and previews before sending.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {"type": "string"},
                            "subject": {"type": "string"},
                            "body": {"type": "string"},
                        },
                        "required": ["recipient", "subject", "body"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": (
                        "Prepare a Gmail email for sending. The application will require explicit user "
                        "confirmation before this tool actually sends anything."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {"type": "string"},
                            "subject": {"type": "string"},
                            "body": {"type": "string"},
                        },
                        "required": ["recipient", "subject", "body"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_recent_emails",
                    "description": "Read the latest Gmail inbox emails and return sender, subject, date, snippet, and message id.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "count": {
                                "type": "integer",
                                "description": "Number of recent emails to return, capped by the Gmail tool.",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_emails",
                    "description": "Search Gmail using Gmail query syntax such as from:manager@gmail.com, has:attachment, newer_than:7d.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_email",
                    "description": "Read one Gmail message by message id and return headers plus body.",
                    "parameters": {
                        "type": "object",
                        "properties": {"message_id": {"type": "string"}},
                        "required": ["message_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "attach_and_send_email",
                    "description": (
                        "Prepare a Gmail email with one local attachment for sending. Supports pdf, docx, xlsx, "
                        "and txt attachments. The application will require explicit user confirmation before "
                        "this tool actually sends anything."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {"type": "string"},
                            "subject": {"type": "string"},
                            "body": {"type": "string"},
                            "file_path": {"type": "string"},
                        },
                        "required": ["recipient", "subject", "body", "file_path"],
                    },
                },
            },
        ]

    def _handle_project_explanation(self) -> AgentResult:
        """Generate a natural language explanation of the current project."""

        context = get_project_context(".")

        if not context.get("success"):
            return AgentResult(
                f"Unable to scan project: {context.get('error', 'Unknown error')}",
                [],
                self.memory.snapshot(),
            )

        formatted_context = format_project(context["metadata"])

        prompt = f"""
        You are a Principal Software Architect reviewing a production-ready software project.

        Your audience is an Engineering Manager.

        Below is automatically generated project context.

        {formatted_context}

        Your job is to explain the project as if you had spent several hours studying the codebase.

        Your explanation must include:

        1. What problem this project solves.
        2. Overall architecture.
        3. How the Model Context Protocol (MCP) is used.
        4. Responsibilities of the important folders.
        5. Responsibilities of the main services.
        6. How the request flow works.
        7. Strengths of the current architecture.
        8. Possible future improvements.

        Do not simply list metadata.

        Write naturally, professionally and confidently.
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You explain software architecture clearly.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
        )

        explanation = response.choices[0].message.content or "No explanation generated."

        return AgentResult(
            explanation,
            [],
            self.memory.snapshot(),
        )