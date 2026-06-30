"""PySide6 main window for the desktop MCP assistant."""

from __future__ import annotations

import json
import logging
from typing import Any

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ui.header_widget import HeaderWidget
from services.agent_service import AgentResult, AgentService
from ui.theme import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    app_stylesheet,
)

logger = logging.getLogger(__name__)


class AgentWorker(QObject):
    """Run an agent request outside the UI thread."""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, agent: AgentService, message: str) -> None:
        super().__init__()
        self.agent = agent
        self.message = message

    @Slot()
    def run(self) -> None:
        """Execute the agent request and emit the result."""
        try:
            self.finished.emit(self.agent.handle_message(self.message))
        except Exception as exc:  # noqa: BLE001 - keep the UI alive on unexpected failures.
            logger.exception("Agent worker failed")
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    """Desktop chat UI for the MCP assistant."""

    def __init__(self) -> None:
        super().__init__()
        self.agent = AgentService()
        self.current_thread: QThread | None = None
        self.current_worker: AgentWorker | None = None

        self.setWindowTitle("Sidekick AI")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._build_ui()
        self.setStyleSheet(app_stylesheet())

    def _build_ui(self) -> None:
        """Create widgets and layouts."""
        container = QWidget()
        root_layout = QVBoxLayout(container)
        header_widget = HeaderWidget()
        root_layout.addWidget(header_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        chat_panel = QGroupBox("Chat")
        chat_layout = QVBoxLayout(chat_panel)
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("Assistant conversation")
        chat_layout.addWidget(self.chat_history)

        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)

        tool_panel = QGroupBox("Tool Execution Log")
        tool_layout = QVBoxLayout(tool_panel)
        self.tool_log = QTextEdit()
        self.tool_log.setReadOnly(True)
        self.tool_log.setPlaceholderText("MCP tool calls and results")
        tool_layout.addWidget(self.tool_log)

        context_panel = QGroupBox("Current Context / Memory")
        context_layout = QVBoxLayout(context_panel)
        self.context_view = QTextEdit()
        self.context_view.setReadOnly(True)
        self.context_view.setMaximumHeight(230)
        context_layout.addWidget(self.context_view)

        email_panel = QGroupBox("Email")
        email_layout = QVBoxLayout(email_panel)
        self.email_view = QTextEdit()
        self.email_view.setReadOnly(True)
        self.email_view.setPlaceholderText("Drafts, sent emails, and recent Gmail messages")
        email_layout.addWidget(self.email_view)

        side_layout.addWidget(tool_panel, stretch=3)
        side_layout.addWidget(context_panel, stretch=2)
        side_layout.addWidget(email_panel, stretch=3)

        splitter.addWidget(chat_panel)
        splitter.addWidget(side_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText(
            "Ask me to summarize files, answer document questions, search folders, draft emails, or open apps..."
        )
        self.input_box.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)

        self.plan_button = QPushButton("Plan")
        self.plan_button.clicked.connect(self.plan_message)

        input_layout.addWidget(self.input_box, stretch=1)
        input_layout.addWidget(self.plan_button)
        input_layout.addWidget(self.send_button)

        root_layout.addWidget(splitter, stretch=1)
        root_layout.addLayout(input_layout)

        self.setCentralWidget(container)
        self._append_system_message(
            "Ready. Try: Summarize resume.pdf, Read report.pdf and tell me the risks, "
            "Find mentions of Groq, or Draft an email from the last summary."
        )
        self._update_context_view(self.agent.memory.snapshot())
        self._update_email_view(self.agent.memory.snapshot())
        self._build_email_preview_panel()

    @Slot()
    def send_message(self) -> None:
        """Send the current input text to the agent."""
        message = self.input_box.text().strip()
        if not message:
            return

        if self.current_thread is not None:
            self._append_system_message("Please wait for the current request to finish.")
            return

        self.input_box.clear()
        self._append_user_message(message)
        self._set_busy(True)

        self.current_thread = QThread()
        self.current_worker = AgentWorker(self.agent, message)
        self.current_worker.moveToThread(self.current_thread)

        self.current_thread.started.connect(self.current_worker.run)
        self.current_worker.finished.connect(self._handle_agent_result)
        self.current_worker.failed.connect(self._handle_agent_error)
        self.current_worker.finished.connect(self.current_thread.quit)
        self.current_worker.failed.connect(self.current_thread.quit)
        self.current_thread.finished.connect(self.current_worker.deleteLater)
        self.current_thread.finished.connect(self.current_thread.deleteLater)
        self.current_thread.finished.connect(self._clear_worker)
        self.current_thread.start()

    @Slot(object)
    def _handle_agent_result(self, result: AgentResult) -> None:
        """Render agent result and tool outputs."""
        for tool_result in result.tool_results:
            self._append_tool_result(tool_result)
        self._append_assistant_message(result.assistant_message)
        self._update_context_view(result.memory_snapshot)
        self._update_email_view(result.memory_snapshot)
        # refresh preview panel when pending email state changes
        try:
            self._refresh_email_preview(result.memory_snapshot)
        except Exception:
            pass
        self._set_busy(False)

    @Slot(str)
    def _handle_agent_error(self, error: str) -> None:
        """Render an unexpected agent failure."""
        self._append_system_message(f"Error: {error}")
        self._set_busy(False)

    @Slot()
    def _clear_worker(self) -> None:
        """Clear references after a worker thread exits."""
        self.current_thread = None
        self.current_worker = None

    def _set_busy(self, busy: bool) -> None:
        """Enable or disable input controls during work."""
        self.send_button.setEnabled(not busy)
        self.input_box.setEnabled(not busy)
        if busy:
            self._append_system_message("Working...")
        else:
            self.input_box.setFocus()

    def _append_user_message(self, text: str) -> None:
        self.chat_history.append(f"<b>You:</b> {self._escape(text)}")

    def _append_assistant_message(self, text: str) -> None:
        self.chat_history.append(f"<b>Assistant:</b> {self._escape(text).replace(chr(10), '<br>')}")

    def _append_system_message(self, text: str) -> None:
        self.chat_history.append(f"<span style='color:#666;'>{self._escape(text)}</span>")

    def _append_tool_result(self, tool_result: dict[str, Any]) -> None:
        payload = self._escape(json.dumps(tool_result, indent=2, default=str))
        self.tool_log.append(
            "<details open>"
            "<summary><b>Tool execution</b></summary>"
            f"<pre>{payload}</pre>"
            "</details>"
        )

    def _update_context_view(self, memory: dict[str, Any]) -> None:
        """Render memory in the context panel."""
        recent = memory.get("recent_context") or []
        recent_text = "\n".join(f"- {item}" for item in recent[-6:]) or "- None"
        context = (
            f"Last File Opened: {memory.get('last_file_opened') or 'None'}\n"
            f"Last File Read: {memory.get('last_file_read') or 'None'}\n"
            f"Last File Summarized: {memory.get('last_file_summarized') or 'None'}\n"
            f"Last Searched File: {memory.get('last_searched_file') or 'None'}\n"
            f"Last Folder: {memory.get('last_folder_analyzed') or 'None'}\n"
            f"Last Recipient: {memory.get('last_recipient') or 'None'}\n"
            f"Last Email Subject: {memory.get('last_email_subject') or 'None'}\n"
            f"Last Draft: {memory.get('last_draft') or 'None'}\n"
            f"Last Attachment: {memory.get('last_attachment') or 'None'}\n"
            f"Pending Email: {'Yes' if memory.get('pending_email_action') else 'No'}\n"
            f"Last Action: {memory.get('last_action') or 'None'}\n"
            f"Current Workflow: {memory.get('current_workflow') or 'None'}\n\n"
            f"Last Sent Email: {memory.get('last_sent_email') or 'None'}\n"
            f"Recent Contacts: {', '.join(c.get('recipient','') for c in (memory.get('recent_contacts') or [])[:5]) or 'None'}\n\n"
            f"Recent Context:\n{recent_text}"
        )
        self.context_view.setPlainText(context)

    def _update_email_view(self, memory: dict[str, Any]) -> None:
        """Render recent Gmail-related activity."""
        drafts = memory.get("drafts") or []
        sent = memory.get("sent_emails") or []
        recent = memory.get("recent_emails") or []
        pending = memory.get("pending_email_action")

        lines: list[str] = []
        lines.append("Pending Send:")
        if pending:
            arguments = pending.get("arguments", {})
            lines.append(f"- {arguments.get('recipient', '')} | {arguments.get('subject', '')}")
            if arguments.get("file_path"):
                lines.append(f"  Attachment: {arguments.get('file_path')}")
        else:
            lines.append("- None")

        lines.append("\nDrafts:")
        if drafts:
            lines.extend(f"- {item.get('recipient', '')} | {item.get('subject', '')} | {item.get('draft_id', '')}" for item in drafts[-5:])
        else:
            lines.append("- None")

        lines.append("\nSent Emails:")
        if sent:
            lines.extend(f"- {item.get('recipient', '')} | {item.get('subject', '')} | {item.get('message_id', '')}" for item in sent[-5:])
        else:
            lines.append("- None")

        lines.append("\nRecent Emails:")
        if recent:
            lines.extend(
                f"- {item.get('date', '')} | {item.get('sender', '')} | {item.get('subject', '')} | {item.get('message_id', '')}"
                for item in recent[:8]
            )
        else:
            lines.append("- None")

        self.email_view.setPlainText("\n".join(lines))

    def _build_email_preview_panel(self) -> None:
        """Create an email preview panel with Approve/Cancel controls."""
        self.email_preview_group = QGroupBox("Email Preview & Approval")
        layout = QVBoxLayout(self.email_preview_group)
        self.email_preview = QTextEdit()
        self.email_preview.setReadOnly(True)
        layout.addWidget(self.email_preview)

        btn_layout = QHBoxLayout()
        self.approve_button = QPushButton("Approve & Send")
        self.approve_button.clicked.connect(self._approve_pending_email)
        self.cancel_button = QPushButton("Cancel Send")
        self.cancel_button.clicked.connect(self._cancel_pending_email)
        btn_layout.addWidget(self.approve_button)
        btn_layout.addWidget(self.cancel_button)
        layout.addLayout(btn_layout)

        # place under side panel by adding to central layout
        # find the side panel layout and insert the preview
        # fallback: add to root layout bottom if not present
        try:
            # insert before input layout (side of splitter)
            self.centralWidget().layout().insertWidget(1, self.email_preview_group)
        except Exception:
            self.centralWidget().layout().addWidget(self.email_preview_group)
        self._refresh_email_preview(self.agent.memory.snapshot())

    def _refresh_email_preview(self, memory: dict[str, Any]) -> None:
        pending = memory.get("pending_email_action")
        if not pending:
            self.email_preview.setPlainText("No pending email to preview.")
            self.approve_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            return

        arguments = pending.get("arguments", {})
        attachment = arguments.get("file_path") or arguments.get("attachment")
        body = arguments.get("body") or ""
        text = (
            f"Recipient: {arguments.get('recipient','')}\n"
            f"Subject: {arguments.get('subject','')}\n\n"
            f"Body:\n{body}\n\n"
        )
        if attachment:
            text += f"Attachment: {attachment}\n"

        text += "\nClick 'Approve & Send' to send, or 'Cancel Send' to discard."
        self.email_preview.setPlainText(text)
        self.approve_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def _approve_pending_email(self) -> None:
        """Approve and send the pending email by invoking the agent confirmation flow."""
        self._append_system_message("Sending pending email...")
        result = self.agent._maybe_execute_pending_email("send it now")
        if result:
            self._handle_agent_result(result)

    def _cancel_pending_email(self) -> None:
        """Cancel the pending email."""
        result = self.agent._maybe_execute_pending_email("cancel")
        if result:
            self._handle_agent_result(result)

    def plan_message(self) -> None:
        """Send a planning request to the agent for the current input text."""
        message = self.input_box.text().strip()
        if not message:
            self._append_system_message("Enter something to plan first.")
            return
        # send a planning-prefixed request to the agent
        plan_text = f"Plan: {message}"
        self._append_user_message(plan_text)
        self._set_busy(True)

        self.current_thread = QThread()
        self.current_worker = AgentWorker(self.agent, plan_text)
        self.current_worker.moveToThread(self.current_thread)

        self.current_thread.started.connect(self.current_worker.run)
        self.current_worker.finished.connect(self._handle_agent_result)
        self.current_worker.failed.connect(self._handle_agent_error)
        self.current_worker.finished.connect(self.current_thread.quit)
        self.current_worker.failed.connect(self.current_thread.quit)
        self.current_thread.finished.connect(self.current_worker.deleteLater)
        self.current_thread.finished.connect(self.current_thread.deleteLater)
        self.current_thread.finished.connect(self._clear_worker)
        self.current_thread.start()

    @staticmethod
    def _escape(text: str) -> str:
        """Escape text for basic HTML display in QTextEdit."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
