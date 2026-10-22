"""Run with: python -m streamlit run app.py"""
import threading
import streamlit as st

from jarvis.config import DB_PATH, MAX_INPUT_CHARS, MODEL
from jarvis.context import build_context
from jarvis.ollama import OllamaClient, OllamaError
from jarvis.service import start_generation
from jarvis.storage import Store

st.set_page_config(page_title="Jarvis · Local assistant", page_icon="◉", layout="centered")

 
@st.cache_resource
def resources(db_path):
    store = Store(db_path)
    store.recover_pending()
    # A single generation at a time across browser tabs for this local app.
    return store, OllamaClient(), threading.Lock(), {}


store, client, lock, shared = resources(str(DB_PATH))
job = shared.get("job")
busy = job is not None and not job.done.is_set()
chats = store.conversations()
ids = [item["id"] for item in chats]
if not ids:
    ids = [store.create()]
    chats = store.conversations()
if st.session_state.get("chat_id") not in ids:
    st.session_state.chat_id = ids[0]

with st.sidebar:
    st.title("◉ Jarvis")
    st.caption("YOUR LOCAL PROJECT ASSISTANT")
    if st.button("＋ New conversation", disabled=busy, width="stretch"):
        st.session_state.chat_id = store.create()
        st.rerun()
    titles = {item["id"]: item["title"] for item in chats}
    selected = st.selectbox("Saved conversations", ids, index=ids.index(st.session_state.chat_id), format_func=lambda value: f"{titles[value]} · #{value}", disabled=busy)
    st.session_state.chat_id = selected
    st.divider()
    st.caption(f"MODEL · {MODEL}\n\nCONTEXT · 4,096 tokens")
    if "connection" not in st.session_state or st.button("Check again", disabled=busy):
        try:
            st.session_state.connection = ("ready", "Ollama is ready") if client.check() else ("missing", "Model download needed")
        except OllamaError:
            st.session_state.connection = ("offline", "Ollama is not connected")
    state, label = st.session_state.connection
    if state == "ready":
        st.success(label)
    elif state == "missing":
        st.warning(label)
        st.caption("Run SETUP_MODEL.bat, then click Check again.")
    else:
        st.warning(label)
        st.caption("Open the Ollama app, then click Check again.")
    st.download_button("Export this conversation", store.export(selected), file_name=f"jarvis-chat-{selected}.json", mime="application/json", disabled=busy, width="stretch")
    with st.expander("Delete this conversation"):
        confirmed = st.checkbox("Delete its saved messages", disabled=busy, key=f"confirm_{selected}")
        if st.button("Delete permanently", disabled=busy or not confirmed):
            store.delete(selected)
            st.rerun()
    st.caption("Chats stay in this project’s data folder. This starter sends prompts only to local Ollama.")

st.title("Let’s build something.")
st.caption("Ask a question, work through a problem, or pick up a saved conversation.")
messages = store.messages(selected)
if not messages:
    st.info("Try: ‘Help me build my first Python project. Explain each step.’")
    st.caption("History is saved automatically. Cross-conversation memory comes later in the roadmap.")


def footer(message):
    metadata = message.get("metadata", {})
    if message["status"] in ("interrupted", "pending"):
        st.caption("Stopped before completion. You can retry this response.")
    elif message["status"] == "error":
        st.error(metadata.get("error", "The response failed. You can retry it."))
    elif message["role"] == "assistant" and metadata:
        info = f"{message.get('model') or MODEL} · {metadata.get('elapsed_seconds', 0):.1f}s"
        duration = metadata.get("eval_duration", 0)
        if duration and metadata.get("eval_count"):
            info += f" · {metadata['eval_count'] / (duration / 1e9):.1f} tokens/s"
        st.caption(info)
        if metadata.get("done_reason") == "length":
            st.caption("Reply limit reached. Ask Jarvis to continue if needed.")
        if metadata.get("omitted_turns"):
            st.caption(f"{metadata['omitted_turns']} older turn(s) were saved but outside this reply’s recent context.")


for message in messages:
    if busy and message["id"] == job.assistant_id:
        continue
    with st.chat_message(message["role"]):
        if message["content"]:
            st.markdown(message["content"])
        footer(message)


@st.fragment(run_every=0.5)
def live_response():
    current = shared.get("job")
    if current is None:
        return
    if current.done.is_set():
        st.rerun()
    with st.chat_message("assistant"):
        st.markdown(current.text + " ▍" if current.text else "Loading the model and thinking…")
        if current.omitted_turns:
            st.caption(f"{current.omitted_turns} older turn(s) are saved but outside this reply’s recent context.")
        if current.cancel.is_set():
            st.caption("Stopping… waiting for Ollama to return its next chunk. The first model load can take longer.")
        elif st.button("Stop response", key="stop_response"):
            current.cancel.set()
            st.rerun(scope="fragment")


if busy:
    if job.conversation_id == selected:
        live_response()
    else:
        st.info("Jarvis is answering in another conversation. Wait for it to finish.")
    st.chat_input("Wait for this reply or stop it above", disabled=True, max_chars=MAX_INPUT_CHARS)
else:
    if job is not None and job.conversation_id == selected and job.error:
        # Covers disk failures where the message metadata could not be saved.
        st.caption(job.error)
    retry = False
    if messages and (messages[-1]["role"] == "user" or messages[-1]["status"] in ("error", "interrupted", "pending")):
        retry = st.button("Retry last response")
    prompt = st.chat_input("Message Jarvis…", max_chars=MAX_INPUT_CHARS)
    if prompt or retry:
        # The mutex prevents two browser sessions racing to start requests.
        with lock:
            active = shared.get("job")
            if active is not None and not active.done.is_set():
                st.warning("Another response is already running. Please wait.")
            else:
                try:
                    if prompt:
                        prompt = prompt.strip()
                        if not prompt:
                            raise ValueError("Please enter a message.")
                        build_context([{"role": "user", "content": prompt}])
                        store.add(selected, "user", prompt)
                    shared["job"] = start_generation(store, selected, client)
                except (ValueError, OllamaError) as error:
                    st.error(str(error))
                else:
                    st.rerun()
