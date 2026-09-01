"""run.py: entry point.

Two modes:
  1. Smoke test (default): one model call, to prove your setup works.
        python run.py --mock      # free/offline
        python run.py             # real local model via Ollama
  2. Full run from a config (works once you've completed engine.py in Week 2):
        python run.py --config configs/debate.yaml
        python run.py --config configs/debate.yaml --mock
"""
import argparse

from llm_client import make_client


def smoke(mock):
    client = make_client(mock=mock)
    messages = [
        {"role": "system", "content": "You are terse."},
        {"role": "user", "content": "Say hello in exactly three words."},
    ]
    r = client.chat("llama3.2:3b", messages, temperature=0)
    print("Model replied:", r.text)
    print(f"(prompt={r.prompt_tokens} tokens, completion={r.completion_tokens} tokens, "
          f"{r.seconds:.2f}s)")


def run_config(path, mock):
    import yaml  # local import so the smoke test needs no extra deps

    from agents import Agent
    from budget import Budget
    from engine import DialogueEngine

    with open(path) as f:
        cfg = yaml.safe_load(f)
    agents = [Agent(**a) for a in cfg["agents"]]
    budget = Budget(**cfg.get("budget", {}))
    client = make_client(mock=mock)

    engine = DialogueEngine(agents, client, budget)
    transcript = engine.run()

    for e in transcript:
        print(f"{e.speaker}: {e.content}\n")

    out = cfg.get("output", "transcripts/run.json")
    engine.save(out, meta={"topic": cfg.get("topic"), "config": path})
    print(f"[stopped: {budget.stop_reason} "
          f"({budget.turns} turns, {budget.tokens} tokens). Saved {out}]")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true", help="use the free offline MockClient")
    p.add_argument("--config", help="run a full dialogue from a YAML config")
    args = p.parse_args()
    if args.config:
        run_config(args.config, mock=args.mock)
    else:
        smoke(mock=args.mock)
