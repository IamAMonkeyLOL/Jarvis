"""Generation runs in a worker so the UI can offer a real Stop button."""
from dataclasses import dataclass, field
import threading
import time
from .context import build_context
from .ollama import OllamaError


@dataclass
class Generation:
    conversation_id: int
    assistant_id: int
    omitted_turns: int
    cancel: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)
    text: str = ""
    error: str = ""
    status: str = "pending"
    metadata: dict = field(default_factory=dict)
    thread: object = None


def start_generation(store, conversation_id, client):
    messages = store.messages(conversation_id)
    # Retrying an unsuccessful reply reuses the user message and assistant row.
    last = messages[-1] if messages else None
    if last and last["role"] == "assistant" and last["status"] != "complete":
        assistant_id = last["id"]
        messages = messages[:-1]
    else:
        assistant_id = None
    context, omitted = build_context(messages)
    if assistant_id is None:
        assistant_id = store.add(conversation_id, "assistant", "", "pending", client.model)
    else:
        store.update(assistant_id, "", "pending")
    job = Generation(conversation_id, assistant_id, omitted)

    def run():
        started = time.monotonic()
        last_save = started
        stream = None
        try:
            if job.cancel.is_set():
                job.status = "interrupted"
                return
            stream = client.stream(context)
            for event in stream:
                if job.cancel.is_set():
                    job.status = "interrupted"
                    break
                content = event.get("message", {}).get("content", "")
                if not isinstance(content, str):
                    raise OllamaError("Ollama returned invalid message text.")
                job.text += content
                if time.monotonic() - last_save >= 1:
                    store.update(assistant_id, job.text, "pending")
                    last_save = time.monotonic()
                if event.get("done"):
                    job.status = "complete"
                    job.metadata = {key: event[key] for key in ("eval_count", "eval_duration", "prompt_eval_count", "done_reason") if key in event}
                    if not job.text.strip():
                        raise OllamaError("Ollama finished without any answer text. Retry or check the model installation.")
            if job.status == "pending":
                job.status = "interrupted" if job.cancel.is_set() else "error"
                if job.status == "error":
                    job.error = "The reply did not finish. You can retry."
        except OllamaError as error:
            job.status = "interrupted" if job.cancel.is_set() else "error"
            job.error = "" if job.cancel.is_set() else str(error)
        except Exception as error:
            job.status = "error"
            job.error = f"Could not complete this reply ({type(error).__name__}). Your earlier messages are saved."
        finally:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
            job.metadata["omitted_turns"] = job.omitted_turns
            job.metadata["elapsed_seconds"] = round(time.monotonic() - started, 2)
            if job.error:
                job.metadata["error"] = job.error
            try:
                store.update(assistant_id, job.text, job.status, job.metadata)
            except Exception:
                job.error = "The reply could not be saved. Check free disk space and folder permissions."
                job.status = "error"
            job.done.set()

    job.thread = threading.Thread(target=run, daemon=True, name="jarvis-generation")
    job.thread.start()
    return job
