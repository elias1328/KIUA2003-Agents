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
    #1. Start with the agents persona instructions
    messages = [{"role": "system", "content": agent.system_prompt}]

    #2. If nobody has spoken yet, give the first agent a push to start
    if not transcript:
        messages.append({"role": "user", "content": "You speak first."})
        return messages

    #3. Otherwise, convert each message from this agent's point of view
    for entry in transcript:
        if entry.speaker == agent.name:
            role = "assistant" # I said this
        else:
            role = "user" # The other agent said this to me

        messages.append({"role": role, "content": entry.content})

    #4. Return the list of message directories
    return messages


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
        # 1. Keep going until a limit fires (turns, tokens, or time)
        while not self.budget.exhausted():

            # 2. Pick who speaks next
            speaker = self.next_speaker()

            # 3. Create the perspective-correct message list using view_for
            messages = self.manage_context(view_for(speaker, self.transcript))

            # 4. Call the LLM to get the response
            reply = self.client.chat(speaker.model, messages, speaker.temperature)

            # 5. Wrap the reply and its metrics (tokens, time) into an Entry
            entry = Entry(
                speaker=speaker.name,
                content=reply.text,
                prompt_tokens=reply.prompt_tokens,
                completion_tokens=reply.completion_tokens,
                seconds=reply.seconds,
                turn_index=len(self.transcript),
            )
            self.transcript.append(entry)

            # 6. Inform the budget of turns and tokens used
            self.budget.record(turns=1, tokens=reply.tokens)

            # 7. Check if domain goal is met (e.g price agreed)
            if self.goal_reached(self.transcript):
                self.budget.stop("goal_reached")

        # When loop finishes, return the full conversation history
        return self.transcript



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


