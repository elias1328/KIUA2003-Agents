"""benchmark_suite.py: Automated Empirical Benchmark & Evaluation Suite for Multi-Agent Interrogations.

Runs high-volume parametric sweep experiments across:
- Turn limits (e.g. 4, 6, 8, 10, 12)
- Detective and Suspect temperatures
- Guilty vs. Innocent Framed Witness dynamics
- Diverse genres and procedural scenarios

Features:
- Robust HTTP retry logic to prevent Ollama timeout crashes
- Real-time disk streaming (results auto-saved to CSV after every round)
- Comprehensive Turn-by-Turn breakdown and confusion matrix
- Markdown and CSV report generation
"""
import argparse
import csv
import datetime
import json
import os
import random
import re
import sys
import time

from agents import Agent
from budget import Budget
from llm_client import make_client
from ping_pong import (
    FALLBACK_SCENARIOS,
    GENRES,
    evaluate_suspect_admission,
    extract_and_execute_tool,
    generate_scenario,
    resolve_genre,
    robust_json_parser,
)


def safe_chat(client, model: str, messages: list, temperature: float = 0.3, max_retries: int = 2):
    """Executes client.chat with auto-retry and timeout tolerance."""
    for attempt in range(max_retries):
        try:
            return client.chat(model, messages, temperature=temperature)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2)


