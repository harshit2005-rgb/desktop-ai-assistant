"""
Intent Router

Routes simple commands directly to local tools without using the LLM.
"""

from __future__ import annotations
from config.applications import APPLICATION_ALIASES
from typing import Any
from config.file_extensions import FILE_EXTENSIONS


class IntentRouter:
    """
    Detect simple commands that can bypass the LLM.
    """

    # Word to number mapping for ordinal commands
    ORDINAL_MAP = {
        "first": 0,
        "second": 1,
        "third": 2,
    }

    def route(self, message: str, memory: Any = None) -> dict[str, Any] | None:
        text = message.strip().lower()

        # --------------------------
        # Search Result Actions (open, info, summarize)
        # --------------------------
        result = self._try_search_result_action(text, memory)
        if result is not None:
            return result

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
        

        # --------------------------
        # Open Application
        # --------------------------
   
        if text.startswith("open "):

            name = message[5:].strip()
            alias = name.lower()

            if alias in APPLICATION_ALIASES:
                return {
                    "tool": "open_application",
                    "arguments": {
                        "app_name": APPLICATION_ALIASES[alias],
                    },
             }
            
        # --------------------------
        # Open File
        # --------------------------

        if text.startswith("open "):

            target = message[5:].strip()

            if any(target.lower().endswith(ext) for ext in FILE_EXTENSIONS):
                return {
                    "tool": "open_file",
                    "arguments": {
                        "path": target,
                    },
                }
        # --------------------------
        # Find File
        # --------------------------

        if text.startswith("find "):

            filename = message[5:].strip()

            return {
                "tool": "find_file",
                "arguments": {
                    "filename": filename,
                },
            }
        # --------------------------
        # File Info
        # --------------------------

        if text.startswith("info "):

            filename = message[5:].strip()

            return {
                "tool": "get_file_info",
                "arguments": {
                    "path": filename,
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

    def _try_search_result_action(self, text: str, memory: Any) -> dict[str, Any] | None:
        """
        Handle actions on numbered search results: open 1, info 2, summarize 3, etc.
        Also supports ordinals: open first, info second, summarize third.
        """
        # Parse "open N", "info N", or "summarize N" commands
        for action in ["open ", "info ", "summarize "]:
            if text.startswith(action):
                remainder = text[len(action):].strip()
                index = self._parse_index(remainder)

                if index is not None:
                    return self._execute_search_result_action(
                        action.strip(),
                        index,
                        memory,
                    )

        return None

    def _parse_index(self, remainder: str) -> int | None:
        """
        Parse index from 'N' (digit) or ordinal word (first, second, third).
        Returns 0-based index or None if not parseable.
        """
        remainder = remainder.lower().strip()

        # Try parsing as ordinal word
        if remainder in self.ORDINAL_MAP:
            return self.ORDINAL_MAP[remainder]

        # Try parsing as digit
        if remainder.isdigit():
            num = int(remainder)
            if num >= 1:  # Convert 1-based to 0-based
                return num - 1

        return None

    def _execute_search_result_action(
        self, action: str, index: int, memory: Any
    ) -> dict[str, Any] | None:
        """
        Execute action (open, info, summarize) on a search result at given index.
        Returns tool dict or error message dict.
        """
        # Check if memory exists
        if memory is None:
            return self._error_response(
                "No previous search results found.\n"
                "Please run a search first."
            )

        # Check if search results exist
        if not memory.last_search_results:
            return self._error_response(
                "No previous search results found.\n"
                "Please run a search first."
            )

        # Check if index is valid
        if index >= len(memory.last_search_results):
            result_num = index + 1  # Convert back to 1-based for display
            return self._error_response(
                f"Search result #{result_num} does not exist.\n"
                f"Please run another search or choose a valid number."
            )

        # Get the file path
        file_path = memory.last_search_results[index]

        # Return the appropriate tool
        if action == "open":
            return {
                "tool": "open_file",
                "arguments": {
                    "path": file_path,
                },
            }
        elif action == "info":
            return {
                "tool": "get_file_info",
                "arguments": {
                    "path": file_path,
                },
            }
        elif action == "summarize":
            return {
                "tool": "summarize_file",
                "arguments": {
                    "path": file_path,
                },
            }

        return None

    def _error_response(self, message: str) -> dict[str, Any]:
        """Return a special error response that will be handled by the agent."""
        return {
            "tool": "error",
            "arguments": {
                "message": message,
            },
        }


intent_router = IntentRouter()