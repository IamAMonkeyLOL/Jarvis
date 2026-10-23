import contextlib
from io import StringIO
import tempfile
import unittest
from pathlib import Path

from main import (
    analyze_project,
    iter_python_files,
    load_vpn_clients,
    normalize_url,
    run_cli,
    save_vpn_clients,
)


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative_path, content):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_recurses_and_ignores_generated_directories(self):
        self.write("package/module.py", "x = 1\n")
        self.write("node_modules/vendor.py", "x = 2\n")
        self.assertEqual(
            [path.relative_to(self.root).as_posix() for path in iter_python_files(self.root)],
            ["package/module.py"],
        )

    def test_reports_ast_findings_and_skips_invalid_source(self):
        self.write(
            "app.py",
            "from tools import *\n"
            "def too_many(a, b, c, d, e, f, g, h):\n"
            "    print('debug')\n"
            "    try:\n"
            "        return eval('1 + 1')\n"
            "    except Exception:\n"
            "        return None\n",
        )
        self.write("broken.py", "def incomplete(:\n")
        report = analyze_project(self.root, max_function_lines=2)
        messages = [item.message for item in report.findings]
        self.assertEqual(len(report.files), 1)
        self.assertEqual(len(report.skipped), 1)
        self.assertTrue(any("Wildcard import" in message for message in messages))
        self.assertTrue(any("Debug print" in message for message in messages))
        self.assertTrue(any("Potentially risky call: eval" in message for message in messages))
        self.assertTrue(any("Broad exception" in message for message in messages))
        self.assertTrue(any("many parameters" in message for message in messages))
        self.assertTrue(any("lines long" in message for message in messages))

    def test_reports_maintainability_rules_and_exports_markdown(self):
        self.write(
            "quality.py",
            "# TODO: replace this implementation\n"
            "class PublicThing:\n"
            "    pass\n"
            "def complex_default(items=[]):\n"
            "    assert items is not None\n"
            "    if items:\n"
            "        return open('result.txt').read()\n"
            "    return ''\n",
        )
        report = analyze_project(self.root, max_complexity=1)
        messages = [item.message for item in report.findings]
        self.assertTrue(any("Unresolved marker" in message for message in messages))
        self.assertTrue(any("mutable default" in message for message in messages))
        self.assertTrue(any("Assert statement" in message for message in messages))
        self.assertTrue(any("does not specify an encoding" in message for message in messages))
        self.assertTrue(any("cyclomatic complexity" in message for message in messages))
        self.assertTrue(any("has no docstring" in message for message in messages))
        self.assertEqual(report.metrics["files"], 1)
        self.assertIn("# Jarvis analysis report", report.as_markdown())

    def test_honors_extra_ignores_and_file_size_limit(self):
        self.write("excluded/source.py", "x = 1\n")
        self.write("large.py", "\n".join("x = 1" for _ in range(4)))
        report = analyze_project(
            self.root, max_file_lines=3, excluded_directories={"excluded"}
        )
        self.assertEqual(report.files, [])
        self.assertEqual(len(report.skipped), 1)
        self.assertIn("exceeds the 3-line limit", report.skipped[0])

    def test_reports_advanced_security_and_reliability_rules(self):
        self.write(
            "risk.py",
            "import hashlib\n"
            "import requests\n"
            "import subprocess\n"
            "import yaml\n"
            "api_token = 'definitely-a-real-secret'\n"
            "global_value = 1\n"
            "def risky(cursor):\n"
            "    global global_value\n"
            "    hashlib.md5(b'value')\n"
            "    requests.get('https://example.test', verify=False)\n"
            "    cursor.execute(f'SELECT {global_value}')\n"
            "    subprocess.run(['echo', 'hello'])\n"
            "    yaml.load('answer: 42')\n"
            "    breakpoint()\n"
            "    try:\n"
            "        raise ValueError('bad')\n"
            "    except:\n"
            "        pass\n",
        )
        messages = [item.message for item in analyze_project(self.root).findings]
        self.assertTrue(any("hard-coded credential" in message for message in messages))
        self.assertTrue(any("Weak cryptographic hash" in message for message in messages))
        self.assertTrue(any("has no timeout" in message for message in messages))
        self.assertTrue(any("disables TLS" in message for message in messages))
        self.assertTrue(any("SQL query is assembled" in message for message in messages))
        self.assertTrue(any("does not require" in message for message in messages))
        self.assertTrue(any("yaml.load" in message for message in messages))
        self.assertTrue(any("Debugger breakpoint" in message for message in messages))
        self.assertTrue(any("silently ignores" in message for message in messages))
        self.assertTrue(any("Global state" in message for message in messages))

    def test_cli_writes_json_and_returns_failure_threshold(self):
        self.write("app.py", "value = eval('1')\n")
        output = self.root / "report.json"
        with contextlib.redirect_stdout(StringIO()):
            result = run_cli(
                [
                    "--analyze",
                    str(self.root),
                    "--format",
                    "json",
                    "--output",
                    str(output),
                    "--fail-on",
                    "high",
                ]
            )
        self.assertEqual(result, 1)
        report = output.read_text(encoding="utf-8")
        self.assertIn('"report_version": 1', report)
        self.assertIn('"generated_at"', report)

    def test_browser_url_and_vpn_client_settings(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com")
        self.assertEqual(normalize_url("http://localhost:8000"), "http://localhost:8000")
        with self.assertRaises(ValueError):
            normalize_url("  ")
        config = self.root / "vpn_clients.json"
        clients = [{"name": "Example VPN", "path": "C:\\\\Program Files\\\\VPN\\\\client.exe"}]
        save_vpn_clients(clients, config)
        self.assertEqual(load_vpn_clients(config), clients)


if __name__ == "__main__":
    unittest.main()
