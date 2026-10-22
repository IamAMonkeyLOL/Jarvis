"""Select recent complete turns; the full archive stays in SQLite."""
import math
from .config import PROMPT_TOKEN_BUDGET, SYSTEM_PROMPT


def estimated_tokens(text):
    ascii_count = sum(ord(char) < 128 for char in text)
    # Plain English is usually about four characters/token. Use three plus
    # UTF-8 bytes for other scripts to leave a conservative margin.
    non_ascii_bytes = sum(len(char.encode("utf-8")) for char in text if ord(char) >= 128)
    return math.ceil(ascii_count / 3) + non_ascii_bytes + 16


def build_context(messages, budget=PROMPT_TOKEN_BUDGET):
    """Return API messages and number of older, complete turns omitted.

    The last record must be the current user message. Interrupted/error
    assistant replies never become accepted evidence in the next prompt.
    """
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("A new user message is required.")
    system = {"role": "system", "content": SYSTEM_PROMPT}
    latest = {"role": "user", "content": messages[-1]["content"]}
    used = estimated_tokens(SYSTEM_PROMPT) + estimated_tokens(latest["content"])
    if used > budget:
        raise ValueError("That message is too long for this starter's context. Please split it into smaller parts.")
    turns = []
    pending = None
    for message in messages[:-1]:
        if message["role"] == "user":
            pending = {"role": "user", "content": message["content"]}
        elif message["role"] == "assistant":
            if pending is not None and message.get("status", "complete") == "complete":
                turns.append([pending, {"role": "assistant", "content": message["content"]}])
            pending = None
    selected = []
    for turn in reversed(turns):
        cost = sum(estimated_tokens(item["content"]) for item in turn)
        if used + cost > budget:
            break
        selected.insert(0, turn)
        used += cost
    return [system] + [item for turn in selected for item in turn] + [latest], len(turns) - len(selected)
