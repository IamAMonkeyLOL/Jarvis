# Jarvis AI backend

Requires Node.js 22 or later. No packages to install. Uses OpenAI Responses over HTTPS and keeps the provider key on the server.

## Your private connection folder

The connection folder supplied for this project is `C:\Users\Riley\OneDrive\Desktop\Jarvis\admin\ChatGpt`. It was empty when checked. Copy `backend/.env.example` there as `.env`, enter your own OpenAI API key and a model ID available to your account, and keep that file private. Do not paste the key into the website or commit it to GitHub.

Create a key in https://platform.openai.com/api-keys. API usage requires an appropriately configured API account. Official setup: https://developers.openai.com/api/docs/quickstart.

From the repository root, run:

```powershell
node --env-file="C:\Users\Riley\OneDrive\Desktop\Jarvis\admin\ChatGpt\.env" backend/server.mjs
```

Check `http://127.0.0.1:8787/health`. It reports whether key and model settings are present; it does not validate the key with OpenAI. A local server alone does not provide a public HTTPS endpoint for GitHub Pages users. Open the website through an HTTP preview server rather than a `file://` URL.

## Host for website users

Deploy the `backend` directory to a Node.js web service. Start with `node server.mjs`. Set the private environment variables from `.env.example` in that host's settings, use `HOST=0.0.0.0`, and use the host's assigned `PORT`. Use `ALLOWED_ORIGINS=https://iamamonkeylol.github.io` for the current GitHub Pages site. The host must provide HTTPS.

In the Jarvis website, open **Connection & setup** and save `https://YOUR-BACKEND-HOST/chat`. No provider key belongs in that field. This backend is not deployed by the GitHub Pages workflow.

The service accepts the website's `{messages}` JSON format and returns `{reply}`. It allows 3 concurrent upstream calls and defaults to 100 requests per UTC day **per process**. Limits reset on restart and are shared by all visitors. CORS is a browser restriction, not authentication: non-browser callers can forge an Origin header. For a public launch, add user authentication and durable shared rate limits at the hosting gateway, and configure provider-side usage controls. This implementation is a bounded preview backend, not a full public account system.

Run automated checks with `node --test backend/server.test.mjs`. Tests use simulated provider replies and spend no API credits.
