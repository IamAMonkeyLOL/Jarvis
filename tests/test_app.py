"""UI checks use a synthetic Ollama server, never a downloaded model."""
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from jarvis.ollama import OllamaClient
from jarvis.storage import Store
from tests.fake_ollama import fake_server

APP = Path(__file__).resolve().parent.parent / "app.py"


def button(app, label):
    return next(item for item in app.button if item.label == label)


class AppTests(unittest.TestCase):
    def setUp(self):
        st.cache_resource.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "chat.sqlite3"
        self.config = patch("jarvis.config.DB_PATH", self.path)
        self.config.start()

    def tearDown(self):
        st.cache_resource.clear()
        self.config.stop()
        self.temp.cleanup()

    def wait_for_saved_reply(self, app):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            rows = Store(self.path).messages(app.session_state.chat_id)
            if rows and rows[-1]["role"] == "assistant" and rows[-1]["status"] != "pending":
                return rows
            time.sleep(0.02)
        self.fail("Reply did not finish")

    def test_chat_restart_new_chat_and_export(self):
        with fake_server() as (_, url), patch("jarvis.ollama.OllamaClient", return_value=OllamaClient(url)):
            app = AppTest.from_file(str(APP)).run()
            self.assertFalse(app.exception)
            self.assertIn("Ollama is ready", [item.value for item in app.success])
            app.chat_input[0].set_value("My project is a weather station.").run()
            rows = self.wait_for_saved_reply(app)
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(len(rows), 2)
            self.assertIn("weather station", rows[-1]["content"])
            first_id = app.session_state.chat_id
            # A new session reloads persisted messages from SQLite.
            restarted = AppTest.from_file(str(APP)).run()
            self.assertEqual(len(restarted.chat_message), 2)
            self.assertIn("weather station", Store(self.path).export(first_id))
            button(restarted, "＋ New conversation").click().run()
            self.assertNotEqual(restarted.session_state.chat_id, first_id)
            self.assertEqual(len(restarted.chat_message), 0)
            restarted.selectbox[0].select(first_id).run()
            self.assertEqual(len(restarted.chat_message), 2)
            self.assertFalse(restarted.exception)

    def test_failed_reply_shows_retry_and_retains_user_text(self):
        with fake_server("error") as (server, url), patch("jarvis.ollama.OllamaClient", return_value=OllamaClient(url)):
            app = AppTest.from_file(str(APP)).run()
            app.chat_input[0].set_value("Keep this question").run()
            self.wait_for_saved_reply(app)
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            server.mode = "success"
            button(app, "Retry last response").click().run()
            rows = self.wait_for_saved_reply(app)
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[-1]["status"], "complete")


if __name__ == "__main__":
    unittest.main()
