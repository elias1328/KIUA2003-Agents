import argparse
from llm_client import make_client

def test_roles(mock=False):
    # make_client gives us the connection to Ollama (or offline mock)
    client = make_client(mock=mock)
    model = "llama3.2:3b"

    print("=" * 50)
    print("STEP 1: Starting with 'system' and 'user'")
    print("=" * 50)

    # 1. Start the conversation list
    messages = [
        {"role": "system", "content": "You are a pirate. Keep replies to 1 short sentence."},
        {"role": "user",   "content": "What is your favorite food?"}
    ]

    # Look at what we are sending:
    print("\n--- Sending this list to the AI: ---")
    for msg in messages:
        print(f"  Role: {msg['role']:<10} | Content: {msg['content']}")

    # 2. Ask the model
    reply1 = client.chat(model, messages)
    print(f"\nAI Replied: \"{reply1.text}\"")

    print("\n" + "=" * 50)
    print("STEP 2: Adding the AI's reply as 'assistant', then asking a follow-up")
    print("=" * 50)

    # 3. Append what the AI just said as 'assistant' (giving it memory!)
    messages.append({"role": "assistant", "content": reply1.text})

    # 4. Append our new question as 'user'
    messages.append({"role": "user", "content": "Why do you like that so much?"})

    # Look at the list now (it has 4 items):
    print("\n--- Updated messages list (with memory): ---")
    for msg in messages:
        print(f"  Role: {msg['role']:<10} | Content: {msg['content']}")

    # 5. Ask the model again with the whole history
    reply2 = client.chat(model, messages)
    print(f"\nAI Replied: \"{reply2.text}\"")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true", help="run offline with mock replies")
    args = p.parse_args()
    test_roles(mock=args.mock)