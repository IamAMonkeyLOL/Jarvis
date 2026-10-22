import json
from pathlib import Path
import tempfile
import unittest

from jarvis.context import build_context, estimated_tokens
from jarvis.ollama import OllamaClient, OllamaError
from jarvis.service import start_generation
from jarvis.storage import Store
from tests.fake_ollama import fake_server


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.sqlite3"
        self.store = Store(self.path)

    def tearDown(self):
        self.temp.cleanup()


class StorageTests(StoreCase):
    def test_persists_after_reopen_and_exports_unicode(self):
        chat = self.store.create()
        self.store.add(chat, "user", "Remember my project: café ☕")
        self.store.add(chat, "assistant", "Saved in this conversation.", model="qwen3:8b")
        reopened = Store(self.path)
        self.assertEqual(len(reopened.messages(chat)), 2)
        exported = json.loads(reopened.export(chat))
        self.assertIn("café ☕", exported["messages"][0]["content"])
        self.assertEqual(exported["messages"][1]["model"], "qwen3:8b")

    def test_delete_isolated_and_cascades(self):
        first, second = self.store.create(), self.store.create()
        self.store.add(first, "user", "Delete me")
        self.store.add(second, "user", "Keep me")
        self.store.delete(first)
        self.assertEqual(self.store.messages(first), [])
        self.assertEqual(self.store.messages(second)[0]["content"], "Keep me")

    def test_backup_includes_recent_writes(self):
        chat = self.store.create()
        self.store.add(chat, "user", "Newest message")
        backup = self.store.backup(Path(self.temp.name) / "backup.sqlite3")
        self.assertEqual(Store(backup).messages(chat)[0]["content"], "Newest message")

    def test_restart_recovers_pending_without_claiming_completion(self):
        chat = self.store.create()
        self.store.add(chat, "user", "Hi")
        self.store.add(chat, "assistant", "Part of an answer", "pending")
        self.store.recover_pending()
        self.assertEqual(self.store.messages(chat)[-1]["status"], "interrupted")


class ContextTests(unittest.TestCase):
    def test_keeps_latest_and_whole_recent_turns(self):
        messages = [{"role": "user", "content": "Old question" * 200}, {"role": "assistant", "content": "Old answer" * 200}, {"role": "user", "content": "Recent question"}, {"role": "assistant", "content": "Recent answer"}, {"role": "user", "content": "Current question"}]
        selected, omitted = build_context(messages, budget=500)
        self.assertEqual(omitted, 1)
        self.assertEqual([m["role"] for m in selected], ["system", "user", "assistant", "user"])
        self.assertEqual(selected[-1]["content"], "Current question")
        self.assertLessEqual(sum(estimated_tokens(m["content"]) for m in selected), 500)

    def test_excludes_failed_turn_and_rejects_oversize_current_message(self):
        selected, _ = build_context([{"role": "user", "content": "Old"}, {"role": "assistant", "content": "Wrong partial", "status": "error"}, {"role": "user", "content": "New"}])
        self.assertEqual(len(selected), 2)
        with self.assertRaises(ValueError):
            build_context([{"role": "user", "content": "界" * 3000}])


class TransportTests(unittest.TestCase):
    def test_real_http_stream_and_local_parameters(self):
        with fake_server() as (server, url):
            client = OllamaClient(url)
            self.assertTrue(client.check())
            events = list(client.stream([{"role": "user", "content": "hello"}]))
            self.assertEqual("".join(e.get("message", {}).get("content", "") for e in events), "Synthetic reply: hello")
            body = server.requests[0]
            self.assertFalse(body["think"])
            self.assertEqual(body["options"]["num_ctx"], 4096)
            self.assertTrue(events[-1]["done"])

    def test_failed_and_incomplete_streams_raise(self):
        for mode in ("missing", "error", "malformed", "truncated"):
            with self.subTest(mode=mode), fake_server(mode) as (_, url):
                with self.assertRaises(OllamaError):
                    list(OllamaClient(url).stream([{"role": "user", "content": "hi"}]))

    def test_refuses_remote_endpoints_and_other_models(self):
        for url in ("https://example.com", "http://192.168.1.1:11434", "http://127.0.0.1:11434/api", "http://user@127.0.0.1:11434"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                OllamaClient(url)
        with self.assertRaises(ValueError):
            OllamaClient(model="cloud-model")


class GenerationTests(StoreCase):
    def test_error_retry_does_not_duplicate_user_or_accept_partial_reply(self):
        chat = self.store.create()
        self.store.add(chat, "user", "hello")
        with fake_server("truncated") as (server, url):
            client = OllamaClient(url)
            failed = start_generation(self.store, chat, client)
            self.assertTrue(failed.done.wait(3))
            self.assertEqual(failed.status, "error")
            self.assertIn("Synthetic", self.store.messages(chat)[-1]["content"])
            server.mode = "success"
            retried = start_generation(self.store, chat, client)
            self.assertTrue(retried.done.wait(3))
            self.assertEqual(retried.status, "complete")
            messages = self.store.messages(chat)
            self.assertEqual(len(messages), 2)
            self.assertEqual(server.requests[-1]["messages"][-1]["content"], "hello")
            self.assertFalse(any(item["role"] == "assistant" for item in server.requests[-1]["messages"]))
            self.assertEqual(messages[-1]["metadata"]["eval_count"], 10)

    def test_cancel_saves_interrupted_status(self):
        chat = self.store.create()
        self.store.add(chat, "user", "hello")
        with fake_server("slow") as (_, url):
            job = start_generation(self.store, chat, OllamaClient(url))
            job.cancel.set()
            self.assertTrue(job.done.wait(3))
            self.assertEqual(job.status, "interrupted")
            self.assertEqual(self.store.messages(chat)[-1]["status"], "interrupted")


if __name__ == "__main__":
    unittest.main()
