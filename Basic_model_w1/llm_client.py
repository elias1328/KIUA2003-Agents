"""Thin wrapper over a chat model. You don't need to change this file.

Two clients, same interface:
  OllamaClient  -- talks to a local model via Ollama's /api/chat
  MockClient    -- canned replies, instant and free (use for development)

Usage:
    client = make_client(mock=True)   # or mock=False for the real model
    reply = client.chat("llama3.2:3b", messages, temperature=0.7)
    print(reply.text, reply.tokens, reply.seconds)
"""
import time
from dataclasses import dataclass

import requests


@dataclass
class ChatResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    seconds: float

    @property
    def tokens(self):
        return self.prompt_tokens + self.completion_tokens


class OllamaClient:
    """Calls a local model served by Ollama (https://ollama.com)."""

    def __init__(self, host="http://localhost:11434"):
        self.host = host

    def chat(self, model, messages, temperature=0.7):
        t0 = time.monotonic()
        try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=300,
            )
        except requests.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.host}.\n"
                f"Is Ollama running? Start it with: ollama serve\n"
                f"Or run with --mock to develop without a model."
            ) from None
        if resp.status_code == 404:
            raise RuntimeError(
                f"Model '{model}' not found.\n"
                f"Pull it first: ollama pull {model}\n"
                f"Or run with --mock to develop without a model."
            )
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            text=data["message"]["content"].strip(),
            prompt_tokens=data.get("prompt_eval_count", 0),   # exact, from Ollama
            completion_tokens=data.get("eval_count", 0),
            seconds=time.monotonic() - t0,
        )


class MockClient:
    """Free, instant, offline. Cycles through canned replies.

    Token counts are approximated by word count, good enough to exercise your
    Budget logic while you debug the loop. Swap to OllamaClient for real runs.
    """

    DEFAULT_REPLIES = [
        "I think we should weigh the costs before anything else.",
        "Fair, but the long-term benefits clearly outweigh those costs.",
        "Only if we ignore the people who can't adapt quickly.",
        "We can support them with a transition plan; that's solvable.",
        "Then let's agree the plan matters as much as the decision.",
        "Agreed. I think that's our common ground.",
    ]

    def __init__(self, replies=None):
        self._replies = replies or self.DEFAULT_REPLIES
        self._i = 0

    def chat(self, model, messages, temperature=0.7):
        text = self._replies[self._i % len(self._replies)]
        self._i += 1
        prompt_tokens = sum(len(m["content"].split()) for m in messages)
        return ChatResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=max(1, len(text.split())),
            seconds=0.01,
        )


def make_client(mock=False, host="http://localhost:11434"):
    return MockClient() if mock else OllamaClient(host=host)
