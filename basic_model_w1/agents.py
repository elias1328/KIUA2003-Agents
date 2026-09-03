"""agents.py: an Agent is just a name + a system prompt + which model/temperature.

COMPLETE. An agent has no behaviour of its own: the engine renders the
conversation from this agent's point of view (see engine.view_for) and asks the
model for the next message. That IS the agent.
"""
from dataclasses import dataclass


@dataclass
class Agent:
    name: str
    system_prompt: str
    model: str = "llama3.2:3b"
    temperature: float = 0.7
