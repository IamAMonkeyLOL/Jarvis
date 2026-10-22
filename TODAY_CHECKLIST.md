# Days 1–7, compressed into one build session

The starter code is prepared. Tick these boxes only after doing the check on
your own PC. Download and installation time will depend on your connection.

| Roadmap day | Action today | Evidence to record |
| --- | --- | --- |
| 1–2 | Install/open Ollama, Python, VS Code and Git; launch the isolated environment. | `CHECK_SETUP.bat` output; Python, Ollama and Git versions; free SSD space. |
| 3 | Download Qwen3 8B and generate a real local reply. | A screenshot of the answer plus `ollama ps` while it is generating. |
| 4 | Run `chat_cli.py` from Python. | The terminal prints an actual reply from Ollama. |
| 5 | Chat in the Streamlit interface. | Both messages appear and `data/jarvis.sqlite3` exists. |
| 6 | Stop/restart Jarvis and reopen the saved conversation. | The same messages remain; a new conversation is separate. |
| 7 | Complete ten prompts, note failures, make one understandable change, and commit. | Filled baseline record, development-log entry and first local Git commit. |

- [ ] Setup checker reports model installed.
- [ ] One real response completes through the CLI.
- [ ] One real response completes in the browser.
- [ ] The second question can refer to the first message in that conversation.
- [ ] Closing and reopening the app keeps the saved messages.
- [ ] New conversation starts without claiming to recall unrelated chats.
- [ ] Stop response leaves an interrupted marker; Retry can finish it.
- [ ] With Ollama quit, a question produces a useful error and keeps the user text.
- [ ] Reopening Ollama and retrying works.
- [ ] Export downloads valid JSON containing this conversation.
- [ ] After installation, a new reply works with the network disconnected.
- [ ] `RUN_TESTS.bat` passes.
- [ ] Ten baseline results are recorded.
- [ ] Git commit is saved locally.

## Your machine record

- OS: Windows 11 Home
- CPU: AMD Ryzen 7 5700X
- RAM: 32 GB
- GPU: RTX 5070, 12 GB dedicated VRAM
- Python version: _fill in_
- Ollama version: _fill in_
- Git version: _fill in_
- NVIDIA driver version: _fill in_
- Free space / model drive: _fill in_
- `ollama ps` PROCESSOR result: _fill in_
- Typical warm response tokens/second: _fill in_
- Restart / offline tests: _fill in_

## To explain in your own words

1. Which file talks to Ollama, and what does the HTTP request contain?
2. Where do conversations live after the app closes?
3. Why does saving a million messages not make them all fit in the model context?
4. What happens when a generation fails halfway through?
5. Which part did you change, and how did you check it?
