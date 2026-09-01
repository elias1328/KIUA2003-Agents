"""Quick self-check for your Week 2 implementation.

Run:  python test_engine.py

If view_for and run() are correct, this prints "All checks passed."
If something is wrong, it tells you what failed.
"""
from agents import Agent
from budget import Budget
from engine import Entry, view_for, DialogueEngine
from llm_client import make_client

A = Agent("Alice", "You are Alice.")
B = Agent("Bob", "You are Bob.")

# -- Check view_for --

transcript = [
    Entry("Alice", "Hi Bob.", 10, 5, 0.1, 0),
    Entry("Bob", "Hey Alice.", 12, 6, 0.1, 1),
    Entry("Alice", "How's it going?", 14, 7, 0.1, 2),
]

alice_view = view_for(A, transcript)
bob_view = view_for(B, transcript)

# Alice's view: her own words are "assistant", Bob's are "user"
assert alice_view[0] == {"role": "system", "content": "You are Alice."}, \
    "First message should be Alice's system prompt"
assert alice_view[1]["role"] == "assistant", \
    "Alice's own message should appear as 'assistant'"
assert alice_view[2]["role"] == "user", \
    "Bob's message should appear as 'user' in Alice's view"
assert alice_view[3]["role"] == "assistant", \
    "Alice's second message should be 'assistant'"

# Bob's view: mirror image
assert bob_view[0] == {"role": "system", "content": "You are Bob."}, \
    "First message should be Bob's system prompt"
assert bob_view[1]["role"] == "user", \
    "Alice's message should appear as 'user' in Bob's view"
assert bob_view[2]["role"] == "assistant", \
    "Bob's own message should appear as 'assistant'"

# Empty transcript should still produce at least system + user
empty_view = view_for(A, [])
assert len(empty_view) >= 2, \
    "Empty transcript should produce system prompt + a starter user message"
assert empty_view[0]["role"] == "system"
assert empty_view[1]["role"] == "user"

print("view_for: OK")

# -- Check run() --

client = make_client(mock=True)
budget = Budget(max_turns=4, max_tokens=4000, max_seconds=60)
engine = DialogueEngine([A, B], client, budget)
result = engine.run()

assert len(result) == 4, f"Expected 4 turns, got {len(result)}"
assert result[0].speaker == "Alice", "Alice should speak first"
assert result[1].speaker == "Bob", "Bob should speak second"
assert result[2].speaker == "Alice", "Turns should alternate"
assert budget.stop_reason == "max_turns", f"Expected max_turns, got {budget.stop_reason}"

for i, e in enumerate(result):
    assert e.turn_index == i, f"Entry {i} has turn_index={e.turn_index}, expected {i}"
    assert e.prompt_tokens > 0, f"Entry {i} has 0 prompt_tokens"
    assert e.completion_tokens > 0, f"Entry {i} has 0 completion_tokens"

print("run():    OK")

# -- Check save() --

import os, json
path = engine.save("transcripts/_test.json", meta={"test": True})
assert os.path.exists(path), f"save() didn't create {path}"
with open(path) as f:
    data = json.load(f)
assert len(data["messages"]) == 4
assert data["budget"]["stop_reason"] == "max_turns"
os.remove(path)

print("save():   OK")
print("\nAll checks passed.")
