"""FastMCP Gmail server with OAuth 2.0 authentication."""

from __future__ import annotations

import base64
import logging
import mimetypes
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("gmail")

BASE_DIR = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = BASE_DIR / "credentials" / "google_credentials.json"
TOKEN_PATH = BASE_DIR / "tokens" / "gmail_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
]
ATTACHMENT_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt"}
MAX_EMAIL_BODY_CHARS = 80_000


def _serialize_error(message: str, **extra: Any) -> dict[str, Any]:
    """Return a consistent error payload for MCP tool responses."""
    payload: dict[str, Any] = {"success": False, "error": message}
    payload.update(extra)
    return payload


def _gmail_service() -> Any:
    """Create an authenticated Gmail API service, refreshing tokens as needed."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError("Gmail support requires Google API dependencies. Run pip install -r requirements.txt") from exc

    credentials = None
    if TOKEN_PATH.exists():
        credentials = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"Missing Google OAuth client credentials at {CREDENTIALS_PATH}. "
                "Create an OAuth desktop client in Google Cloud Console and save it there."
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        credentials = flow.run_local_server(port=0, prompt="consent")

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials)


def _encode_message(message: EmailMessage) -> dict[str, str]:
    """Encode an EmailMessage for Gmail API send/draft calls."""
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    return {"raw": raw}


def _build_message(recipient: str, subject: str, body: str) -> EmailMessage:
    """Build a plain text email."""
    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    return message


def _build_message_with_attachment(recipient: str, subject: str, body: str, file_path: str) -> EmailMessage:
    """Build a plain text email with one supported attachment."""
    attachment = Path(file_path).expanduser()
    if not attachment.exists():
        raise FileNotFoundError(f"Attachment does not exist: {attachment}")
    if not attachment.is_file():
        raise ValueError(f"Attachment path is not a file: {attachment}")
    if attachment.suffix.lower() not in ATTACHMENT_EXTENSIONS:
        raise ValueError(
            f"Unsupported attachment type: {attachment.suffix or 'no extension'}. "
            f"Supported: {', '.join(sorted(ATTACHMENT_EXTENSIONS))}"
        )

    message = _build_message(recipient, subject, body)
    mime_type, _ = mimetypes.guess_type(str(attachment))
    maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
    message.add_attachment(
        attachment.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=attachment.name,
    )
    return message


def _header(headers: list[dict[str, str]], name: str) -> str:
    """Read a Gmail header by case-insensitive name."""
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _decode_body_part(part: dict[str, Any]) -> str:
    """Decode body data from a Gmail message part tree."""
    body = part.get("body", {})
    data = body.get("data")
    if data:
        return base64.urlsafe_b64decode(data.encode("ascii")).decode("utf-8", errors="replace")

    chunks: list[str] = []
    for child in part.get("parts", []) or []:
        mime_type = child.get("mimeType", "")
        if mime_type in {"text/plain", "text/html"} or child.get("parts"):
            decoded = _decode_body_part(child)
            if decoded:
                chunks.append(decoded)
    return "\n".join(chunks)


def _summarize_message(message: dict[str, Any]) -> dict[str, Any]:
    """Return compact message details for lists/search results."""
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    return {
        "message_id": message.get("id", ""),
        "thread_id": message.get("threadId", ""),
        "sender": _header(headers, "From"),
        "recipient": _header(headers, "To"),
        "subject": _header(headers, "Subject"),
        "date": _header(headers, "Date"),
        "snippet": message.get("snippet", ""),
    }


def send_email_impl(recipient: str, subject: str, body: str) -> dict[str, Any]:
    """Send an email through Gmail."""
    if not recipient.strip():
        return _serialize_error("recipient is required")
    if not subject.strip():
        return _serialize_error("subject is required")

    try:
        service = _gmail_service()
        message = _build_message(recipient, subject, body)
        sent = service.users().messages().send(userId="me", body=_encode_message(message)).execute()
    except Exception as exc:  # noqa: BLE001 - OAuth/API errors are library-specific.
        logger.exception("Unable to send Gmail message")
        return _serialize_error(str(exc))

    return {
        "success": True,
        "status": "sent",
        "message_id": sent.get("id"),
        "thread_id": sent.get("threadId"),
        "recipient": recipient,
        "subject": subject,
    }


def draft_email_impl(recipient: str, subject: str, body: str) -> dict[str, Any]:
    """Create a Gmail draft."""
    if not recipient.strip():
        return _serialize_error("recipient is required")
    if not subject.strip():
        return _serialize_error("subject is required")

    try:
        service = _gmail_service()
        message = _build_message(recipient, subject, body)
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body={"message": _encode_message(message)})
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 - OAuth/API errors are library-specific.
        logger.exception("Unable to create Gmail draft")
        return _serialize_error(str(exc))

    return {
        "success": True,
        "status": "draft_created",
        "draft_id": draft.get("id"),
        "message_id": draft.get("message", {}).get("id"),
        "recipient": recipient,
        "subject": subject,
    }


def read_recent_emails_impl(count: int = 10) -> dict[str, Any]:
    """Retrieve recent Gmail messages."""
    safe_count = max(1, min(int(count or 10), 50))
    try:
        service = _gmail_service()
        response = service.users().messages().list(userId="me", maxResults=safe_count, labelIds=["INBOX"]).execute()
        messages = []
        for item in response.get("messages", []) or []:
            message = (
                service.users()
                .messages()
                .get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "To", "Subject", "Date"])
                .execute()
            )
            messages.append(_summarize_message(message))
    except Exception as exc:  # noqa: BLE001 - OAuth/API errors are library-specific.
        logger.exception("Unable to read recent Gmail messages")
        return _serialize_error(str(exc))

    return {"success": True, "count": len(messages), "emails": messages}


def search_emails_impl(query: str) -> dict[str, Any]:
    """Search Gmail with a Gmail query string."""
    if not query.strip():
        return _serialize_error("query is required")

    try:
        service = _gmail_service()
        response = service.users().messages().list(userId="me", q=query, maxResults=20).execute()
        messages = []
        for item in response.get("messages", []) or []:
            message = (
                service.users()
                .messages()
                .get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "To", "Subject", "Date"])
                .execute()
            )
            messages.append(_summarize_message(message))
    except Exception as exc:  # noqa: BLE001 - OAuth/API errors are library-specific.
        logger.exception("Unable to search Gmail")
        return _serialize_error(str(exc))

    return {"success": True, "query": query, "count": len(messages), "emails": messages}


def read_email_impl(message_id: str) -> dict[str, Any]:
    """Read a Gmail message by ID."""
    if not message_id.strip():
        return _serialize_error("message_id is required")

    try:
        service = _gmail_service()
        message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        summary = _summarize_message(message)
        body = _decode_body_part(message.get("payload", {}))
        truncated = len(body) > MAX_EMAIL_BODY_CHARS
        if truncated:
            body = body[:MAX_EMAIL_BODY_CHARS]
    except Exception as exc:  # noqa: BLE001 - OAuth/API errors are library-specific.
        logger.exception("Unable to read Gmail message")
        return _serialize_error(str(exc))

    return {
        "success": True,
        **summary,
        "body": body,
        "body_truncated": truncated,
    }


def attach_and_send_email_impl(recipient: str, subject: str, body: str, file_path: str) -> dict[str, Any]:
    """Attach a local file and send an email through Gmail."""
    if not recipient.strip():
        return _serialize_error("recipient is required")
    if not subject.strip():
        return _serialize_error("subject is required")

    try:
        attachment = Path(file_path).expanduser()
        service = _gmail_service()
        message = _build_message_with_attachment(recipient, subject, body, file_path)
        sent = service.users().messages().send(userId="me", body=_encode_message(message)).execute()
    except Exception as exc:  # noqa: BLE001 - OAuth/API/path errors are library-specific.
        logger.exception("Unable to send Gmail message with attachment")
        return _serialize_error(str(exc))

    return {
        "success": True,
        "status": "sent",
        "message_id": sent.get("id"),
        "thread_id": sent.get("threadId"),
        "recipient": recipient,
        "subject": subject,
        "attachment": str(attachment),
    }


@mcp.tool()
def send_email(recipient: str, subject: str, body: str, confirmed: bool = False) -> dict[str, Any]:
    """Send an email through Gmail after explicit confirmation."""
    if not confirmed:
        return {
            "success": False,
            "requires_confirmation": True,
            "status": "pending_confirmation",
            "recipient": recipient,
            "subject": subject,
            "message": "Explicit confirmation is required before sending email.",
        }
    return send_email_impl(recipient, subject, body)


@mcp.tool()
def draft_email(recipient: str, subject: str, body: str) -> dict[str, Any]:
    """Create a Gmail draft."""
    return draft_email_impl(recipient, subject, body)


@mcp.tool()
def read_recent_emails(count: int = 10) -> dict[str, Any]:
    """Retrieve latest Gmail inbox emails."""
    return read_recent_emails_impl(count)


@mcp.tool()
def search_emails(query: str) -> dict[str, Any]:
    """Search Gmail with a Gmail query string."""
    return search_emails_impl(query)


@mcp.tool()
def read_email(message_id: str) -> dict[str, Any]:
    """Read one Gmail message by ID."""
    return read_email_impl(message_id)


@mcp.tool()
def attach_and_send_email(
    recipient: str,
    subject: str,
    body: str,
    file_path: str,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Attach a supported local file and send an email through Gmail after explicit confirmation."""
    if not confirmed:
        return {
            "success": False,
            "requires_confirmation": True,
            "status": "pending_confirmation",
            "recipient": recipient,
            "subject": subject,
            "attachment": file_path,
            "message": "Explicit confirmation is required before sending email.",
        }
    return attach_and_send_email_impl(recipient, subject, body, file_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run()
