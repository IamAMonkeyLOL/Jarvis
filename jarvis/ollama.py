"""Small local-only Ollama client using Python's standard library."""
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

from .config import CONTEXT_TOKENS, MODEL, OLLAMA_URL, REPLY_TOKENS


class OllamaError(RuntimeError):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OllamaError("Ollama returned a redirect. Check that the local Ollama app is running.")


class OllamaClient:
    def __init__(self, base_url=OLLAMA_URL, model=MODEL, timeout=180):
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username or parsed.path or parsed.query or parsed.fragment:
            raise ValueError("This starter only connects to http://127.0.0.1 on your own computer.")
        if model != MODEL:
            raise ValueError(f"This starter uses {MODEL}; add other models after the baseline works.")
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        # Never send local chat through an HTTP_PROXY environment setting.
        self.opener = build_opener(ProxyHandler({}), NoRedirects())

    def _open(self, path, body=None, timeout=None):
        request = Request(self.base_url + path, data=json.dumps(body).encode("utf-8") if body is not None else None, headers={"Content-Type": "application/json"})
        try:
            return self.opener.open(request, timeout=timeout or self.timeout)
        except HTTPError as error:
            code = error.code
            error.close()
            if code == 404:
                raise OllamaError("Model or endpoint not found. Run SETUP_MODEL.bat and update Ollama if needed.") from error
            raise OllamaError(f"Ollama returned HTTP {code}. Check the Ollama app and available memory.") from error
        except (URLError, OSError, TimeoutError) as error:
            raise OllamaError("Cannot reach Ollama. Open the Ollama app, wait a moment, then click Check again. A slow first model load can also time out.") from error

    def get_json(self, path):
        try:
            with self._open(path, timeout=3) as response:
                return json.load(response)
        except (ValueError, OSError) as error:
            raise OllamaError("Ollama sent an unreadable response. Restart the Ollama app.") from error

    def check(self):
        payload = self.get_json("/api/tags")
        models = payload.get("models")
        if not isinstance(models, list):
            raise OllamaError("Ollama sent an unexpected model list. Update or restart Ollama.")
        return any(item.get("name") == self.model or item.get("model") == self.model for item in models)

    def stream(self, messages):
        body = {"model": self.model, "messages": messages, "stream": True, "think": False, "keep_alive": "5m", "options": {"num_ctx": CONTEXT_TOKENS, "num_predict": REPLY_TOKENS, "temperature": 0.4}}
        try:
            with self._open("/api/chat", body) as response:
                for raw in response:
                    if not raw.strip():
                        continue
                    try:
                        event = json.loads(raw)
                    except (ValueError, UnicodeError) as error:
                        raise OllamaError("Ollama sent an unreadable stream. Retry the response.") from error
                    if not isinstance(event, dict):
                        raise OllamaError("Ollama sent an unexpected stream response.")
                    if event.get("error"):
                        raise OllamaError("Ollama could not generate the reply. Check the Ollama app for details, close memory-heavy apps, and retry.")
                    yield event
                    if event.get("done") is True:
                        return
                raise OllamaError("The connection ended before the reply finished. Your conversation is saved; you can retry.")
        except (socket.timeout, TimeoutError) as error:
            raise OllamaError("Ollama took too long to respond. The first load can be slow. Check Ollama and retry.") from error
        except (OSError, URLError) as error:
            raise OllamaError("The connection to Ollama was interrupted. Your conversation is saved; you can retry.") from error
