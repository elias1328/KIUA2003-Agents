"""agents.py: Agent dataclass defining name, system prompt, model, and temperature."""
from dataclasses import dataclass


@dataclass
class Agent:
    name: str
    system_prompt: str
    model: str = "llama3.2:3b"
    temperature: float = 0.7
