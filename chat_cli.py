"""Day 4: a small direct Python-to-Ollama example (no saved chat history)."""
import sys
from jarvis.context import build_context
from jarvis.ollama import OllamaClient, OllamaError


def main():
    prompt = " ".join(sys.argv[1:]) or input("You: ").strip()
    if not prompt:
        return 0
    try:
        messages, _ = build_context([{"role": "user", "content": prompt}])
        print("Jarvis: ", end="", flush=True)
        for event in OllamaClient().stream(messages):
            print(event.get("message", {}).get("content", ""), end="", flush=True)
        print()
        return 0
    except (OllamaError, ValueError) as error:
        print(f"\n{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
