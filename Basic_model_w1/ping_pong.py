"""ping_pong.py: Minimal two-agent turn-taking loop bounded by Budget (Week 1)."""
import argparse
from agents import Agent
from budget import Budget
from llm_client import make_client

# Define the two agents with distinct personas and system prompts
AGENT_A = Agent(
    name="Detective Cross",
    system_prompt=(
        "You are Detective Cross interrogating Julian Vance about the theft of the "
        "'Star of Midnight' diamond from the Grand Gallery vault at 21:30. "
        "Ask direct, pointed questions probing his whereabouts and uncover any inconsistencies in his alibi. "
        "Be concise: 1 to 2 sentences per response."
    ),
    temperature=0.3,
)

AGENT_B = Agent(
    name="Julian Vance",
    system_prompt=(
        "You are Julian Vance, chief curator and prime suspect in the theft of the 'Star of Midnight' diamond. "
        "Your alibi is that you were having dinner alone across town at the Grand Bistro between 21:00 and 22:30. "
        "Defend your alibi, respond cautiously, and do not admit guilt unless backed into a corner. "
        "Be concise: 1 to 2 sentences per response."
    ),
    temperature=0.5,
)


def run_dialogue(mock: bool = False, turns: int = 6):
    """Runs a dialogue between two agents for exactly N turns under Budget control."""
    client = make_client(mock=mock)
    agents = [AGENT_A, AGENT_B]
    transcript = []
    budget = Budget(max_turns=turns, max_tokens=4000, max_seconds=120)

    print(f"--- Starting Interrogation ({turns} turns cap) ---")
    while not budget.exhausted():
        speaker = agents[len(transcript) % 2]
        history = "\n".join(f"{name}: {text}" for name, text in transcript) or "(Interrogation starting.)"
        messages = [
            {"role": "system", "content": speaker.system_prompt},
            {
                "role": "user",
                "content": (
                    f"Dialogue so far:\n{history}\n\n"
                    f"Your turn, {speaker.name}. Speak in 1-2 sentences."
                ),
            },
        ]
        reply = client.chat(speaker.model, messages, temperature=speaker.temperature)
        transcript.append((speaker.name, reply.text))
        budget.record(turns=1, tokens=reply.tokens)
        print(f"[{speaker.name}]: {reply.text}\n")

    print(f"[Run finished | Stop reason: {budget.stop_reason} | Total turns: {budget.turns} | Total tokens: {budget.tokens}]")
    return transcript, budget


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a 2-agent dialogue loop capped by Budget.")
    parser.add_argument("--mock", action="store_true", help="run with offline MockClient")
    parser.add_argument("--turns", type=int, default=6, help="hard cap on number of turns (N)")
    args = parser.parse_args()

    run_dialogue(mock=args.mock, turns=args.turns)
