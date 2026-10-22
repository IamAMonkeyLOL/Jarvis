# Jarvis: a local assistant you can understand and extend

A first-week Python project: chat with Qwen3 8B through Ollama, store your
conversations in SQLite, and reopen them later. The interface uses Streamlit.

This is an AI-assisted software project. The model was trained by its original
creators; this project builds the assistant around it. Keep a development log
of what you test, change, and learn so you can explain your contribution.

## Start on Windows

Read **START_HERE.txt** for the complete click-by-click setup.

1. Install [Ollama](https://ollama.com/download/windows) and a 64-bit Python
   installation. Python 3.11+ is required; Python 3.12 was used for the tests.
   Python 3.13 is a reasonable Windows installer choice from
   [python.org](https://www.python.org/downloads/windows/).
2. Extract the ZIP onto your SSD and open the `jarvis_starter` folder.
3. Open Ollama and run `SETUP_MODEL.bat` to download `qwen3:8b`.
4. Run `START_JARVIS.bat`. Its first launch installs the app dependencies into
   `.venv`. Later launches reuse them.
5. Open <http://127.0.0.1:8501> if your browser does not open automatically.

Keep the launcher terminal open. Press **Ctrl+C** in that terminal to stop the
app. Installing dependencies and downloading the model need internet. Once
installed, normal chat uses your local model and can be tested offline.

The launchers have been reviewed but not executed on Windows in this build
environment. The Python app was tested on Linux with Python 3.12 and
Streamlit 1.66.0. Your Windows/GPU checks remain in TODAY_CHECKLIST.md.

### Manual launch (PowerShell, from this folder)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen3:8b
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Virtual environment activation is unnecessary: these commands use its Python
directly, so you do not need to change PowerShell execution policy.

## What works

- Streaming chat through the local Ollama API, with Qwen3's thinking mode off.
- Persistent SQLite conversations, titles, message timestamps, and model names.
- A sidebar to start or reopen conversations and export an individual chat as JSON.
- A Stop button, interrupted/error labels, and retry without duplicating the
  user's question. Stop takes effect on the next returned stream chunk; an
  initial model load or stalled connection can take longer to stop.
- Recent context from the current conversation. Complete turns are selected
  within an estimated prompt budget; older archived turns remain on disk.
- Reply timing and tokens/second when Ollama supplies the counters.
- A local backup helper, setup checker, short API example, and automated tests.

The assistant cannot browse, run commands, edit files, or recall unrelated
conversations yet. It does not train its own weights when you chat. Adding
searchable project memory is the next milestone after this baseline works.

## How it fits together

`app.py` displays the chat. `jarvis/storage.py` reads and writes SQLite.
`jarvis/context.py` selects recent turns. `jarvis/service.py` runs generation
in a background thread so the screen can remain responsive.
`jarvis/ollama.py` sends those turns to Ollama and reads the response stream.

| File | What to learn from it |
| --- | --- |
| `chat_cli.py` | Send one prompt to an HTTP API from Python. This example does not save history. |
| `app.py` | Widgets, browser sessions, and connecting the UI to the backend. |
| `jarvis/storage.py` | SQL tables, transactions, foreign keys, JSON export and consistent backups. |
| `jarvis/context.py` | Saved data versus the limited text a model sees for one response. |
| `jarvis/ollama.py` | JSON requests, streamed JSON lines, timeouts and useful errors. |
| `jarvis/service.py` | A worker thread, cancellation and saving incomplete work honestly. |
| `tests/` | Repeatable checks that do not depend on unpredictable model answers. |

### Storage and context are different

All conversation messages are saved in `data/jarvis.sqlite3`. SQLite may also
create `-wal` and `-shm` files while the app is running. A saved chat can be much
larger than the text sent to the model for one reply.

The model uses a **4,096-token context**. The app budgets about 2,800 estimated
prompt tokens and allows up to 768 output tokens, leaving a margin for model
formatting. This estimator is deliberately simple, not an exact Qwen tokenizer;
unusual text can still behave differently. Inputs are limited to 3,000 characters,
and messages that exceed the estimated budget are rejected with a clear error.
Long answers may stop at the output limit; ask Jarvis to continue.

Whole recent question/answer pairs are included while they fit. Failed and
interrupted answers are excluded. The app shows when older complete turns have
been omitted. It does not search other chats or automatically summarize them.

### Data and network behavior

The app binds to `127.0.0.1:8501`; its model client only accepts the loopback
address and `qwen3:8b`. There is no paid API provider, API key, or remote fallback.
Streamlit usage statistics are disabled in `.streamlit/config.toml`.

Chats are ordinary local SQLite data, not encrypted by this app. `.gitignore`
excludes conversations, backups, virtual environments and common secret files.
If you place the project in a folder synchronized by another app, that app's
sync behavior still applies. This is a single-user desktop project, not a
shared hosted service; only one generation runs at a time.

## Today's checks

Use **TODAY_CHECKLIST.md** and **BASELINE_PROMPTS.md**. Run:

```powershell
.\.venv\Scripts\python.exe chat_cli.py "Explain what a Python dictionary is."
.\.venv\Scripts\python.exe doctor.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

While Jarvis is answering, open another terminal and run `ollama ps`. Record
the PROCESSOR column and response timing. Model loading, other GPU applications,
context length and available VRAM affect results. The 15.9 GB of shared GPU
memory shown by Windows is system RAM, not extra dedicated VRAM equivalent to
the RTX 5070's 12 GB.

**Build validation:** 13 automated tests passed in the build environment using
a synthetic local HTTP server. They cover persistence after reopening, export,
backup, deletion isolation, context trimming, streaming, failure/retry,
cancellation, and the Streamlit chat interface. These tests do not validate
the actual Qwen model, NVIDIA drivers, Windows batch files, or your GPU speed.

## Back up your chats

```powershell
.\.venv\Scripts\python.exe backup.py
```

This writes a consistent database snapshot under `backups/` using SQLite's
backup API. Copy that backup elsewhere if you want protection from disk failure.
To restore: stop Jarvis, preserve the existing `data` folder under another name,
create a fresh `data` folder, copy your chosen backup into it as
`jarvis.sqlite3`, and restart. Keep the preserved folder until you verify the
restored chat. Do not mix an old database with unrelated `-wal`/`-shm` files.

## Save a first Git commit

Install [Git for Windows](https://git-scm.com/install/windows), open a terminal
in this folder, and run:

```powershell
git init
git status
git add .
git diff --cached --stat
git commit -m "Build local Jarvis chat with persistent history"
```

If Git asks for your identity, set it for this repository (no `--global` needed):

```powershell
git config user.name "Your Name"
git config user.email "your-chosen-commit-email@example.com"
```

Replace those placeholders with the identity you want attached to commits, then
retry the commit. Check that `data/`, `.venv/` and any keys are absent from the
staged list. These commands make a local commit; they do not publish anything.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| `py` or `python` is not recognized | Install Python, enable its launcher/PATH options if offered, and open a new terminal. |
| Ollama is not connected | Open the Ollama app and click **Check again**. |
| Model download needed / HTTP 404 | Run `SETUP_MODEL.bat`; update Ollama if the model or API is unsupported. |
| First answer seems stuck | Give the model time to load; inspect Ollama and `ollama ps`. The HTTP timeout is 180 seconds per stalled read, not a whole-reply timer. |
| Slow replies or CPU/GPU split | Close games or other GPU-heavy apps, check `ollama ps`, free VRAM and verify the NVIDIA driver before changing models. |
| Port 8501 is occupied | Stop an older Jarvis terminal, or manually launch with `--server.port 8502`. |
| A message is too long | Split it into smaller parts. Changing context settings is a later, measured tuning step. |
| Installation failed | Read the terminal error, check internet/free space, then rerun the launcher. |
| Dependencies break after moving the folder | Stop the app, remove only `.venv`, and rerun the launcher. Keep `data`. |

## Next milestone

After the first-week checklist passes, add an explicit memory table: create,
list, edit and delete facts, with a source and date. Then add document retrieval
with citations. A cloud provider can later implement the same chat interface
without replacing the database. Keep each stage small enough to test and explain.

## Official references

- [Ollama Windows setup](https://docs.ollama.com/windows)
- [Qwen3 8B model](https://ollama.com/library/qwen3:8b)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama model list API](https://docs.ollama.com/api/tags)
- [Ollama context length](https://docs.ollama.com/context-length)
- [Ollama GPU support](https://docs.ollama.com/gpu)
- [Streamlit app testing](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)

Dependencies and model weights keep their own licenses. Model weights and
third-party packages are downloaded separately; they are not bundled in this ZIP.
