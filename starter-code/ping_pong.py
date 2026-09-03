"""ping_pong.py: AI-Generated Procedural Detective Interrogation System.

Features:
  1. AI Scenario Architect: Generates a unique crime, suspect alibi, and evidence DB.
  2. Tool Use (Stretch Goal): Detective can query the database using [LOOKUP: <category>].
  3. Detective vs. Suspect turn-taking dialogue bounded by Budget.
  4. Chief Inspector / Judge: Verifies if the detective caught the contradiction.
  5. Full transcript output saved to a .txt file with scenario details and answers at the top.

Run:
  python ping_pong.py --mock         # Fast, offline test
  python ping_pong.py --turns 8      # Live local model (Ollama)
"""
import argparse
import datetime
import json
import os
import random
import re

from agents import Agent
from budget import Budget
from llm_client import make_client

# ==============================================================================
# 1. PROCEDURAL SCENARIOS (Used for Mock Mode and LLM Fallback)
# ==============================================================================

FALLBACK_SCENARIOS = [
    {
        "theme": "Museum Diamond Heist",
        "crime_summary": "The 'Star of Midnight' blue diamond was stolen from the gallery vault at 21:30.",
        "suspect_name": "Julian Vance (Chief Curator)",
        "suspect_alibi": "I was having dinner at the 24/7 Grand Bistro across town from 21:00 to 22:30, paying with cash.",
        "evidence_db": {
            "grand_bistro_records": "Grand Bistro was closed all evening on Sunday due to emergency kitchen plumbing repairs.",
            "traffic_cameras": "Traffic cameras show low traffic on Main Avenue between 21:00 and 22:00.",
            "vault_keycard_logs": "Master keycard #04 swiped at Vault Door 2 at 21:28.",
            "security_guard_notes": "Guard on duty reported motion sensor alarm triggered at 21:32."
        },
        "flaw_explanation": "Julian claims he ate dinner at Grand Bistro at 21:30, but Grand Bistro was closed for emergency plumbing repairs.",
        "contradiction_key": "closed"
    },
    {
        "theme": "Space Station Sabotage",
        "is_guilty": True,
        "crime_summary": "The main oxygen valve in Hydroponics was manually severed at 03:15.",
        "suspect_name": "Dr. Nyx (Life Support Engineer)",
        "suspect_alibi": "I was in the Observation Lounge stargazing and watching the solar flare from 02:45 to 03:45.",
        "evidence_db": {
            "observation_lounge_cctv": "Observation blast shutters were automatically sealed for radiation shielding from 01:00 to 05:00. Zero visibility outside.",
            "airlock_pressure_logs": "Normal pressure across all standard airlocks at 03:00.",
            "hydroponics_door_sensor": "Motion registered inside Hydroponics at 03:14.",
            "station_comm_logs": "Automated beacon broadcast transmitted at 03:00."
        },
        "flaw_explanation": "Dr. Nyx claims they watched the solar flare from the Observation Lounge, but the blast shutters were sealed with zero visibility.",
        "contradiction_key": "shutters"
    },
    {
        "theme": "Art Museum Robbery (Framed Witness Case)",
        "is_guilty": False,
        "crime_summary": "The 'Moonlight Serenade' painting was stolen from Gallery 4 at 23:30.",
        "suspect_name": "Lucas Grey (Museum Night Guard)",
        "suspect_alibi": "I was doing my scheduled patrol on the 2nd floor East Wing between 23:15 and 23:45.",
        "evidence_db": {
            "east_wing_motion_sensor": "Motion confirmed on 2nd Floor East Wing continuously from 23:15 to 23:45, matching Lucas's patrol.",
            "security_console_log": "Security alarm in Gallery 4 was overridden using Master Admin credentials belonging to Director Hoffman, not the guard.",
            "emergency_exit_camera": "A figure in a dark trenchcoat carrying a framed canvas exited via the service alley at 23:32.",
            "guard_radio_chatter": "Lucas radioed dispatch at 23:25 reporting all quiet in East Wing."
        },
        "flaw_explanation": "Lucas is completely innocent. East Wing motion sensors confirm his alibi, and the alarm was overridden using Director Hoffman's admin key, not Lucas's guard credentials.",
        "contradiction_key": "innocent"
    }
]


