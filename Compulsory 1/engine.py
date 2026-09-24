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
    # 1. Start with the agent's system prompt
    msgs = [{"role": "system", "content": agent.system_prompt}]
    
    # 2. Add a starter message if the transcript is empty (Turn 0)
    if not transcript:
        msgs.append({"role": "user", "content": "You speak first."})
        
    # 3. Walk the neutral record and flip the roles accordingly
    for entry in transcript:
        role = "assistant" if entry.speaker == agent.name else "user"
        msgs.append({"role": role, "content": entry.content})
        
    return msgs

def truncate_context(messages, max_messages=10):
    """Keep the system prompt + the most recent (max_messages - 1) messages."""
    if len(messages) <= max_messages:
        return messages
    dropped = len(messages) - max_messages
    print(f"[context] Truncated {dropped} older message(s); keeping system prompt + last {max_messages - 1}.")
    return [messages[0]] + messages[-(max_messages - 1):]

def summarise_context(messages, client, model, max_messages=10):
    if len(messages) <= max_messages:
        return messages
        
    # Split: keep system prompt at [0], isolate the old middle, keep the recent end
    system = messages[0]
    old = messages[1:-(max_messages // 2)]
    recent = messages[-(max_messages // 2):]

    # Ask the model to compress the old messages with strict instructions
    summary_prompt = [
        {
            "role": "system", 
            "content": (
                "Summarise this interrogation in 3-4 sentences. "
                "You MUST preserve all exact timestamps, specific locations, alibi claims, and contradictions. "
                "Drop conversational filler, but keep the concrete evidence."
            )
        },
        {
            "role": "user", 
            "content": "\n".join(f"{m['role']}: {m['content']}" for m in old)
        }
    ]
    
    # temperature=0 ensures the summary remains factual and deterministic
    reply = client.chat(model, summary_prompt, temperature=0)
    print(f"[context] Summarised {len(old)} older message(s) into a persistent memory block.")

    # Rebuild: system + summary-as-user-message + recent verbatim messages
    summary_msg = {"role": "user", "content": f"[Summary of earlier conversation: {reply.text}]"}
    return [system, summary_msg] + recent


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
        self.manage_context = manage_context or summarise_context # default WEEK 3 hook to summarise context

    def next_speaker(self):
        return self.agents[len(self.transcript) % len(self.agents)]

    def run(self):
        while not self.budget.exhausted():
            speaker = self.next_speaker()
            messages = self.manage_context(view_for(speaker, self.transcript))
            
            # Call the LLM
            reply = self.client.chat(speaker.model, messages, speaker.temperature)
            
            # Create the transcript entry
            entry = Entry(
                speaker=speaker.name,
                content=reply.text,
                prompt_tokens=reply.prompt_tokens,
                completion_tokens=reply.completion_tokens,
                seconds=reply.seconds,
                turn_index=len(self.transcript)
            )
            self.transcript.append(entry)
            
            # Record the cost in the budget
            self.budget.record(turns=1, tokens=reply.tokens)
            
            # Check early stop condition
            if self.goal_reached(self.transcript):
                self.budget.stop("goal_reached")
                
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
