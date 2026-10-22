"""A synthetic HTTP fixture. It is not an AI model."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"models": [{"name": "qwen3:8b"}]}).encode())

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(body)
        mode = self.server.mode
        self.send_response(404 if mode == "missing" else 200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        if mode == "missing":
            return
        if mode == "error":
            self.wfile.write(b'{"error":"synthetic model failure"}\n')
            return
        if mode == "malformed":
            self.wfile.write(b'not json\n')
            return
        text = "Synthetic reply: " + body["messages"][-1]["content"]
        chunks = [text[:10], text[10:]]
        try:
            for chunk in chunks:
                if mode == "slow":
                    time.sleep(0.2)
                self.wfile.write((json.dumps({"message": {"role": "assistant", "content": chunk}, "done": False}) + "\n").encode())
                self.wfile.flush()
            if mode != "truncated":
                final = {"message": {"content": ""}, "done": True, "done_reason": "stop", "eval_count": 10, "eval_duration": 1_000_000_000}
                self.wfile.write((json.dumps(final) + "\n").encode())
        except (BrokenPipeError, ConnectionResetError):
            pass


@contextmanager
def fake_server(mode="success"):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.mode = mode
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