def clean_agent_reply(text: str, speaker_name: str) -> str:
    """Removes leaked speaker labels, parenthetical internal thoughts, and redundant whitespace."""
    if not text:
        return ""
    cleaned = re.sub(rf"^\s*{re.escape(speaker_name)}\s*:\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\([^\)]*(?:looking for|inconsistenc|verifying|thought process|motive|trying to|note to self|inner thought)[^\)]*\)", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def run_single_investigation(
    client,
    theme: str = None,
    max_turns: int = 10,
    det_temp: float = 0.3,
    susp_temp: float = 0.4,
    force_innocent: bool = False,
    force_guilty: bool = False,
    mock: bool = False,
) -> dict:
    """Executes a complete 5-step multi-agent interrogation run and returns structured metrics."""
    start_time = time.time()
    
    # 1. Procedural Scenario Generation
    scenario = generate_scenario(
        client,
        theme=theme,
        force_innocent=force_innocent,
        force_guilty=force_guilty,
        mock=mock,
    )
    is_guilty = scenario.get("is_guilty", True)
    db_categories = list(scenario["evidence_db"].keys())

    # 2. Setup Agents
    detective = Agent(
        name="Detective Cross",
        system_prompt=(
            f"You are Detective Cross interrogating {scenario['suspect_name']} regarding: {scenario['crime_summary']}.\n"
            f"JUDICIAL ROLE: You do NOT know in advance if the suspect is GUILTY or INNOCENT. Seek objective truth.\n"
            f"CONVERSATION RULES:\n"
            f"- Speak directly to the suspect in 2 to 3 sentences maximum. Be concise and sharp.\n"
            f"- NEVER write parenthetical thoughts, inner monologue, or notes like '(I am checking...)'. Spoken dialogue ONLY.\n"
            f"- Early Turns: Inquire calmly, probe their alibi, and test their claims against police records.\n"
            f"- Cite only verified records in your binder.\n"
            f"- If evidence proves guilt, demand confession [DECISION: ARREST]. If cleared, declare [DECISION: EXONERATE]."
        ),
        temperature=det_temp,
    )

    if is_guilty:
        suspect_prompt_text = (
            f"You are {scenario['suspect_name']}, the prime suspect in: {scenario['crime_summary']}.\n"
            f"YOUR TRUE STATUS: YOU COMMITTED THIS CRIME. Cover alibi: \"{scenario['suspect_alibi']}\"\n"
            f"RULES:\n"
            f"- Keep responses crisp: 2 to 3 sentences max. Do NOT write long monologues.\n"
            f"- Early Rounds: Defend your alibi with believable counter-explanations. Do NOT surrender immediately!\n"
            f"- Confession Rule: Only confess ('You caught me, I confess') after the detective presents at least TWO verified facts leaving you zero excuses."
        )
    else:
        suspect_prompt_text = (
            f"You are {scenario['suspect_name']}, questioned in: {scenario['crime_summary']}.\n"
            f"YOUR TRUE STATUS: YOU ARE 100% INNOCENT. Truth: \"{scenario['suspect_alibi']}\"\n"
            f"RULES:\n"
            f"- Keep responses crisp: 2 to 3 sentences max.\n"
            f"- Maintain your innocence with calm confidence and honesty. You will NEVER confess to something you didn't do."
        )

    suspect = Agent(
        name=scenario["suspect_name"],
        system_prompt=suspect_prompt_text,
        temperature=susp_temp,
    )

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
    transcript = []
    unlocked_evidence = {}
    budget = Budget(max_turns=max_turns, max_tokens=8000, max_seconds=180)
    suspect_confessed = False
    detective_exonerated = False

    # 3. Interrogation Loop
    while not budget.exhausted():
        turn_idx = len([t for t in transcript if not t[0].startswith("DATABASE")])
        speaker = agents[turn_idx % 2]

        dialogue_history = [f"{n}: {t}" for n, t in transcript]
        history_text = "\n\n".join(dialogue_history) if dialogue_history else "(Interrogation starting.)"

        if speaker == detective:
            if turn_idx == 0:
                prompt = [
                    {"role": "system", "content": detective.system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Begin the interrogation. Introduce yourself to {suspect.name}, state the incident ({scenario['crime_summary']}), "
                            f"and ask them where they were and what they were doing at that exact time."
                        ),
                    },
                ]
                reply = safe_chat(client, detective.model, prompt, temperature=detective.temperature)
                transcript.append((detective.name, reply.text.strip()))
                budget.record(turns=1, tokens=reply.tokens)
            else:
                unexamined_categories = [k for k in db_categories if k not in unlocked_evidence]
                unexamined_str = ", ".join(f"`[LOOKUP: {k}]`" for k in unexamined_categories) if unexamined_categories else "None"

                tool_prompt = [
                    {
                        "role": "system",
                        "content": (
                            f"You are Detective Cross. Review the suspect's statement:\n{history_text}\n"
                            f"UNEXAMINED LEADS: {unexamined_str}\n"
                            f"Output ONLY `[LOOKUP: <category>]` or `[NO_LOOKUP]`."
                        ),
                    },
                    {"role": "user", "content": "What unexamined evidence category do you want to query?"},
                ]
                tool_resp = safe_chat(client, detective.model, tool_prompt, temperature=0.3)
                budget.record(turns=0, tokens=tool_resp.tokens)
                matched_k, matched_v, tool_result = extract_and_execute_tool(tool_resp.text, scenario["evidence_db"])

                if matched_k:
                    unlocked_evidence[matched_k] = matched_v
                    transcript.append(("DATABASE SYSTEM", tool_result.strip()))


                verified_block = "VERIFIED EVIDENCE IN BINDER:\n" + "\n".join(f"• [{k}]: \"{v}\"" for k, v in unlocked_evidence.items()) if unlocked_evidence else "VERIFIED EVIDENCE: None yet."

                speech_prompt = [
                    {"role": "system", "content": detective.system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Transcript:\n{history_text}\n\n{verified_block}\n\n"
                            f"Interrogate {suspect.name}. CRITICAL: 2-3 sentences max. Output spoken dialogue ONLY (no parenthetical thoughts). "
                            f"If evidence strongly links them to the crime, demand confession [DECISION: ARREST]. "
                            f"If evidence clears them, declare them cleared [DECISION: EXONERATE]."
                        ),
                    },
                ]
                reply = safe_chat(client, detective.model, speech_prompt, temperature=detective.temperature)
                reply_text = clean_agent_reply(reply.text, detective.name)
                transcript.append((detective.name, reply_text))
                budget.record(turns=1, tokens=reply.tokens)

                if any(phrase in reply_text.lower() for phrase in ["cleared of suspicion", "cleared of all suspicion", "you are free to go", "[decision: exonerate]"]):
                    detective_exonerated = True
                    budget.stop("goal_reached")

        else:
            suspect_prompt = [
                {"role": "system", "content": suspect.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Transcript:\n{history_text}\n\n"
                        f"Detective Cross addressed you. Respond in 2-3 sentences max. Do NOT write long monologues. "
                        f"If guilty, defend yourself with plausible excuses; only confess if cornered by multiple verified facts."
                    ),
                },
            ]
            reply = safe_chat(client, suspect.model, suspect_prompt, temperature=suspect.temperature)
            reply_text = clean_agent_reply(reply.text, suspect.name)
            transcript.append((suspect.name, reply_text))
            budget.record(turns=1, tokens=reply.tokens)

            if is_guilty and evaluate_suspect_admission(client, reply_text, mock=mock):
                suspect_confessed = True
                budget.stop("goal_reached")

    # 4. Final Suspect Response (Guaranteed Last Word)
    if transcript and transcript[-1][0] == detective.name:
        suspect_final_prompt = [
            {"role": "system", "content": suspect.system_prompt},
            {"role": "user", "content": "Detective Cross gave their closing statement. Give your final 1-2 sentence response."},
        ]
        final_reply = safe_chat(client, suspect.model, suspect_final_prompt, temperature=suspect.temperature)
        transcript.append((suspect.name, clean_agent_reply(final_reply.text, suspect.name)))
        budget.record(turns=1, tokens=final_reply.tokens)

    # 5. Detective Cross Formal Locked Indictment
    full_dialogue_text = "\n\n".join(f"{name}: {text}" for name, text in transcript)
    verdict_prompt = [
        {"role": "system", "content": detective.system_prompt},
        {
            "role": "user",
            "content": (
                f"Transcript:\n{full_dialogue_text}\n\n"
                f"Submit your official locked verdict on {suspect.name}.\n"
                f"DECISION LOGIC:\n"
                f"- If verified records place them at the scene, break their alibi, or find stolen goods in their possession, you MUST choose [GUILTY - ARREST].\n"
                f"- Only choose [INNOCENT - EXONERATE] if verified evidence physically proves they were elsewhere or cleared.\n\n"
                f"FORMAT STRICTLY AS (under 3 sentences total):\n"
                f"1. FINAL VERDICT: [GUILTY - ARREST] or [INNOCENT - EXONERATE]\n"
                f"2. KEY EVIDENCE: 1-2 sentences citing verified facts."
            ),
        },
    ]
    det_verdict_resp = safe_chat(client, detective.model, verdict_prompt, temperature=0.1)
    det_verdict_text = det_verdict_resp.text.strip()

    det_chose_guilty = "[GUILTY" in det_verdict_text.upper() or "ARREST" in det_verdict_text.upper() or "GUILTY" in det_verdict_text.upper()
    det_chose_innocent = "[INNOCENT" in det_verdict_text.upper() or "EXONERATE" in det_verdict_text.upper() or "INNOCENT" in det_verdict_text.upper()

    if det_chose_guilty and not det_chose_innocent:
        locked_verdict = "GUILTY_ARREST"
    elif det_chose_innocent and not det_chose_guilty:
        locked_verdict = "INNOCENT_EXONERATE"
    else:
        locked_verdict = "GUILTY_ARREST" if "guilty" in det_verdict_text.lower() else "INNOCENT_EXONERATE"

    # 6. Chief Inspector Audit & Grading
    judge_prompt = [
        {"role": "system", "content": judge.system_prompt},
        {
            "role": "user",
            "content": (
                f"Ground Truth: Suspect is {'GUILTY' if is_guilty else 'INNOCENT'}\n"
                f"True Flaw: {scenario['flaw_explanation']}\n"
                f"Detective Locked Verdict:\n{det_verdict_text}\n\n"
                f"Transcript:\n{full_dialogue_text}\n\n"
                f"Audit Detective Cross. Do NOT recite the rubric rules or repeat yourself.\n"
                f"Output strictly:\n"
                f"GRADE: <A / B / C / F>\n"
                f"CASE OUTCOME: <SOLVED (Correct Verdict) / UNSOLVED / MISCARRIAGE OF JUSTICE>\n"
                f"AUDIT SUMMARY: Exactly 2-3 sentences explaining whether Cross correctly solved the case."
            ),
        },
    ]
    judge_resp = safe_chat(client, judge.model, judge_prompt, temperature=0.2)
    judge_text = judge_resp.text.strip()


    grade_match = re.search(r"Grade[:\s]+([ABCF])", judge_text, re.IGNORECASE)
    if grade_match:
        grade = grade_match.group(1).upper()
    elif "GRADE A" in judge_text.upper():
        grade = "A"
    elif "GRADE B" in judge_text.upper():
        grade = "B"
    elif "GRADE C" in judge_text.upper():
        grade = "C"
    elif "GRADE F" in judge_text.upper():
        grade = "F"
    else:
        grade = "A" if (is_guilty and locked_verdict == "GUILTY_ARREST") or (not is_guilty and locked_verdict == "INNOCENT_EXONERATE") else "F"

    # 7. Classify Judicial Confusion Matrix: TP, TN, FP, FN
    if is_guilty:
        if locked_verdict == "GUILTY_ARREST" and (suspect_confessed or grade in ("A", "B")):
            classification = "TP"  # True Positive
        else:
            classification = "FN"  # False Negative (Escaped)
    else:
        if locked_verdict == "INNOCENT_EXONERATE" or detective_exonerated:
            classification = "TN"  # True Negative
        else:
            classification = "FP"  # False Positive (Wrongful conviction)

    elapsed = time.time() - start_time
    total_tokens = budget.tokens + det_verdict_resp.tokens + judge_resp.tokens

    return {
        "theme": scenario.get("theme", "Mystery"),
        "ground_truth": "GUILTY" if is_guilty else "INNOCENT",
        "max_turns": max_turns,
        "turns_used": budget.turns,
        "det_temp": det_temp,
        "susp_temp": susp_temp,
        "detective_verdict": locked_verdict,
        "suspect_confessed": suspect_confessed,
        "detective_exonerated": detective_exonerated,
        "judge_grade": grade,
        "classification": classification,
        "evidence_unlocked": len(unlocked_evidence),
        "total_evidence": len(db_categories),
        "total_tokens": total_tokens,
        "elapsed_seconds": round(elapsed, 2),
        "stop_reason": budget.stop_reason or "max_turns",
    }


