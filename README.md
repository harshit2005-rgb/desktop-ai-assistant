# Desktop MCP Agent

A Python desktop AI assistant that uses FastMCP-style tools for filesystem and application operations, PySide6 for the UI, and Groq for LLM tool-calling.

## Features

- Find files under `Desktop`, `Documents`, and `Downloads`
- List directory contents
- Open files with the operating system default application
- Get file metadata
- Open macOS applications such as Chrome, VS Code, Spotify, and Terminal
- List running macOS GUI applications
- Read supported documents: `txt`, `md`, `pdf`, `docx`, `csv`, `json`, and `py`
- Summarize documents with standard, technical, beginner, executive, bullet-point, and one-paragraph modes
- Answer questions from document content only
- Analyze folders by chaining directory listing and document reads
- Search inside supported files with matching lines and context
- Remember last opened/read/summarized/searched files and last analyzed folder for follow-up requests
- Read, search, draft, and send Gmail messages after OAuth authorization
- Attach supported files (`pdf`, `docx`, `xlsx`, `txt`) to Gmail sends
- Draft email previews from document summaries without sending automatically
- Require explicit confirmation before sending Gmail messages
- Display chat, tool execution logs, current memory/context, and Gmail activity in separate desktop UI panels

## Setup

```bash
cd desktop-mcp-agent
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Edit `.env` and set:

```bash
GROQ_API_KEY=your_real_groq_api_key
```

If `GROQ_API_KEY` is missing or left as a placeholder, the app still starts with a simple local fallback for commands like `Open VS Code`, `Find resume.pdf`, and `List running applications`.
The local fallback can also read/search/summarize documents with deterministic extractive summaries, but Groq is required for richer multi-step reasoning and adaptive document answers.

## Gmail OAuth Setup

1. Create an OAuth 2.0 Desktop client in Google Cloud Console.
2. Enable the Gmail API for that Google Cloud project.
3. Download the OAuth client JSON.
4. Save it as:

```text
credentials/google_credentials.json
```

On the first Gmail action, the app opens a browser for Google login and consent. The OAuth token is saved locally as:

```text
tokens/gmail_token.json
```

The app refreshes expired tokens automatically when Google provides a refresh token. Do not commit either credentials or token files.

## Run The Desktop App

```bash
python app.py
```

## Run MCP Servers

In separate terminals:

```bash
python mcp_servers/filesystem_server.py
```

```bash
python mcp_servers/application_server.py
```

```bash
python mcp_servers/document_server.py
```

```bash
python mcp_servers/gmail_server.py
```

The desktop app currently imports and executes the same tool implementations in-process. The FastMCP server wrappers are included so the tools can also run as standalone MCP servers.

## Example Commands

- `Open VS Code`
- `Find resume.pdf`
- `Open my latest resume`
- `List running applications`
- `List my Downloads folder`
- `Get file info for /Users/yourname/Downloads/resume.pdf`
- `Summarize /Users/yourname/Downloads/report.pdf`
- `Give me a technical summary of project_report.docx`
- `Explain notes.txt like I'm a beginner`
- `Read report.pdf and tell me the risks`
- `Find mentions of MCP in architecture.md`
- `Summarize all PDFs in Downloads`
- `Read today's report and draft an email to my manager`
- `Show my latest emails`
- `Search emails from:manager@gmail.com newer_than:7d`
- `Read email MESSAGE_ID`
- `Draft an email to rahul@example.com about the report`
- `Find my latest resume and send it to rahul@example.com`
- `Send it now`

## Project Structure

```text
desktop-mcp-agent/
├── app.py
├── .env
├── requirements.txt
├── README.md
├── mcp_servers/
│   ├── __init__.py
│   ├── filesystem_server.py
│   ├── application_server.py
│   ├── document_server.py
│   └── gmail_server.py
├── credentials/
│   └── google_credentials.json
├── tokens/
│   └── gmail_token.json
├── services/
│   ├── __init__.py
│   └── agent_service.py
└── ui/
    ├── __init__.py
    └── main_window.py
```

## Notes

- Application tools support macOS initially.
- File search is recursive and can take time if `Desktop`, `Documents`, or `Downloads` contain many files.
- Document reads are bounded for safety. Very large files may return truncated content with metadata indicating truncation.
- PDF support uses `pypdf`; DOCX support uses `python-docx`.
- Gmail OAuth uses Google client credentials from `credentials/google_credentials.json`; secrets are never hardcoded.
- The assistant never sends emails automatically. Send tools are held as pending actions until the user explicitly confirms with wording such as `send it now` or `confirm`.
- Destructive actions such as deleting or moving files must ask for confirmation before execution.
- Opening apps and files may trigger macOS permission prompts depending on local security settings.
