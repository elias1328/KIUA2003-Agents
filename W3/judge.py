import json
from llm_client import make_client


def judge(transcript, client=None, model="llama3.2:3b"):
    """Evaluates a dialogue transcript and returns a structured verdict."""
    client = client or make_client()
    conversation = "\n".join(f"{e.speaker}: {e.content}" for e in transcript)
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are an impartial evaluator for a criminal interrogation dialogue.\n"
                "Evaluate whether the detective conducted a coherent, probing inquiry and whether "
                "the suspect maintained an alibi or confessed.\n"
                "Respond ONLY with a JSON object in this exact schema:\n"
                '{"score": <integer 1-5>, "success": <true/false>, "reason": "<short explanation>"}'
            ),
        },
        {"role": "user", "content": conversation},
    ]

    reply = client.chat(model, messages, temperature=0)
    try:
        return json.loads(reply.text)
    except json.JSONDecodeError:
        return {"score": 0, "success": False, "reason": f"invalid JSON from judge: {reply.text[:100]}"}