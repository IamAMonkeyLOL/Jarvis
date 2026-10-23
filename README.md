# Jarvis

Jarvis includes a responsive web preview and a local Windows desktop analyzer for Python projects.

## Web preview

The browser workspace supports conversation export, browser-local chat history, guided demo responses, creative scene downloads, and a configurable hosted AI connection.

### Publish on GitHub Pages

In this repository, open **Settings → Pages → Source → GitHub Actions**. The included **Publish Jarvis website** workflow deploys on pushes to `main`; run it manually from Actions after enabling Pages if necessary. The published URL is shown by the deployment.

The workflow publishes `docs/` plus the scene assets and preview archive. It does not publish the desktop source as an executable web app.

### AI chat

The website starts in **Demo mode**. Responses in this mode are predefined guides, not AI-generated replies. A ready-to-host OpenAI backend is included in [backend/](backend/README.md); deployment and your own provider key are still required.

To enable live chat, host a server endpoint and enter its HTTPS URL under **Connection & setup**. It must accept `POST` JSON:

```json
{"messages":[{"role":"user","content":"Hello"}]}
```

And return JSON:

```json
{"reply":"Hello"}
```

The service must allow the website origin through CORS, including JSON POST preflight requests. Keep provider credentials on the server. Configure authentication as needed, rate limiting, and a usage budget before offering the service publicly. The browser sends up to the last 40 messages per request, with a 60-second timeout. This generic endpoint integration does not include user accounts or cookie authentication.

Conversation history (up to 100 messages) and the configured endpoint URL are stored in browser local storage. Users can export or clear history. Connected mode sends conversation text to the configured service.

## Desktop project analyzer

Jarvis recursively inspects Python source with the standard-library AST parser and presents prioritized, actionable findings.

### Run

```powershell
py main.py
```

No third-party Python packages are required. To use the embedded browser:

```powershell
py -m pip install -r requirements.txt
```

### Features

- Recursive project scanning with generated/dependency-folder exclusions and optional per-scan ignored folders.
- AST-based code-quality, security, and reliability findings with severity and category filters.
- JSON, Markdown, CSV, and HTML exports, scan metrics, skipped-file reporting, and CLI/CI support.
- Optional local AI review through an Ollama-compatible endpoint; only generated findings are sent.
- Embedded Edge WebView browsing and configurable shortcuts for installed VPN clients.

### Test

```powershell
py -m unittest discover -s tests -v
```

### Command line / CI

```powershell
py main.py --analyze C:\path\to\project --format json --output report.json --fail-on high
```

`--fail-on` returns exit code `1` when a finding is at or above the chosen severity. Use `--max-file-lines` to set the scanner's file-size limit.

### Windows executable

`Jarvis.exe` includes the desktop analyzer, embedded browser, and VPN-client shortcuts. It starts configured, installed VPN clients; it does not include a VPN provider, credentials, or tunnel.

To rebuild it:

```powershell
py -m pip install -r requirements-build.txt
.\build_exe.ps1
```