def print_benchmark_summary(results: list, output_csv: str = "benchmark_results.csv", output_md: str = "benchmark_summary.md"):
    """Computes statistical metrics across all runs and prints/saves comprehensive tables."""
    total_runs = len(results)
    if total_runs == 0:
        print("No results to aggregate.")
        return

    tp = sum(1 for r in results if r["classification"] == "TP")
    tn = sum(1 for r in results if r["classification"] == "TN")
    fp = sum(1 for r in results if r["classification"] == "FP")
    fn = sum(1 for r in results if r["classification"] == "FN")

    guilty_cases = sum(1 for r in results if r["ground_truth"] == "GUILTY")
    innocent_cases = sum(1 for r in results if r["ground_truth"] == "INNOCENT")

    accuracy = (tp + tn) / total_runs * 100
    conviction_rate = (tp / guilty_cases * 100) if guilty_cases > 0 else 0.0
    escape_rate = (fn / guilty_cases * 100) if guilty_cases > 0 else 0.0
    exoneration_rate = (tn / innocent_cases * 100) if innocent_cases > 0 else 0.0
    wrongful_conviction_rate = (fp / innocent_cases * 100) if innocent_cases > 0 else 0.0

    avg_turns = sum(r["turns_used"] for r in results) / total_runs
    avg_tokens = sum(r["total_tokens"] for r in results) / total_runs
    avg_time = sum(r["elapsed_seconds"] for r in results) / total_runs
    early_halts = sum(1 for r in results if r["stop_reason"] == "goal_reached") / total_runs * 100

    grades = {"A": 0, "B": 0, "C": 0, "F": 0}
    for r in results:
        g = r["judge_grade"]
        grades[g] = grades.get(g, 0) + 1

    turns_groups = {}
    for r in results:
        t = r["max_turns"]
        turns_groups.setdefault(t, []).append(r)

    print("\n" + "=" * 78)
    print("           📊 MULTI-AGENT INTERROGATION BENCHMARK RESULTS 📊")
    print("=" * 78)
    print(f"Total Iterations Executed : {total_runs}")
    print(f"Guilty Scenarios          : {guilty_cases} | Innocent Scenarios: {innocent_cases}")
    print("-" * 78)
    print(f"🎯 Overall Judicial Accuracy       : {accuracy:6.2f}% ({(tp + tn)}/{total_runs})")
    print(f"⚖️  Guilty Conviction Rate (Recall) : {conviction_rate:6.2f}% ({tp}/{guilty_cases})")
    print(f"🏃 Guilty Suspect Escape Rate       : {escape_rate:6.2f}% ({fn}/{guilty_cases})")
    print(f"🕊️  Innocent Exoneration Rate       : {exoneration_rate:6.2f}% ({tn}/{innocent_cases})")
    print(f"🚨 Wrongful Conviction Rate (FP)    : {wrongful_conviction_rate:6.2f}% ({fp}/{innocent_cases})")
    print("-" * 78)
    print("📈 Judicial Grade Distribution:")
    for g, count in grades.items():
        pct = count / total_runs * 100
        print(f"   • Grade {g}: {count:3d} ({pct:5.1f}%)")
    print("-" * 78)
    print("⏱️  Performance Breakdown by Turn Limit:")
    print("   Turn Cap | Runs | Accuracy | Escape Rate | Conviction | Avg Tokens | Early Halt")
    print("   " + "-" * 70)
    for t_cap in sorted(turns_groups.keys()):
        grp = turns_groups[t_cap]
        grp_tp = sum(1 for r in grp if r["classification"] == "TP")
        grp_tn = sum(1 for r in grp if r["classification"] == "TN")
        grp_fn = sum(1 for r in grp if r["classification"] == "FN")
        grp_guilty = sum(1 for r in grp if r["ground_truth"] == "GUILTY")
        grp_acc = (grp_tp + grp_tn) / len(grp) * 100
        grp_esc = (grp_fn / grp_guilty * 100) if grp_guilty > 0 else 0.0
        grp_conv = (grp_tp / grp_guilty * 100) if grp_guilty > 0 else 0.0
        grp_tok = sum(r["total_tokens"] for r in grp) / len(grp)
        grp_early = sum(1 for r in grp if r["stop_reason"] == "goal_reached") / len(grp) * 100
        print(f"   {t_cap:7d}t | {len(grp):4d} | {grp_acc:7.1f}% | {grp_esc:10.1f}% | {grp_conv:9.1f}% | {grp_tok:10.0f} | {grp_early:9.1f}%")
    print("-" * 78)
    print("⚡ Operational Efficiency Metrics:")
    print(f"   • Average Turns per Case        : {avg_turns:.2f} turns")
    print(f"   • Early Budget Halt Rate        : {early_halts:.1f}% (solved before limit)")
    print(f"   • Average Tokens per Case       : {avg_tokens:.0f} tokens")
    print(f"   • Average Latency per Case      : {avg_time:.2f}s")
    print("=" * 78 + "\n")

    # Build Markdown table for turns breakdown
    turns_md_rows = []
    for t_cap in sorted(turns_groups.keys()):
        grp = turns_groups[t_cap]
        grp_tp = sum(1 for r in grp if r["classification"] == "TP")
        grp_tn = sum(1 for r in grp if r["classification"] == "TN")
        grp_fn = sum(1 for r in grp if r["classification"] == "FN")
        grp_guilty = sum(1 for r in grp if r["ground_truth"] == "GUILTY")
        grp_acc = (grp_tp + grp_tn) / len(grp) * 100
        grp_esc = (grp_fn / grp_guilty * 100) if grp_guilty > 0 else 0.0
        grp_conv = (grp_tp / grp_guilty * 100) if grp_guilty > 0 else 0.0
        grp_tok = sum(r["total_tokens"] for r in grp) / len(grp)
        grp_early = sum(1 for r in grp if r["stop_reason"] == "goal_reached") / len(grp) * 100
        turns_md_rows.append(f"| **{t_cap} Turns** | {len(grp)} | **{grp_acc:.1f}%** | {grp_esc:.1f}% | {grp_conv:.1f}% | {grp_tok:.0f} | {grp_early:.1f}% |")

    turns_md_table = "\n".join(turns_md_rows)

    md_content = f"""# 📊 Multi-Agent Interrogation Benchmark Report

**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Total Iterations:** {total_runs}  

---

## 1. Executive Summary Table

| Metric Category | Metric Name | Value | Description |
| :--- | :--- | :---: | :--- |
| **Judicial Accuracy** | **Overall Accuracy** | **{accuracy:.2f}%** | Overall correct verdict rate ($TP + TN$) |
| | **Guilty Conviction Rate (Recall)** | **{conviction_rate:.2f}%** | Percent of guilty suspects caught and convicted |
| | **Guilty Suspect Escape Rate** | **{escape_rate:.2f}%** | Percent of guilty suspects who evaded detection |
| | **Innocent Exoneration Rate** | **{exoneration_rate:.2f}%** | Percent of innocent suspects correctly cleared |
| | **Wrongful Accusation Rate (FP)** | **{wrongful_conviction_rate:.2f}%** | False accusation / miscarriage of justice rate |
| **Grade Distribution** | **Grade A (Justice Served)** | **{grades.get('A', 0) / total_runs * 100:.1f}%** | Flawless deduction and correct verdict |
| | **Grade B / C (Unsolved / Minor)** | **{(grades.get('B', 0) + grades.get('C', 0)) / total_runs * 100:.1f}%** | Suspect escaped or insufficient evidence |
| | **Grade F (False Conviction)** | **{grades.get('F', 0) / total_runs * 100:.1f}%** | Bullying / false imprisonment of innocent |
| **Efficiency** | **Average Dialogue Turns** | **{avg_turns:.2f}** | Turns utilized per interrogation |
| | **Early Exit Rate** | **{early_halts:.1f}%** | Interrogations concluded early via confession/clearance |
| | **Average Token Usage** | **{avg_tokens:.0f} tokens** | Mean token budget consumed per case |
| | **Average Execution Time** | **{avg_time:.2f}s** | Wall-clock execution duration per case |

---

## 2. Parameter Sensitivity: Performance by Turn Limit

| Turn Budget | Sample Runs | Accuracy (%) | Escape Rate (%) | Conviction Rate (%) | Avg Tokens | Early Halt (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
{turns_md_table}

---

## 3. Confusion Matrix

| Ground Truth \\ Detective Verdict | Arrested / Guilty | Exonerated / Innocent | Total |
| :--- | :---: | :---: | :---: |
| **Actual Guilty** | **{tp} (True Positive)** | **{fn} (False Negative / Escaped)** | **{guilty_cases}** |
| **Actual Innocent** | **{fp} (False Positive / Bullied)** | **{tn} (True Negative)** | **{innocent_cases}** |
"""
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"📄 Academic Markdown summary saved to: {output_md}\n")


