"""engine.py: WEEK 2 target: a reusable two-agent dialogue engine.

The guardrails (Budget) and the bookkeeping (Entry, save) are DONE.
You implement the two parts marked `# TODO (WEEK 2)`:
  1. view_for(...)      - render the conversation from one agent's point of view
  2. DialogueEngine.run - the orchestration loop

In WEEK 3 you also implement the `manage_context` hook (truncation/summarisation).

Read the Week 2 handout alongside this file.
"""
import json
from dataclasses import asdict, dataclass

from budget import Budget  # used by DialogueEngine's constructor parameter


@dataclass
class Entry:
    """One message in the conversation, with its measured cost."""
    speaker: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    turn_index: int


def view_for(agent, transcript):
    """Build the message list to send to `agent`, from ITS point of view.

    Requirements (this is the key idea of Week 2):
      - first message: {"role": "system", "content": agent.system_prompt}
      - for each Entry in transcript:
            role = "assistant" if it was spoken by THIS agent
            role = "user"      if it was spoken by the OTHER agent
      - if the transcript is empty (turn 0), add a user message like
            {"role": "user", "content": "You speak first."}
        so the model always gets at least system + user.
      - return the list of {"role", "content"} dicts.

    Tip: test it by hand-building a 3-entry transcript and printing the view for
    each of your two agents; the roles should be mirror images.
    """
    # TODO (WEEK 2): implement and DELETE the line below.
    raise NotImplementedError("Implement view_for; see the docstring.")


class DialogueEngine:
    """Runs two (or more) agents in turn until a Budget stop fires.

    agents:        list of Agent; turn order follows the list, then wraps.
    client:        an OllamaClient or MockClient.
    budget:        a Budget instance (your three guardrails).
    goal_reached:  optional fn(transcript) -> bool; return True when the
                   scenario goal is met (engine then stops with 'goal_reached').
    manage_context: optional fn(messages) -> messages; WEEK 3 hook to keep the
                   message list inside the context window. Default: no-op.
    """

    def __init__(self, agents, client, budget, goal_reached=None, manage_context=None):
        self.agents = agents
        self.client = client
        self.budget = budget
        self.transcript = []  # list[Entry]
        self.goal_reached = goal_reached or (lambda t: False)
        self.manage_context = manage_context or (lambda messages: messages)

    def next_speaker(self):
        return self.agents[len(self.transcript) % len(self.agents)]

    def run(self):
        """Run the dialogue to completion. Return the final transcript.

        Loop shape (fill in the body):
            while not self.budget.exhausted():
                speaker = self.next_speaker()
                messages = self.manage_context(view_for(speaker, self.transcript))
                reply = self.client.chat(speaker.model, messages, speaker.temperature)
                append Entry(speaker.name, reply.text, reply.prompt_tokens,
                             reply.completion_tokens, reply.seconds,
                             len(self.transcript)) to self.transcript
                self.budget.record(turns=1, tokens=reply.tokens)
                if self.goal_reached(self.transcript):
                    self.budget.stop("goal_reached")
            return self.transcript
        """
        # TODO (WEEK 2): implement the loop above and DELETE this line.
        raise NotImplementedError("Implement DialogueEngine.run; see the docstring.")

    # === bookkeeping below is DONE ===

    def save(self, path, meta=None):
        """Write a structured JSON transcript: a run header + every message."""
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        record = {
            "meta": meta or {},
            "agents": [
                {"name": a.name, "model": a.model, "temperature": a.temperature}
                for a in self.agents
            ],
            "budget": self.budget.summary(),
            "totals": {
                "turns": len(self.transcript),
                "prompt_tokens": sum(e.prompt_tokens for e in self.transcript),
                "completion_tokens": sum(e.completion_tokens for e in self.transcript),
                "seconds": round(sum(e.seconds for e in self.transcript), 3),
            },
            "messages": [asdict(e) for e in self.transcript],
        }
        with open(path, "w") as f:
            json.dump(record, f, indent=2)
        return path
