"""llm_client.py: Minimal client wrapper for Ollama and offline Mock."""
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
    """Calls a local model served by Ollama."""

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
                f"Cannot connect to Ollama at {self.host}. Start it with: ollama serve"
            ) from None
        if resp.status_code == 404:
            raise RuntimeError(f"Model '{model}' not found. Pull it first: ollama pull {model}")
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            text=data["message"]["content"].strip(),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            seconds=time.monotonic() - t0,
        )


class MockClient:
    """Offline test client cycling canned responses for quick, free debugging."""

    DEFAULT_REPLIES = [
        "Where were you last night at 21:30 when the gallery vault was breached?",
        "I was having dinner alone across town at the Grand Bistro between 21:00 and 22:30.",
        "Our records show the Grand Bistro was closed all night due to emergency plumbing repairs.",
        "I... must have mixed up the name of the restaurant, detective.",
        "You swiped your master keycard at the vault at 21:28. How do you explain that?",
        "Alright, you caught me. I took the diamond because of my debts.",
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
