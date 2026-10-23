# Jarvis · Web preview

A responsive browser workspace with conversation export, browser-local chat history, guided demo responses, creative scene downloads, and a configurable hosted AI connection.

## Publish on GitHub Pages

In this repository, open **Settings → Pages → Source → GitHub Actions**. The included **Publish Jarvis website** workflow deploys on pushes to `main`; run it manually from Actions after enabling Pages if necessary. The published URL is shown by the deployment.

The workflow publishes `docs/` plus the scene assets and preview archive. It does not publish the desktop source as an executable web app.

## AI chat

The website starts in **Demo mode**. Responses in this mode are predefined guides, not AI-generated replies. A ready-to-host OpenAI backend is included in [backend/](backend/README.md); deployment and your own provider key are still required.

To enable live chat, host a server endpoint and enter its HTTPS URL under **Connection & setup**. It must accept `POST` JSON:

```json
{"messages":[{"role":"user","content":"Hello"}]}
```

And return JSON:

```json
{"reply":"Hello!"}
```

The service must allow the website origin through CORS, including JSON POST preflight requests. Keep provider credentials on the server. Configure authentication as needed, rate limiting, and a usage budget before offering the service publicly. The browser sends up to the last 40 messages per request, with a 60-second timeout. This generic endpoint integration does not include user accounts or cookie authentication.

Conversation history (up to 100 messages) and the configured endpoint URL are stored in browser local storage. Users can export or clear history. Connected mode sends conversation text to the configured service.

## Desktop preview

The original `JARVIS_6_Preview/`, `D5_Starter/`, Blender file, and archive remain available. The desktop preview needs Python, Streamlit, and local Ollama. Windows launch controls do not run in a website.
