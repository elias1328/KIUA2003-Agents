# KIUA2003-Agents
Code written by Elias and Simen
# Bounded Two-Agent Dialogue System: Police Interrogation

A bounded multi-agent system where two LLM agents engage in an interrogation under turn, token, and time budgets, followed by automated evaluation using an LLM-as-a-judge.

---

## Scenario Overview

* **Scenario:** High-stakes police interrogation regarding the theft of the "Star of Midnight" diamond from the Grand Gallery vault at 21:30.
* **Agent A:** Detective Cross (probing investigator seeking alibi contradictions).
* **Agent B:** Julian Vance (museum curator defending an alibi with structured status flags).
* **Termination Conditions:** Hard stop at 8 turns, 4,000 tokens, 120 seconds, or an explicit confession (`{"confessed": true}`).
* **Context Management:** Summarisation hook that preserves critical alibi timestamps, locations, and contradictions without overflowing the context window.

---

## Prerequisites

1. **Python 3.10+**
2. **Ollama running locally:**
   ```bash
   ollama serve
   ollama pull llama3.2:3b
   ```

## Quickstart (Single Command)
1.  **Install dependencies:** 
    ```bash
    pip install -r requirements.txt
    ```

2. **Run the complete dialogue and automated evaluation with one command:**
    ```bash
    python run.py --config configs/interrogation.yaml --judge
    ```

3. **To test offline without Ollama running, append --mock:**
    ```bash
    python run.py --config configs/interrogation.yaml --mock
    ```

## Repository Structure
```text
├── agents.py                 # Agent dataclass definition
├── budget.py                 # Budget guardrail (turns, tokens, wall-clock) -Unchanged from example code
├── engine.py                 # DialogueEngine orchestration, view_for role-mapping, summarisation
├── judge.py                  # LLM-as-a-judge evaluation rubric and JSON parser
├── llm_client.py             # OllamaClient and MockClient wrappers
├── run.py                    # Entry point and structured parse guard
├── requirements.txt          # Python dependencies (pyyaml, requests)
├── configs/
│   ├── interrogation.yaml    # Primary interrogation scenario
│   ├── exp-temp00.yaml       # Experiment run: temperature 0.0
│   ├── exp-temp07.yaml       # Experiment run: temperature 0.7
│   ├── exp-temp10.yaml       # Experiment run: temperature 1.0
│   ├── fail-drift.yaml       # Failure mode test: temperature 1.5 (topic drift)
│   ├── fail-forgetting.yaml  # Failure mode test: aggressive truncation (forgetting)
│   └── fail-sycophancy.yaml  # Failure mode test: aligned agreeable personas (sycophancy)
├── transcripts/              # Output JSON transcripts with per-message metrics
└── judge_docs/               # Evaluator verdict outputs
```

## Key Components
* **Role-Mapping (`view_for` in `engine.py`):** Chat models require perspective-dependent roles. `view_for` renders a neutral conversation into an agent-specific message list, mapping the current agent's historical lines to `assistant` and the opposing agent's lines to `user`.

* **Guardrails (`budget.py`):** Prevents infinite agent loops by enforcing limits on total turns, tokens (prompt + completion), and wall-clock elapsed time. Whichever condition fires first terminates the run and records `stop_reason`.

* **Context Management (`summarise_context` in `engine.py`):** Compresses dialogue history older than 10 messages into a deterministic summary block (`temperature=0`), preserving concrete timestamps and claims to prevent the forgetting failure mode.

* **Structured Decision & Parse Guard (`run.py`):** The suspect appends a structured JSON payload (`{"confessed": boolean}`) to replies. The engine extracts and validates this payload using regex and `json.loads` within a `try/except` guard to trigger early termination if a confession occurs.

* **LLM-as-a-Judge (`judge.py`):** Runs as an independent evaluation pass (`temperature=0`) over the completed transcript, returning a structured JSON score (1–5), binary success flag, and explanation based on investigative consistency.

## Reproducing the Experiments
1. **Run all temperature configurations with automated judging:**
    ```bash
    python run.py --config configs/exp-temp00.yaml --judge
    python run.py --config configs/exp-temp07.yaml --judge
    python run.py --config configs/exp-temp10.yaml --judge
    ```

All transcripts are written directly to `transcripts/`, and judge evaluations are stored in `judge_docs/`.