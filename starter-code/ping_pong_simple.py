"""ping_pong_detective.py: Simple 3-Agent loop with basic tool calling.

Run:  python ping_pong_detective.py --mock
      python ping_pong_detective.py --turns 6
"""
import argparse
import re

from agents import Agent
from budget import Budget
from llm_client import make_client

# === Hardcoded Database for Tools (From Museum Diamond Heist Scenario) ===
EVIDENCE_DB = {
    "finger_prints": "A partial fingerprint match was found on one of the stolen items, which was later identified as belonging to Julian Vance.",
    "traffic_cameras": "Traffic cameras show low traffic on Main Avenue between 21:00 and 22:00.",
    "vault_keycard_logs": "Master keycard #04 swiped at Vault Door 2 at 21:28.",
    "security_guard_notes": "Guard on duty reported motion sensor alarm triggered at 21:32."
}

# === Your three personas ===
TOPIC = "The 'Star of Midnight' blue diamond was stolen from the gallery vault at 21:30."

AGENT_A = Agent(
    "Detective_Cross", 
    "You are Detective Cross. Ask probing questions about the diamond heist. "
    "You can check evidence by including [LOOKUP: <category>] in your response. "
    "Available categories: finger_prints, traffic_cameras, vault_keycard_logs, security_guard_notes. Be brief: 2 sentences max."
)
AGENT_B = Agent(
    "Julian_Vance", 
    "You are Julian Vance, Chief Curator and prime suspect. Your alibi is: 'I was having dinner at the 24/7 Grand Bistro across town from 21:00 to 22:30, paying with cash.' "
    "Politely defend your story and invent excuses for any evidence presented. Be brief: 2 sentences max."
)
AGENT_C = Agent(
    "Chief_Inspector_Ward", 
    "You are Chief Inspector Ward. Review the transcript, evaluate the evidence used against the suspect's alibi, "
    "and declare the suspect 'GUILTY - ARREST' or 'INNOCENT - EXONERATE' in 3 sentences."
)

def render(transcript):
    if not transcript:
        return "(You speak first.)"
    return "\n".join(f"{name}: {text}" for name, text in transcript)

def handle_tool_call(text):
    """Simple regex to intercept [LOOKUP: category] and fetch from EVIDENCE_DB."""
    match = re.search(r"\[LOOKUP:\s*(\w+)\]", text, re.IGNORECASE)
    if match:
        key = match.group(1).lower()
        if key in EVIDENCE_DB:
            return f"[DATABASE VERIFIED]: {EVIDENCE_DB[key]}"
        return f"[DATABASE ERROR]: No records found for '{key}'."
    return None

def main(mock, turns):
    client = make_client(mock=mock)
    agents = [AGENT_A, AGENT_B]
    transcript = [] 

    # Budget is turns + 1 to ensure the Inspector gets the final say
    budget = Budget(max_turns=turns + 1, max_tokens=4000, max_seconds=120)

    # 1. The Interrogation Phase
    while not budget.exhausted() and len([t for t in transcript if t[0] != "SYSTEM"]) < turns:
        # Determine speaker, skipping SYSTEM turns so A and B always alternate
        speaker_idx = len([t for t in transcript if t[0] != "SYSTEM"]) % 2
        speaker = agents[speaker_idx]
        
        messages = [
            {"role": "system", "content": f"{speaker.system_prompt}\nScenario: {TOPIC}"},
            {"role": "user", "content": f"Conversation so far:\n{render(transcript)}\n\nYour turn, {speaker.name}. Reply briefly."}
        ]
        
        reply = client.chat(speaker.model, messages, temperature=speaker.temperature)
        transcript.append((speaker.name, reply.text))
        budget.record(turns=1, tokens=reply.tokens)
        print(f"{speaker.name}: {reply.text}\n")

        # Check for tool usage if the Detective just spoke
        if speaker.name == "Detective_Cross":
            db_response = handle_tool_call(reply.text)
            if db_response:
                transcript.append(("SYSTEM", db_response))
                print(f"\033[93mSYSTEM: {db_response}\033[0m\n")

    # 2. The Verdict Phase
    if not budget.exhausted():
        speaker = AGENT_C
        messages = [
            {"role": "system", "content": f"{speaker.system_prompt}\nScenario: {TOPIC}"},
            {"role": "user", "content": f"Transcript:\n{render(transcript)}\n\nDeliver your final decision."}
        ]
        reply = client.chat(speaker.model, messages, temperature=speaker.temperature)
        budget.record(turns=1, tokens=reply.tokens)
        print(f"--- FINAL VERDICT ---")
        print(f"{speaker.name}: {reply.text}\n")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true", help="use the free offline MockClient")
    p.add_argument("--turns", type=int, default=6, help="hard cap on number of interrogation turns")
    args = p.parse_args()
    main(mock=args.mock, turns=args.turns)