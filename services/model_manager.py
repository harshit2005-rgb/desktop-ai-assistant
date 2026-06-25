"""
Model Manager

Responsible for:
- Loading AI providers
- Selecting the active model
- Sending chat requests
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq


DEFAULT_MODEL = "llama-3.3-70b-versatile"


class ModelManager:
    """
    Central place responsible for all AI models.

    Today:
        - Groq

    Future:
        - Ollama
        - OpenAI
        - Gemini
        - Claude
    """

    def __init__(self) -> None:
        load_dotenv()

        self.provider = os.getenv("MODEL_PROVIDER", "groq").lower()
        self.model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)

        self.client = None

        if self.provider == "groq":
            self._initialize_groq()

    def _initialize_groq(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        if api_key and not api_key.startswith("your_"):
            self.client = Groq(api_key=api_key)

    @property
    def available(self) -> bool:
        return self.client is not None

    def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.1,
    ):
        """
        Send a chat request to the currently selected model.
        """

        if self.client is None:
            raise RuntimeError("No AI provider configured.")

        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
        )