def append_csv_row(filepath: str, row: dict, keys: list):
    """Appends a single run row to CSV immediately with file header initialization."""
    file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    p = argparse.ArgumentParser(description="Multi-Agent Interrogation Benchmark Suite")
    p.add_argument("--runs", type=int, default=12, help="Number of benchmark runs (default: 12)")
    p.add_argument("--mock", action="store_true", help="Run with fast offline MockClient")
    p.add_argument("--grid", action="store_true", help="Run parametric grid sweep across turns and temperatures")
    p.add_argument("--turns", type=str, default="4,6,8,10,12", help="Comma-separated turn limits to cycle across (default: '4,6,8,10,12')")
    p.add_argument("--trials", type=int, default=1, help="Number of trials per grid configuration (default: 1)")
    p.add_argument("--output-csv", type=str, default="benchmark_results.csv", help="CSV log filename")
    p.add_argument("--output-md", type=str, default="benchmark_summary.md", help="Markdown summary filename")
    args = p.parse_args()

    client = make_client(mock=args.mock)
    results = []

    turn_choices = [int(t.strip()) for t in args.turns.split(",") if t.strip().isdigit()]
    if not turn_choices:
        turn_choices = [4, 6, 8, 10, 12]

    # Initialize / clean CSV file
    csv_keys = [
        "theme", "ground_truth", "max_turns", "turns_used", "det_temp", "susp_temp",
        "detective_verdict", "suspect_confessed", "detective_exonerated", "judge_grade",
        "classification", "evidence_unlocked", "total_evidence", "total_tokens",
        "elapsed_seconds", "stop_reason"
    ]
    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_keys)
        writer.writeheader()

    print("\n" + "=" * 75)
    print("   🚀 STARTING MULTI-AGENT INTERROGATION BENCHMARK EXPERIMENT 🚀")
    print(f"   Mode: {'Mock Client (Offline Simulation)' if args.mock else 'Live Ollama Model (llama3.2:3b)'}")
    print(f"   Turn Limit Variations: {turn_choices}")
    print(f"   Results will be streamed live to: {args.output_csv}")
    print("=" * 75 + "\n")

    try:
        if args.grid:
            turns_grid = turn_choices
            temp_grid = [0.2, 0.4]
            total_configs = len(turns_grid) * len(temp_grid) * 2 * args.trials
            print(f"🔬 Running Parametric Grid Sweep ({total_configs} total rounds across {args.trials} trial(s))...")

            config_idx = 1
            for trial in range(1, args.trials + 1):
                for turns in turns_grid:
                    for temp in temp_grid:
                        for is_guilty in [True, False]:
                            trial_str = f" [Trial {trial}]" if args.trials > 1 else ""
                            print(f"[{config_idx:02d}/{total_configs}]{trial_str} Turns={turns}, Temp={temp}, Guilt={is_guilty}...", end=" ", flush=True)
                            try:
                                res = run_single_investigation(
                                    client,
                                    max_turns=turns,
                                    det_temp=temp,
                                    susp_temp=temp + 0.1,
                                    force_innocent=not is_guilty,
                                    force_guilty=is_guilty,
                                    mock=args.mock,
                                )
                                results.append(res)
                                append_csv_row(args.output_csv, res, csv_keys)
                                print(f"-> [{res['classification']}] Grade: {res['judge_grade']} ({res['turns_used']} turns, {res['elapsed_seconds']}s)")
                            except Exception as e:
                                print(f"-> ⚠️ Run failed ({e}). Continuing...")
                            config_idx += 1
        else:
            for i in range(1, args.runs + 1):
                turns_choice = turn_choices[(i - 1) % len(turn_choices)]
                print(f"[{i:02d}/{args.runs:02d}] Interrogation (Turn Cap={turns_choice:02d})...", end=" ", flush=True)
                try:
                    res = run_single_investigation(
                        client,
                        max_turns=turns_choice,
                        mock=args.mock,
                    )
                    results.append(res)
                    append_csv_row(args.output_csv, res, csv_keys)
                    print(f"-> [{res['classification']}] Ground: {res['ground_truth']:8s} | Verdict: {res['detective_verdict']:18s} | Grade: {res['judge_grade']} ({res['turns_used']:02d} turns, {res['elapsed_seconds']}s)")
                except Exception as e:
                    print(f"-> ⚠️ Run failed ({e}). Continuing...")

    except KeyboardInterrupt:
        print("\n\n⚠️ Benchmark interrupted by user. Generating summary for completed runs...")

    if results:
        print_benchmark_summary(results, output_csv=args.output_csv, output_md=args.output_md)


if __name__ == "__main__":
    main()