GENRES = [
    "1900s Victorian & Industrial Era Detective Mystery",
    "University of Hamar Exam & Research Fraud Mystery (Hamar, Norway)",
    "The Ultra-Rich Elite Ring Investment Fraud (High Society Scam)",
    "Nordic Forest Cabin Murder Mystery (Dark Norwegian Woods)",
    "High-End Art & Diamond Heist at the Oslo Opera House (Oslo, Norway)",
    "Champion Pedigree Show Dog Kidnapping / Dognapping Ransoms",
    "Formula 1 Racing Telemetry Theft (Monaco Paddock)",
    "Cyberpunk Corporate Data Heist (Neo-Tokyo Megacorp)",
    "Deep Space Station Sabotage (Mars Orbital Station)",
    "High-Stakes Casino Vault Robbery (Las Vegas Strip)",
    "Arctic Biosphere Sample Tampering (Svalbard Research Station)",
    "Luxury Submarine Expedition Poisoning (Pacific Trench)"
]


def robust_json_parser(raw_text: str) -> dict:
    """Repairs and extracts valid JSON even with unescaped quotes or markdown blocks."""
    # 1. Clean markdown codeblocks
    cleaned = re.sub(r"```json\s*", "", raw_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*", "", cleaned)
    
    # 2. Extract outermost JSON object
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in response.")
    
    json_str = match.group(1).strip()
    
    # 3. Clean common LLM formatting glitches (trailing commas, control chars)
    json_str = re.sub(r",\s*\}", "}", json_str)
    json_str = re.sub(r",\s*\]", "]", json_str)
    json_str = json_str.replace("\t", " ")

    return json.loads(json_str)


def resolve_genre(theme_input: str = None) -> str:
    """Matches a user keyword to a preset genre, or uses the custom input directly."""
    if not theme_input or theme_input.strip().lower() in ("random", "any", "none"):
        return random.choice(GENRES)

    clean_input = theme_input.strip().lower()
    for g in GENRES:
        if clean_input in g.lower():
            return g
            
    # If not in presets, allow user's custom theme string!
    return theme_input.strip()


def generate_scenario(client, theme: str = None, force_innocent: bool = False, force_guilty: bool = False, mock: bool = False) -> dict:
    """Generate a scenario via LLM with dynamic guilt/innocence and robust JSON handling."""
    if mock:
        return random.choice(FALLBACK_SCENARIOS)

    chosen_genre = resolve_genre(theme)
    
    if force_innocent:
        is_guilty = False
    elif force_guilty:
        is_guilty = True
    else:
        is_guilty = random.choice([True, False])

    status_str = "GUILTY (The suspect committed the crime and lied in alibi)" if is_guilty else "INNOCENT / FRAMED WITNESS (The suspect did NOT commit the crime; evidence proves innocence)"
    print(f"🎲 Selected Theme Setting: '{chosen_genre}'")
    print(f"🎭 Case Dynamic: {status_str}")

    evidence_instructions = (
        "• Since the suspect is GUILTY: evidence_db should have 2 records providing circumstantial/timeline clues and 1-2 records with hard contradictions proving the alibi is false."
        if is_guilty else
        "• Since the suspect is INNOCENT: evidence_db MUST contain 1-2 clearly EXONERATING records (e.g., CCTV/logs verifying suspect was far away, or forensic proof linking a different perpetrator) that completely clear the suspect."
    )

    prompt = [
        {
            "role": "system",
            "content": (
                f"You are an expert mystery writer. Generate an interrogation case in the genre: '{chosen_genre}'.\n"
                f"CRITICAL REQUIREMENT: The suspect is {status_str}.\n"
                f"{evidence_instructions}\n"
                "Return ONLY a strictly valid JSON object matching this exact schema:\n"
                "{\n"
                '  "theme": "<Theme Title>",\n'
                f'  "is_guilty": {str(is_guilty).lower()},\n'
                '  "crime_summary": "<Crime summary and exact timestamp>",\n'
                '  "suspect_name": "<Name and occupation>",\n'
                '  "suspect_alibi": "<Suspect statement of whereabouts>",\n'
                '  "evidence_db": {\n'
                '    "<category_1>": "<Record fact>",\n'
                '    "<category_2>": "<Record fact that PROVES guilt if guilty, or EXONERATES if innocent>",\n'
                '    "<category_3>": "<Record fact>",\n'
                '    "<category_4>": "<Record fact>"\n'
                "  },\n"
                '  "flaw_explanation": "<Explanation of why evidence proves guilt or proves innocence>",\n'
                '  "contradiction_key": "<key phrase in evidence>"\n'
                "}\n"
                "Do NOT include unescaped quotes inside strings. Output valid JSON only."
            ),
        },
        {
            "role": "user",
            "content": f"Generate the '{chosen_genre}' case now in pure JSON.",
        },
    ]


    # Try generating and parsing with 1 auto-retry
    for attempt in range(2):
        reply = None
        try:
            reply = client.chat("llama3.2:3b", prompt, temperature=0.75)
            if reply and reply.text:
                data = robust_json_parser(reply.text)
                if all(k in data for k in ("theme", "crime_summary", "suspect_name", "suspect_alibi", "evidence_db", "flaw_explanation")):
                    data["is_guilty"] = is_guilty
                    return data
        except Exception:
            if attempt == 0 and reply and getattr(reply, "text", None):
                prompt.append({"role": "assistant", "content": reply.text})
                prompt.append({"role": "user", "content": "Syntax error in JSON. Output strictly valid JSON without any commentary or unescaped quotes."})

    print("⚠️ Custom JSON generation failed; loading curated scenario.")
    return [s for s in FALLBACK_SCENARIOS if s["is_guilty"] == is_guilty][0]



def extract_and_execute_tool(message_text: str, evidence_db: dict):
    """Intercepts [LOOKUP: <category>] and returns (matched_key, matched_val, dispatch_str)."""
    match = re.search(r"\[LOOKUP:\s*([^\]]+)\]", message_text, re.IGNORECASE)
    if not match:
        return None, None, ""

    raw_query = match.group(1).strip()
    norm_query = re.sub(r"[\s_\-]+", "", raw_query.lower())
    
    for key, value in evidence_db.items():
        norm_key = re.sub(r"[\s_\-]+", "", key.lower())
        if norm_query in norm_key or norm_key in norm_query or norm_query == norm_key:
            return key, value, f"\n[DATABASE DISPATCH]: Verified Record for '{key}': \"{value}\""
            
    return None, None, f"\n[DATABASE DISPATCH]: No record found for '{raw_query}'."


def clean_agent_reply(text: str, speaker_name: str) -> str:
    """Removes leaked speaker labels, parenthetical internal thoughts, and redundant whitespace."""
    if not text:
        return ""
    cleaned = re.sub(rf"^\s*{re.escape(speaker_name)}\s*:\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\([^\)]*(?:looking for|inconsistenc|verifying|thought process|motive|trying to|note to self|inner thought)[^\)]*\)", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()



def evaluate_suspect_admission(client, suspect_speech: str, mock: bool = False) -> bool:
    """Robust 3-layer confession evaluator: Token Tag -> Fast Keywords -> Semantic Classifier."""
    # Layer 1: Explicit state tag
    if "[STATE: CONFESSED]" in suspect_speech.upper():
        return True

    # Layer 2: Fast-path common surrender signals
    lower = suspect_speech.lower()
    fast_signals = [
        "i confess", "you caught me", "alright, i lied", "i did it",
        "covered my tracks", "i admit", "i stole", "it was me",
        "i am guilty", "take me in", "you got me", "i'm ruined",
        "i broke into", "i had no choice"
    ]
    if any(sig in lower for sig in fast_signals):
        return True

    if mock:
        return False

    # Layer 3: Semantic LLM Evaluator for ambiguous/novel admissions
    eval_prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert legal auditor. Analyze the suspect's statement in an interrogation.\n"
                "Did the suspect concede defeat, admit guilt, give up their defense, or acknowledge being caught?\n"
                "Answer strictly with one word: 'YES' or 'NO'."
            ),
        },
        {"role": "user", "content": f"Suspect statement: \"{suspect_speech}\""},
    ]
    try:
        res = client.chat("llama3.2:3b", eval_prompt, temperature=0.0)
        return "YES" in res.text.strip().upper()
    except Exception:
        return False


