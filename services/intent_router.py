"""
Intent Router

Routes simple commands directly to local tools without using the LLM.
"""

from __future__ import annotations

import re
from typing import Any


class IntentRouter:
    """
    Detect simple commands that can bypass the LLM.
    """

    def route(self, message: str) -> dict[str, Any] | None:
        text = message.strip().lower()

        # Open website
        if text.startswith("open ") and (
            ".com" in text or ".org" in text or ".io" in text
        ):
            url = message[5:].strip()

            return {
                "tool": "open_browser",
                "arguments": {
                    "url": url,
                },
            }

        # Google Search
        if text.startswith("search google for "):
            query = message[len("search google for "):].strip()

            return {
                "tool": "google_search",
                "arguments": {
                    "query": query,
                },
            }

        return None


intent_router = IntentRouter()