# ==============================================================================
# 3. MAIN DIALOGUE & INTERROGATION LOOP
# ==============================================================================

def main(mock: bool, turns: int, theme: str = None, force_innocent: bool = False, force_guilty: bool = False):
    client = make_client(mock=mock)


    print("Generating crime scenario...")
    scenario = generate_scenario(client, theme=theme, force_innocent=force_innocent, force_guilty=force_guilty, mock=mock)

    is_guilty = scenario.get("is_guilty", True)
    db_categories = list(scenario["evidence_db"].keys())
    categories_str = ", ".join(f"`[LOOKUP: {k}]`" for k in db_categories)

    # 1. Detective Persona (Crisp, direct, truth-seeking investigator)
    detective = Agent(
        name="Detective Cross",
        system_prompt=(
            f"You are Detective Cross interrogating {scenario['suspect_name']} regarding: {scenario['crime_summary']}.\n"
            f"JUDICIAL ROLE: You do NOT know in advance if the suspect is GUILTY or INNOCENT. Seek objective truth.\n"
            f"CONVERSATION RULES:\n"
            f"- Speak directly to the suspect in 2 to 3 sentences maximum. Be concise and sharp.\n"
            f"- NEVER write parenthetical thoughts, inner monologue, or notes like '(I am checking...)' or '(Looking for inconsistencies)'. Spoken dialogue ONLY.\n"
            f"- Early Turns: Inquire calmly, probe their alibi, and test their claims against police records.\n"
            f"- Cite only verified records in your binder.\n"
            f"- If evidence proves guilt, demand confession [DECISION: ARREST]. If cleared, declare [DECISION: EXONERATE]."
        ),
        temperature=0.3,
    )

    # 2. Suspect Persona (Guilty Culprit or Innocent Framed Witness)
    if is_guilty:
        suspect_prompt_text = (
            f"You are {scenario['suspect_name']}, the prime suspect in: {scenario['crime_summary']}.\n"
            f"YOUR TRUE STATUS: YOU COMMITTED THIS CRIME. Cover alibi: \"{scenario['suspect_alibi']}\"\n"
            f"RULES:\n"
            f"- Keep responses crisp: 2 to 3 sentences max. Do NOT write long monologues.\n"
            f"- Early Rounds: Defend your alibi with believable counter-explanations. Do NOT surrender immediately on the first turn!\n"
            f"- Confession Rule: Only confess ('You caught me, I confess') after the detective has presented at least TWO verified facts that leave you zero excuses."
        )
    else:
        suspect_prompt_text = (
            f"You are {scenario['suspect_name']}, questioned in: {scenario['crime_summary']}.\n"
            f"YOUR TRUE STATUS: YOU ARE 100% INNOCENT. Your truth: \"{scenario['suspect_alibi']}\"\n"
            f"RULES:\n"
            f"- Keep responses crisp: 2 to 3 sentences max.\n"
            f"- Maintain your innocence with calm confidence and honesty. You will NEVER confess to a crime you didn't commit."
        )

    suspect = Agent(
        name=scenario["suspect_name"],
        system_prompt=suspect_prompt_text,
        temperature=0.4,
    )

    # 3. Judge / Chief Inspector (Fact-Checking & Judicial Accuracy Auditor)
    judge = Agent(
        name="Chief Inspector Ward",
        system_prompt=(
            f"You are Chief Inspector Ward auditing Detective Cross's case regarding {scenario['suspect_name']}.\n"
            f"Ground Truth Status: Suspect is {'GUILTY (Perpetrator)' if is_guilty else 'INNOCENT (Framed Witness)'}.\n"
            f"Ground Truth Evidence: {scenario['flaw_explanation']}\n\n"
            f"Grading Criteria:\n"
            f"- Grade A (Justice Served): Detective made correct verdict supported by facts.\n"
            f"- Grade F (Miscarriage of Justice): Wrong verdict (exonerating a guilty suspect or falsely accusing an innocent witness).\n"
            f"- Grade C (Unsolved): Inconclusive / insufficient proof.\n"
            f"STYLE: Output strictly concise evaluation. Do NOT recite the grading rubric or repeat paragraphs."
        ),
        temperature=0.2,
    )


    agents = [detective, suspect]
    transcript = []  # list of tuples: (speaker, text)
    unlocked_evidence = {}  # Python-level ground truth inventory

    print("=" * 65)
    print(f"🕵️  CASE FILE: {scenario['theme'].upper()} 🕵️")
    print(f"Incident: {scenario['crime_summary']}")
    print(f"Suspect : {scenario['suspect_name']}")
    print("=" * 65 + "\n")

    budget = Budget(max_turns=turns, max_tokens=8000, max_seconds=240)

    while not budget.exhausted():
        turn_idx = len([t for t in transcript if not t[0].startswith("DATABASE")])
        speaker = agents[turn_idx % 2]

        # Build clean dialogue history for context
        dialogue_history = []
        for name, text in transcript:
            dialogue_history.append(f"{name}: {text}")
        history_text = "\n\n".join(dialogue_history) if dialogue_history else "(No dialogue yet. Interrogation starting.)"

        if speaker == detective:
            if turn_idx == 0:
                # Turn 0: Opening question
                prompt_messages = [
                    {"role": "system", "content": detective.system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Begin the interrogation. Introduce yourself to {suspect.name}, state the incident ({scenario['crime_summary']}), "
                            f"and ask them where they were and what they were doing at that exact time."
                        ),
                    },
                ]
                reply = client.chat(detective.model, prompt_messages, temperature=detective.temperature)
                reply_text = clean_agent_reply(reply.text, detective.name)
                transcript.append((detective.name, reply_text))
                budget.record(turns=1, tokens=reply.tokens)
                print(f"[{detective.name}]:\n{reply_text}\n")
            else:
                # Calculate unexamined leads
                unexamined_categories = [k for k in db_categories if k not in unlocked_evidence]
                unexamined_str = ", ".join(f"`[LOOKUP: {k}]`" for k in unexamined_categories) if unexamined_categories else "None (All leads investigated)"

                # ReAct Phase 1: Decide on Evidence Lookup
                tool_decision_prompt = [
                    {
                        "role": "system",
                        "content": (
                            f"You are Detective Cross. Review the suspect's latest statement:\n\n"
                            f"{history_text}\n\n"
                            f"UNEXAMINED LEADS (Not yet checked): {unexamined_str}\n"
                            f"ALREADY CHECKED: {list(unlocked_evidence.keys())}\n"
                            f"Investigative Rule: Pick an unexamined category to verify facts!\n"
                            f"Output ONLY `[LOOKUP: <category>]` or `[NO_LOOKUP]`."
                        ),
                    },
                    {"role": "user", "content": "What unexamined evidence category do you want to query now?"},
                ]
                tool_choice_resp = client.chat(detective.model, tool_decision_prompt, temperature=0.3)
                budget.record(turns=0, tokens=tool_choice_resp.tokens)
                
                matched_k, matched_v, tool_result = extract_and_execute_tool(tool_choice_resp.text, scenario["evidence_db"])
                
                # Auto-Retry if lookup failed
                if not matched_k and unexamined_categories:
                    retry_prompt = [
                        {"role": "system", "content": f"Query failed. You MUST pick strictly from unexamined leads: {unexamined_str}"},
                        {"role": "user", "content": "Output a valid `[LOOKUP: <category>]` now."},
                    ]
                    retry_resp = client.chat(detective.model, retry_prompt, temperature=0.2)
                    budget.record(turns=0, tokens=retry_resp.tokens)
                    matched_k, matched_v, tool_result = extract_and_execute_tool(retry_resp.text, scenario["evidence_db"])

                # If successful, add to Python's unlocked evidence inventory
                if matched_k:
                    unlocked_evidence[matched_k] = matched_v
                    transcript.append(("DATABASE SYSTEM", tool_result.strip()))
                    print(f"\033[93m{tool_result}\033[0m")


                # Format current evidence inventory
                if unlocked_evidence:
                    verified_block = "VERIFIED EVIDENCE IN YOUR BINDER:\n" + "\n".join(f"• [{k}]: \"{v}\"" for k, v in unlocked_evidence.items())
                else:
                    verified_block = "VERIFIED EVIDENCE IN YOUR BINDER: None yet."

                # ReAct Phase 2: Interrogate using verified proof and decide Arrest vs Exoneration
                speech_prompt = [
                    {"role": "system", "content": detective.system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Transcript so far:\n{history_text}\n\n"
                            f"{verified_block}\n\n"
                            f"Your turn, Detective Cross. Interrogate {suspect.name}.\n"
                            f"CRITICAL RULES:\n"
                            f"1. 2 to 3 sentences maximum. Be direct and punchy.\n"
                            f"2. Output SPOKEN DIALOGUE ONLY. Do NOT write your thoughts, commentary, or parenthetical notes.\n"
                            f"3. Probe their claims or confront them with verified contradictions.\n"
                            f"4. If evidence strongly links them to the crime, demand confession [DECISION: ARREST]. If cleared, declare [DECISION: EXONERATE]."
                        ),
                    },
                ]
                reply = client.chat(detective.model, speech_prompt, temperature=detective.temperature)
                reply_text = clean_agent_reply(reply.text, detective.name)
                transcript.append((detective.name, reply_text))
                budget.record(turns=1, tokens=reply.tokens)
                print(f"[{detective.name}]:\n{reply_text}\n")

                # Check if detective exonerated suspect
                if any(phrase in reply_text.lower() for phrase in ["cleared of suspicion", "cleared of all suspicion", "you are free to go", "[decision: exonerate]"]):
                    print("🕊️ [ALERT]: Detective Cross recognized innocence and exonerated the suspect! 🕊️\n")
                    budget.stop("goal_reached")

        else:
            # Suspect Turn
            suspect_prompt = [
                {"role": "system", "content": suspect.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Transcript so far:\n{history_text}\n\n"
                        f"Detective Cross just addressed you. Give your spoken response in 2-3 sentences max. "
                        f"Match your true status ({'GUILTY' if is_guilty else 'INNOCENT'}). "
                        f"Do NOT write long monologues. Only confess if cornered by multiple verified facts."
                    ),
                },
            ]
            reply = client.chat(suspect.model, suspect_prompt, temperature=suspect.temperature)
            reply_text = clean_agent_reply(reply.text, suspect.name)
            transcript.append((suspect.name, reply_text))
            budget.record(turns=1, tokens=reply.tokens)
            print(f"[{suspect.name}]:\n{reply_text}\n")

            # Check if suspect surrendered, confessed, or conceded defeat
            if is_guilty and evaluate_suspect_admission(client, reply_text, mock=mock):
                print("🚨 [ALERT]: Suspect cracked and surrendered! Interrogation complete. 🚨\n")
                budget.stop("goal_reached")


    # ==============================================================================
    # 4. FINAL SUSPECT RESPONSE (GUARANTEES SUSPECT HAS THE LAST WORD)
    # ==============================================================================
    if transcript and transcript[-1][0] == detective.name:
        history_summary = "\n\n".join(f"{n}: {t}" for n, t in transcript)
        suspect_final_prompt = [
            {"role": "system", "content": suspect.system_prompt},
            {
                "role": "user",
                "content": (
                    f"Dialogue so far:\n{history_summary}\n\n"
                    f"Detective Cross gave their closing statement. Give your final reaction in 1-2 sentences."
                ),
            },
        ]
        final_reply = client.chat(suspect.model, suspect_final_prompt, temperature=suspect.temperature)
        final_text = clean_agent_reply(final_reply.text, suspect.name)
        transcript.append((suspect.name, final_text))
        budget.record(turns=1, tokens=final_reply.tokens)
        print(f"[{suspect.name} (Closing Response)]:\n{final_text}\n")

    # ==============================================================================
    # 5. DETECTIVE CROSS FORMAL VERDICT SUBMISSION (LOCKED ANSWER)
    # ==============================================================================
    print("=" * 65)
    print("📝  DETECTIVE CROSS — FORMAL CASE INDICTMENT & VERDICT  📝")
    print("=" * 65 + "\n")

    full_dialogue_text = "\n\n".join(f"{name}: {text}" for name, text in transcript)
    
    verdict_prompt = [
        {"role": "system", "content": detective.system_prompt},
        {
            "role": "user",
            "content": (
                f"The interrogation has ended. Here is your final verified evidence binder:\n{verified_block}\n\n"
                f"Full Interrogation Transcript:\n{full_dialogue_text}\n\n"
                f"TASK: Submit your official locked verdict on {suspect.name}.\n"
                f"DECISION LOGIC:\n"
                f"- If verified records place them at the scene, break their alibi, or find stolen goods in their possession, you MUST choose [GUILTY - ARREST].\n"
                f"- Only choose [INNOCENT - EXONERATE] if verified evidence physically proves they were elsewhere or cleared of the crime.\n\n"
                f"FORMAT STRICTLY AS (under 3 sentences total):\n"
                f"FINAL VERDICT: [GUILTY - ARREST] or [INNOCENT - EXONERATE]\n"
                f"KEY EVIDENCE: Exactly 1-2 sentences citing the verified facts."
            ),
        },
    ]
    detective_verdict_resp = client.chat(detective.model, verdict_prompt, temperature=0.1)
    budget.record(turns=0, tokens=detective_verdict_resp.tokens)
    print(detective_verdict_resp.text)
    print("\n" + "=" * 65)

    # ==============================================================================
    # 5. CHIEF INSPECTOR JUDICIAL AUDIT & VERDICT
    # ==============================================================================
    print("⚖️  CHIEF INSPECTOR WARD — OFFICIAL JUDICIAL AUDIT  ⚖️")
    print("=" * 65 + "\n")

    judge_messages = [
        {"role": "system", "content": judge.system_prompt},
        {
            "role": "user",
            "content": (
                f"Case Summary: {scenario['crime_summary']}\n"
                f"Ground Truth: Suspect was {'GUILTY' if is_guilty else 'INNOCENT'}\n"
                f"True Evidence: {scenario['flaw_explanation']}\n\n"
                f"Detective's Final Locked Verdict:\n{detective_verdict_resp.text}\n\n"
                f"Full Interrogation Transcript:\n{full_dialogue_text}\n\n"
                f"TASK: Audit Detective Cross. Do NOT recite the grading rubric rules or repeat yourself.\n"
                f"Output STRICTLY in this format:\n"
                f"GRADE: <A / B / C / F>\n"
                f"CASE OUTCOME: <SOLVED (Correct Verdict) / UNSOLVED / MISCARRIAGE OF JUSTICE>\n"
                f"GROUNDING AUDIT: <PASSED (100% Grounded) / FAILED>\n"
                f"AUDIT SUMMARY: Exactly 2-3 sentences explaining whether Cross correctly solved the case based on the ground truth."
            ),
        },
    ]

    judge_reply = client.chat(judge.model, judge_messages, temperature=judge.temperature)
    budget.record(turns=1, tokens=judge_reply.tokens)
    print(judge_reply.text)
    print("\n" + "=" * 65)


    # ==============================================================================
    # 6. SAVE RUN TO A STRUCTURED .TXT FILE (WITH SCENARIO & ANSWERS AT TOP)
    # ==============================================================================
    if mock:
        print("[Mock Mode: Skipping .txt file creation.]\n")
        return

    os.makedirs("transcripts", exist_ok=True)
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clean_theme = re.sub(r"[^\w\s-]", "", scenario.get("theme", "Case")).strip().replace(" ", "_")
    txt_filename = f"transcripts/{timestamp_str}_{clean_theme}.txt"

    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write("=" * 75 + "\n")
        f.write("                   OFFICIAL INVESTIGATION REPORT\n")
        f.write("=" * 75 + "\n\n")
        f.write(f"DATE & TIME      : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"MODEL USED       : {detective.model}\n")
        f.write(f"EXECUTION MODE   : {'MockClient (Offline)' if mock else 'OllamaClient (Live Local Model)'}\n")
        f.write(f"TEMPERATURES     : Detective={detective.temperature}, Suspect={suspect.temperature}, Judge={judge.temperature}\n")
        f.write(f"CASE THEME       : {scenario.get('theme', 'N/A')}\n")
        f.write(f"SUSPECT STATUS   : {'GUILTY (Perpetrator)' if is_guilty else 'INNOCENT (Framed Witness)'}\n")
        f.write(f"CRIME SUMMARY    : {scenario.get('crime_summary', 'N/A')}\n")
        f.write(f"SUSPECT NAME     : {scenario.get('suspect_name', 'N/A')}\n")
        f.write(f"SUSPECT ALIBI    : {scenario.get('suspect_alibi', 'N/A')}\n\n")
        f.write("-" * 75 + "\n")
        f.write("GROUND TRUTH / SOLUTION KEY:\n")
        f.write(f"  {scenario.get('flaw_explanation', 'N/A')}\n")
        f.write("-" * 75 + "\n\n")
        f.write("AVAILABLE EVIDENCE DATABASE RECORDS:\n")
        for cat, val in scenario.get("evidence_db", {}).items():
            f.write(f"  • [{cat}]: {val}\n")
        f.write("\n" + "=" * 75 + "\n")
        f.write("                      INTERROGATION TRANSCRIPT\n")
        f.write("=" * 75 + "\n\n")

        for turn_num, (speaker_name, message_content) in enumerate(transcript, start=1):
            f.write(f"[TURN {turn_num:02d}] {speaker_name}:\n")
            f.write(f"{message_content}\n\n")

        f.write("=" * 75 + "\n")
        f.write("             DETECTIVE CROSS FINAL LOCKED VERDICT\n")
        f.write("=" * 75 + "\n\n")
        f.write(detective_verdict_resp.text + "\n\n")

        f.write("=" * 75 + "\n")
        f.write("                  CHIEF INSPECTOR FINAL VERDICT\n")
        f.write("=" * 75 + "\n\n")
        f.write(judge_reply.text + "\n\n")
        f.write("-" * 75 + "\n")
        f.write(f"BUDGET METRICS: {budget.turns} turns | {budget.tokens} tokens | {budget.elapsed:.2f}s | Stop: {budget.stop_reason}\n")
        f.write("=" * 75 + "\n")

    print(f"📁 Full case report saved to: {txt_filename}\n")



if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true", help="use offline mock LLM client")
    p.add_argument("--turns", type=int, default=10, help="number of interrogation turns (default: 10)")
    p.add_argument(
        "--theme",
        type=str,
        default=None,
        help="choose theme/keyword (e.g. hamar, oslo, 1900s, forest, ring, dog, casino, f1) or custom freeform string",
    )
    p.add_argument("--innocent", action="store_true", help="force an innocent framed witness scenario")
    p.add_argument("--guilty", action="store_true", help="force a guilty suspect scenario")
    args = p.parse_args()
    main(mock=args.mock, turns=args.turns, theme=args.theme, force_innocent=args.innocent, force_guilty=args.guilty)




