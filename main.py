import argparse
import ast
from collections import Counter
import csv
from datetime import datetime, timezone
from html import escape
from io import StringIO
import json
import os
import re
import subprocess
import threading
import tkinter as tk
import tokenize
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_EXCLUDED_DIRECTORIES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
SUPPORTED_SUFFIXES = {".py"}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
MAX_FILE_LINES = 1_000
VPN_CONFIG_PATH = Path(os.getenv("APPDATA", Path.home())) / "Jarvis" / "vpn_clients.json"
RISKY_CALLS = {
    "eval": ("high", "Security", "Avoid eval(); parse or validate untrusted input explicitly."),
    "exec": ("high", "Security", "Avoid exec(); use a constrained, explicit dispatch table."),
    "pickle.load": ("high", "Security", "Do not deserialize untrusted pickle data."),
    "subprocess.call": ("medium", "Reliability", "Prefer subprocess.run(..., check=True) and avoid shell=True."),
    "subprocess.Popen": ("medium", "Reliability", "Validate command arguments and avoid shell=True."),
    "os.system": ("high", "Security", "Use subprocess.run with a list of validated arguments instead."),
    "yaml.load": ("high", "Security", "Use yaml.safe_load() for untrusted YAML content."),
    "marshal.load": ("high", "Security", "Do not deserialize untrusted marshal data."),
}
WEAK_HASHES = {"hashlib.md5", "hashlib.sha1"}
HTTP_CALLS = {
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.patch",
    "requests.delete",
    "requests.request",
}
SENSITIVE_NAME = re.compile(r"(api[_-]?key|password|passwd|secret|token|private[_-]?key)", re.I)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    severity: str
    category: str
    message: str
    suggestion: str


@dataclass(frozen=True)
class FileSummary:
    path: str
    lines: int
    functions: int
    classes: int
    imports: int
    complexity: int
    is_test: bool


@dataclass(frozen=True)
class AnalysisReport:
    root: str
    files: list[FileSummary]
    findings: list[Finding]
    skipped: list[str]
    generated_at: str

    def as_dict(self):
        return {
            "report_version": 1,
            "root": self.root,
            "generated_at": self.generated_at,
            "metrics": self.metrics,
            "files": [asdict(item) for item in self.files],
            "findings": [asdict(item) for item in self.findings],
            "skipped": self.skipped,
        }

    @property
    def metrics(self):
        severity_counts = Counter(item.severity for item in self.findings)
        category_counts = Counter(item.category for item in self.findings)
        return {
            "files": len(self.files),
            "lines": sum(item.lines for item in self.files),
            "functions": sum(item.functions for item in self.files),
            "classes": sum(item.classes for item in self.files),
            "imports": sum(item.imports for item in self.files),
            "test_files": sum(item.is_test for item in self.files),
            "average_complexity": round(
                sum(item.complexity for item in self.files) / len(self.files), 1
            )
            if self.files
            else 0,
            "findings": len(self.findings),
            "severity_counts": dict(severity_counts),
            "category_counts": dict(category_counts),
        }

    def as_markdown(self):
        metrics = self.metrics
        lines = [
            "# Jarvis analysis report",
            "",
            f"**Project:** `{self.root}`",
            f"**Generated:** {self.generated_at}",
            "",
            "## Summary",
            "",
            f"- {metrics['files']} files, {metrics['lines']} lines, "
            f"{metrics['functions']} functions, {metrics['classes']} classes, "
            f"{metrics['test_files']} test files",
            f"- {metrics['findings']} findings: "
            + ", ".join(
                f"{severity} {metrics['severity_counts'].get(severity, 0)}"
                for severity in ("high", "medium", "low", "info")
            ),
            "",
            "## Findings",
            "",
            "| Severity | Location | Category | Finding | Suggested fix |",
            "| --- | --- | --- | --- | --- |",
        ]
        for item in self.findings:
            lines.append(
                f"| {item.severity.upper()} | `{item.path}:{item.line}` | "
                f"{item.category} | {item.message} | {item.suggestion} |"
            )
        if self.skipped:
            lines.extend(["", "## Skipped files", ""])
            lines.extend(f"- `{item}`" for item in self.skipped)
        return "\n".join(lines) + "\n"

    def as_csv(self):
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["severity", "path", "line", "category", "message", "suggestion"])
        for item in self.findings:
            writer.writerow(
                [item.severity, item.path, item.line, item.category, item.message, item.suggestion]
            )
        return output.getvalue()

    def as_html(self):
        rows = "\n".join(
            "<tr>"
            f"<td>{escape(item.severity.upper())}</td>"
            f"<td>{escape(f'{item.path}:{item.line}')}</td>"
            f"<td>{escape(item.category)}</td>"
            f"<td>{escape(item.message)}</td>"
            f"<td>{escape(item.suggestion)}</td>"
            "</tr>"
            for item in self.findings
        )
        metrics = self.metrics
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Jarvis analysis report</title>"
            "<style>body{font-family:system-ui;margin:2rem;color:#1f2937}"
            "table{border-collapse:collapse;width:100%}th,td{border:1px solid #d1d5db;"
            "padding:.5rem;text-align:left;vertical-align:top}th{background:#f3f4f6}</style>"
            "</head><body>"
            "<h1>Jarvis analysis report</h1>"
            f"<p><strong>Project:</strong> {escape(self.root)}<br>"
            f"<strong>Generated:</strong> {escape(self.generated_at)}</p>"
            f"<p>{metrics['files']} files, {metrics['lines']} lines, "
            f"{metrics['findings']} findings</p>"
            "<table><thead><tr><th>Severity</th><th>Location</th><th>Category</th>"
            "<th>Finding</th><th>Suggested fix</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></body></html>"
        )


def iter_python_files(root: Path, excluded_directories=DEFAULT_EXCLUDED_DIRECTORIES):
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in excluded_directories and not name.startswith(".")
        )
        for filename in sorted(filenames):
            path = Path(directory, filename)
            if path.suffix.lower() in SUPPORTED_SUFFIXES:
                yield path


def normalize_url(value):
    value = value.strip()
    if not value:
        raise ValueError("Enter a website address.")
    if not re.match(r"https?://", value, re.I):
        value = f"https://{value}"
    return value


def load_vpn_clients(path=VPN_CONFIG_PATH):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not load VPN client settings: {error}") from error
    if not isinstance(data, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("name"), str)
        or not isinstance(item.get("path"), str)
        for item in data
    ):
        raise RuntimeError("VPN client settings are invalid.")
    return data


def save_vpn_clients(clients, path=VPN_CONFIG_PATH):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(clients, indent=2), encoding="utf-8")


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


class PythonInspector(ast.NodeVisitor):
    def __init__(self, relative_path, max_function_lines=75, max_complexity=10):
        self.relative_path = str(relative_path)
        self.max_function_lines = max_function_lines
        self.max_complexity = max_complexity
        self.findings = []
        self.functions = 0
        self.classes = 0
        self.imports = 0
        self.complexity = 1
        self.function_complexities = []

    def visit_Module(self, node):
        if not ast.get_docstring(node):
            self.add(
                node,
                "low",
                "Documentation",
                "Module has no docstring.",
                "Add a concise module docstring describing its purpose.",
            )
        self.generic_visit(node)

    def add(self, node, severity, category, message, suggestion):
        self.findings.append(
            Finding(
                self.relative_path,
                getattr(node, "lineno", 1),
                severity,
                category,
                message,
                suggestion,
            )
        )

    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

    def _visit_function(self, node):
        self.functions += 1
        end_line = getattr(node, "end_lineno", node.lineno)
        if end_line - node.lineno + 1 > self.max_function_lines:
            self.add(
                node,
                "medium",
                "Maintainability",
                f"Function '{node.name}' is {end_line - node.lineno + 1} lines long.",
                "Split it into smaller functions with one responsibility each.",
            )
        if len(node.args.args) + len(node.args.kwonlyargs) > 7:
            self.add(
                node,
                "medium",
                "Maintainability",
                f"Function '{node.name}' has many parameters.",
                "Group related arguments into a small configuration object.",
            )
        if not node.name.startswith("_") and not ast.get_docstring(node):
            self.add(
                node,
                "low",
                "Documentation",
                f"Public function '{node.name}' has no docstring.",
                "Document the function's purpose, inputs, and return value.",
            )
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.add(
                    node,
                    "medium",
                    "Reliability",
                    f"Function '{node.name}' uses a mutable default argument.",
                    "Use None as the default and create the mutable value inside the function.",
                )
                break
        self.function_complexities.append(1)
        self.generic_visit(node)
        complexity = self.function_complexities.pop()
        if complexity > self.max_complexity:
            self.add(
                node,
                "medium",
                "Maintainability",
                f"Function '{node.name}' has cyclomatic complexity {complexity}.",
                "Extract decision-heavy branches into small, named helpers.",
            )

    def visit_ClassDef(self, node):
        self.classes += 1
        if not node.name.startswith("_") and not ast.get_docstring(node):
            self.add(
                node,
                "low",
                "Documentation",
                f"Public class '{node.name}' has no docstring.",
                "Document the class responsibility and its main collaboration points.",
            )
        self.generic_visit(node)

    def visit_Import(self, node):
        self.imports += len(node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.imports += len(node.names)
        if node.names and node.names[0].name == "*":
            self.add(
                node,
                "medium",
                "Maintainability",
                "Wildcard import obscures where names come from.",
                "Import the names used by this module explicitly.",
            )
        self.generic_visit(node)

    def visit_Call(self, node):
        name = dotted_name(node.func)
        if name == "print":
            self.add(
                node,
                "info",
                "Quality",
                "Debug print call found.",
                "Use the logging module for application diagnostics.",
            )
        if name == "open" and not any(keyword.arg == "encoding" for keyword in node.keywords):
            self.add(
                node,
                "low",
                "Portability",
                "File open call does not specify an encoding.",
                "Specify encoding='utf-8' for text files.",
            )
        if name in RISKY_CALLS:
            severity, category, suggestion = RISKY_CALLS[name]
            self.add(node, severity, category, f"Potentially risky call: {name}().", suggestion)
        if name in WEAK_HASHES:
            self.add(
                node,
                "medium",
                "Security",
                f"Weak cryptographic hash: {name}().",
                "Use SHA-256 or a purpose-built password hashing algorithm.",
            )
        if name in HTTP_CALLS and not any(keyword.arg == "timeout" for keyword in node.keywords):
            self.add(
                node,
                "medium",
                "Reliability",
                f"HTTP request {name}() has no timeout.",
                "Set an explicit timeout to prevent the application from hanging.",
            )
        if name in HTTP_CALLS and any(
            keyword.arg == "verify"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False
            for keyword in node.keywords
        ):
            self.add(
                node,
                "high",
                "Security",
                f"HTTP request {name}() disables TLS certificate verification.",
                "Keep certificate verification enabled and configure trusted certificates if needed.",
            )
        if name.endswith(".execute") and node.args and isinstance(
            node.args[0], (ast.BinOp, ast.JoinedStr)
        ):
            self.add(
                node,
                "high",
                "Security",
                "SQL query is assembled with string interpolation.",
                "Use parameterized query placeholders and pass values separately.",
            )
        if name == "subprocess.run" and not any(
            keyword.arg == "check" and isinstance(keyword.value, ast.Constant) and keyword.value.value
            for keyword in node.keywords
        ):
            self.add(
                node,
                "low",
                "Reliability",
                "subprocess.run() does not require a successful exit status.",
                "Pass check=True or explicitly handle unsuccessful return codes.",
            )
        if name == "breakpoint":
            self.add(
                node,
                "info",
                "Quality",
                "Debugger breakpoint found.",
                "Remove the breakpoint before release.",
            )
        if name in {"subprocess.call", "subprocess.Popen"} and any(
            keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value
            for keyword in node.keywords
        ):
            self.add(
                node,
                "high",
                "Security",
                "subprocess call enables shell=True.",
                "Pass a validated argument list and leave shell disabled.",
            )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == "Exception"):
            self.add(
                node,
                "medium",
                "Reliability",
                "Broad exception handler can hide failures.",
                "Catch the specific expected exception and report unexpected failures.",
            )
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.add(
                node,
                "medium",
                "Reliability",
                "Exception handler silently ignores an error.",
                "Handle the expected condition or log context before continuing.",
            )
        self.generic_visit(node)

    def visit_Global(self, node):
        self.add(
            node,
            "low",
            "Maintainability",
            f"Global state declaration: {', '.join(node.names)}.",
            "Prefer passing state explicitly or encapsulating it in an object.",
        )
        self.generic_visit(node)

    def visit_Assign(self, node):
        self._check_sensitive_assignment(node.targets, node.value, node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self._check_sensitive_assignment([node.target], node.value, node)
        self.generic_visit(node)

    def _check_sensitive_assignment(self, targets, value, node):
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str) or len(value.value) < 8:
            return
        names = [target.id for target in targets if isinstance(target, ast.Name)]
        if any(SENSITIVE_NAME.search(name) for name in names):
            self.add(
                node,
                "high",
                "Security",
                f"Possible hard-coded credential in '{names[0]}'.",
                "Load secrets from environment variables or a dedicated secrets manager.",
            )

    def visit_Assert(self, node):
        self.add(
            node,
            "low",
            "Reliability",
            "Assert statement may be removed when Python runs with optimizations.",
            "Raise an explicit exception for runtime validation.",
        )
        self.generic_visit(node)

    def _visit_branch(self, node):
        self.complexity += 1
        if self.function_complexities:
            self.function_complexities[-1] += 1
        self.generic_visit(node)

    visit_If = _visit_branch
    visit_For = _visit_branch
    visit_AsyncFor = _visit_branch
    visit_While = _visit_branch
    visit_Try = _visit_branch
    visit_BoolOp = _visit_branch


def comment_findings(source, relative_path):
    findings = []
    try:
        tokens = tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__)
        for token in tokens:
            if token.type == tokenize.COMMENT and re.search(r"\b(TODO|FIXME|XXX)\b", token.string, re.I):
                findings.append(
                    Finding(
                        str(relative_path),
                        token.start[0],
                        "info",
                        "Maintenance",
                        f"Unresolved marker: {token.string.strip()}",
                        "Create a tracked task or resolve the marker before release.",
                    )
                )
    except tokenize.TokenError:
        pass
    return findings


def analyze_project(
    directory,
    max_function_lines=75,
    max_complexity=10,
    max_file_lines=MAX_FILE_LINES,
    excluded_directories=None,
    progress=None,
):
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError("Select an existing project folder.")

    ignored = DEFAULT_EXCLUDED_DIRECTORIES | set(excluded_directories or ())
    paths = list(iter_python_files(root, ignored))
    files, findings, skipped = [], [], []
    for index, path in enumerate(paths, start=1):
        relative_path = path.relative_to(root)
        if progress:
            progress(index, len(paths), str(relative_path))
        try:
            source = path.read_text(encoding="utf-8")
            line_count = len(source.splitlines())
            if line_count > max_file_lines:
                skipped.append(
                    f"{relative_path}: {line_count} lines exceeds the {max_file_lines}-line limit"
                )
                continue
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as error:
            skipped.append(f"{relative_path}: {error}")
            continue

        inspector = PythonInspector(relative_path, max_function_lines, max_complexity)
        inspector.visit(tree)
        files.append(
            FileSummary(
                str(relative_path),
                line_count,
                inspector.functions,
                inspector.classes,
                inspector.imports,
                inspector.complexity,
                relative_path.name.startswith("test_") or "tests" in relative_path.parts,
            )
        )
        findings.extend([*inspector.findings, *comment_findings(source, relative_path)])

    findings.sort(key=lambda item: (SEVERITY_ORDER[item.severity], item.path, item.line))
    return AnalysisReport(
        str(root),
        files,
        findings,
        skipped,
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def create_ai_review(report, endpoint, model):
    findings = [asdict(item) for item in report.findings[:30]]
    prompt = (
        "Review these static-analysis findings. Prioritize concrete fixes, explain the "
        "highest risks, and propose small safe code changes. Do not claim to have inspected "
        "code that is not included.\n\n"
        + json.dumps({"root": report.root, "findings": findings}, indent=2)
    )
    payload = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}
    ).encode("utf-8")
    request = Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"AI review failed: {error}") from error
    content = body.get("message", {}).get("content")
    if not content:
        raise RuntimeError("AI review returned no message content.")
    return content


def ollama_models(endpoint="http://127.0.0.1:11434/api/tags"):
    try:
        with urlopen(endpoint, timeout=3) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return []
    return [
        item["name"]
        for item in body.get("models", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    ]


class JarvisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Jarvis Project Analyzer")
        self.root.geometry("1380x900")
        self.root.minsize(1080, 720)
        self.report = None
        self.directory = tk.StringVar()
        self.severity = tk.StringVar(value="All")
        self.category = tk.StringVar(value="All")
        self.search = tk.StringVar()
        self.max_function_lines = tk.IntVar(value=75)
        self.max_complexity = tk.IntVar(value=10)
        self.extra_ignored_directories = tk.StringVar()
        self.status = tk.StringVar(value="Choose a project folder to begin.")
        self.finding_count = tk.StringVar(value="No analysis yet")
        self.metric_values = {
            key: tk.StringVar(value="—")
            for key in ("files", "lines", "functions", "findings", "high", "medium")
        }
        self.visible_findings = []
        self._build_ui()

    def _build_ui(self):
        self._configure_styles()
        frame = ttk.Frame(self.root, style="App.TFrame", padding=22)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)

        header = ttk.Frame(frame, style="App.TFrame")
        header.grid(row=0, column=0, sticky=tk.EW, pady=(0, 18))
        brand = ttk.Frame(header, style="App.TFrame")
        brand.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(brand, text="J", style="BrandMark.TLabel", padding=(12, 7)).pack(side=tk.LEFT, padx=(0, 12))
        title_block = ttk.Frame(brand, style="App.TFrame")
        title_block.pack(side=tk.LEFT, anchor=tk.CENTER)
        ttk.Label(title_block, text="Jarvis", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(title_block, text="PYTHON PROJECT ANALYZER", style="App.Eyebrow.TLabel").pack(
            anchor=tk.W, pady=(2, 0)
        )
        ttk.Button(header, text="VPN clients", command=self.manage_vpn_clients).pack(side=tk.RIGHT)
        ttk.Button(header, text="Browser", command=self.open_browser_dialog).pack(side=tk.RIGHT, padx=(0, 8))

        project = ttk.Frame(frame, style="Panel.TFrame", padding=16)
        project.grid(row=1, column=0, sticky=tk.EW, pady=(0, 14))
        project.columnconfigure(1, weight=1)
        ttk.Label(project, text="PROJECT WORKSPACE", style="Eyebrow.TLabel").grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 8)
        )
        ttk.Entry(project, textvariable=self.directory).grid(
            row=1, column=0, columnspan=2, sticky=tk.EW, padx=(0, 8)
        )
        ttk.Button(project, text="Browse", command=self.choose_folder).grid(row=1, column=2, sticky=tk.E)

        settings = ttk.Frame(project, style="Panel.TFrame")
        settings.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=(14, 0))
        ttk.Label(settings, text="Function length >", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Spinbox(
            settings, from_=10, to=500, textvariable=self.max_function_lines, width=6
        ).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Label(settings, text="lines", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(settings, text="Complexity >", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Spinbox(
            settings, from_=2, to=100, textvariable=self.max_complexity, width=5
        ).pack(side=tk.LEFT, padx=(8, 18))
        ttk.Label(settings, text="Ignore folders", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Entry(settings, textvariable=self.extra_ignored_directories, width=28).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 12)
        )
        self.scan_button = ttk.Button(
            settings, text="Analyze project", style="Primary.TButton", command=self.start_analysis
        )
        self.scan_button.pack(side=tk.RIGHT)

        actions = ttk.Frame(project, style="Panel.TFrame")
        actions.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=(14, 0))
        ttk.Button(actions, text="AI review", command=self.start_ai_review).pack(side=tk.LEFT)
        ttk.Label(actions, text="EXPORT", style="Eyebrow.TLabel").pack(side=tk.LEFT, padx=(18, 8))
        ttk.Button(actions, text="JSON", command=self.export_json).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(actions, text="Markdown", command=self.export_markdown).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(actions, text="CSV", command=self.export_csv).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(actions, text="HTML", command=self.export_html).pack(side=tk.LEFT)

        metrics = ttk.Frame(frame, style="App.TFrame")
        metrics.grid(row=2, column=0, sticky=tk.EW, pady=(0, 14))
        metric_cards = (
            ("files", "PYTHON FILES"),
            ("lines", "LINES ANALYZED"),
            ("functions", "FUNCTIONS"),
            ("findings", "FINDINGS"),
            ("high", "HIGH SEVERITY"),
            ("medium", "MEDIUM SEVERITY"),
        )
        for column, (key, label) in enumerate(metric_cards):
            metrics.columnconfigure(column, weight=1, uniform="metrics")
            card = ttk.Frame(metrics, style="MetricCard.TFrame", padding=(14, 12))
            card.grid(row=0, column=column, sticky=tk.EW, padx=(0 if column == 0 else 6, 0 if column == len(metric_cards) - 1 else 6))
            ttk.Label(card, text=label, style="MetricLabel.TLabel").pack(anchor=tk.W)
            ttk.Label(card, textvariable=self.metric_values[key], style="MetricValue.TLabel").pack(
                anchor=tk.W, pady=(7, 0)
            )

        results = ttk.Frame(frame, style="Panel.TFrame", padding=16)
        results.grid(row=3, column=0, sticky=tk.NSEW)
        results.columnconfigure(0, weight=1)
        results.rowconfigure(2, weight=1)
        heading = ttk.Frame(results, style="Panel.TFrame")
        heading.grid(row=0, column=0, sticky=tk.EW, pady=(0, 12))
        ttk.Label(heading, text="Findings", style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Label(heading, textvariable=self.finding_count, style="Muted.TLabel").pack(
            side=tk.LEFT, padx=(10, 0)
        )
        self.skipped_button = ttk.Button(
            heading, text="Skipped files (0)", command=self.show_skipped_files, state=tk.DISABLED
        )
        self.skipped_button.pack(side=tk.RIGHT)

        filters = ttk.Frame(results, style="Panel.TFrame")
        filters.grid(row=1, column=0, sticky=tk.EW, pady=(0, 12))
        ttk.Label(filters, text="Severity", style="Muted.TLabel").pack(side=tk.LEFT)
        severity_box = ttk.Combobox(
            filters,
            textvariable=self.severity,
            values=("All", "High", "Medium", "Low", "Info"),
            width=10,
            state="readonly",
        )
        severity_box.pack(side=tk.LEFT, padx=(8, 14))
        severity_box.bind("<<ComboboxSelected>>", lambda _: self.render_findings())
        ttk.Label(filters, text="Category", style="Muted.TLabel").pack(side=tk.LEFT)
        self.category_box = ttk.Combobox(
            filters, textvariable=self.category, values=("All",), width=16, state="readonly"
        )
        self.category_box.pack(side=tk.LEFT, padx=(8, 14))
        self.category_box.bind("<<ComboboxSelected>>", lambda _: self.render_findings())
        ttk.Label(filters, text="Search", style="Muted.TLabel").pack(side=tk.LEFT)
        search = ttk.Entry(filters, textvariable=self.search)
        search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.search.trace_add("write", lambda *_: self.render_findings())

        panes = ttk.Panedwindow(results, orient=tk.HORIZONTAL)
        panes.grid(row=2, column=0, sticky=tk.NSEW)
        finding_panel = ttk.Frame(panes, style="Panel.TFrame")
        detail_panel = ttk.Frame(panes, style="Detail.TFrame", padding=16)
        panes.add(finding_panel, weight=3)
        panes.add(detail_panel, weight=2)
        finding_panel.columnconfigure(0, weight=1)
        finding_panel.rowconfigure(0, weight=1)
        self.findings_tree = ttk.Treeview(
            finding_panel,
            columns=("severity", "location", "category", "finding"),
            show="headings",
            selectmode="browse",
        )
        self.findings_tree.heading("severity", text="SEVERITY")
        self.findings_tree.heading("location", text="LOCATION")
        self.findings_tree.heading("category", text="CATEGORY")
        self.findings_tree.heading("finding", text="FINDING")
        self.findings_tree.column("severity", width=96, minwidth=82, stretch=False, anchor=tk.W)
        self.findings_tree.column("location", width=210, minwidth=150, stretch=False, anchor=tk.W)
        self.findings_tree.column("category", width=132, minwidth=100, stretch=False, anchor=tk.W)
        self.findings_tree.column("finding", width=410, minwidth=240, stretch=True, anchor=tk.W)
        for severity, color in (
            ("high", "#fca5a5"),
            ("medium", "#fcd34d"),
            ("low", "#93c5fd"),
            ("info", "#67e8f9"),
        ):
            self.findings_tree.tag_configure(severity, foreground=color)
        self.findings_tree.grid(row=0, column=0, sticky=tk.NSEW)
        tree_scroll = ttk.Scrollbar(finding_panel, orient=tk.VERTICAL, command=self.findings_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky=tk.NS)
        tree_xscroll = ttk.Scrollbar(
            finding_panel, orient=tk.HORIZONTAL, command=self.findings_tree.xview
        )
        tree_xscroll.grid(row=1, column=0, sticky=tk.EW)
        self.findings_tree.configure(
            yscrollcommand=tree_scroll.set, xscrollcommand=tree_xscroll.set
        )
        self.findings_tree.bind("<<TreeviewSelect>>", self._show_selected_finding)

        ttk.Label(detail_panel, text="FINDING DETAILS", style="Detail.Eyebrow.TLabel").pack(anchor=tk.W)
        self.detail_severity = ttk.Label(detail_panel, text="—", style="Muted.TLabel")
        self.detail_severity.pack(anchor=tk.W, pady=(14, 4))
        self.detail_title = ttk.Label(
            detail_panel, text="Select a finding", style="Detail.Section.TLabel", wraplength=330
        )
        self.detail_title.pack(anchor=tk.W, fill=tk.X)
        self.detail_location = ttk.Label(
            detail_panel, text="", style="Detail.Muted.TLabel", wraplength=330
        )
        self.detail_location.pack(anchor=tk.W, pady=(6, 18))
        ttk.Label(detail_panel, text="DESCRIPTION", style="Detail.Eyebrow.TLabel").pack(anchor=tk.W)
        self.detail_message = ttk.Label(
            detail_panel, text="Run an analysis to explore project findings.", style="DetailText.TLabel",
            wraplength=330, justify=tk.LEFT,
        )
        self.detail_message.pack(anchor=tk.W, fill=tk.X, pady=(7, 18))
        ttk.Label(detail_panel, text="SUGGESTED ACTION", style="Detail.Eyebrow.TLabel").pack(anchor=tk.W)
        self.detail_suggestion = ttk.Label(
            detail_panel, text="", style="DetailText.TLabel", wraplength=330, justify=tk.LEFT
        )
        self.detail_suggestion.pack(anchor=tk.W, fill=tk.X, pady=(7, 0))

        footer = ttk.Frame(frame, style="App.TFrame")
        footer.grid(row=4, column=0, sticky=tk.EW, pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status, style="App.Muted.TLabel").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 14)
        )
        self.progress = ttk.Progressbar(footer, mode="determinate", length=220, style="Jarvis.Horizontal.TProgressbar")
        self.progress.grid(row=0, column=1, sticky=tk.E)

    def _configure_styles(self):
        self.root.configure(background="#0b1220")
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("App.TFrame", background="#0b1220")
        style.configure("Panel.TFrame", background="#111c30")
        style.configure("MetricCard.TFrame", background="#111c30")
        style.configure("Detail.TFrame", background="#0e192b")
        style.configure("TLabel", background="#0b1220", foreground="#e2e8f0")
        style.configure("Panel.TLabel", background="#111c30", foreground="#e2e8f0")
        style.configure("Detail.TLabel", background="#0e192b", foreground="#e2e8f0")
        style.configure("Title.TLabel", background="#0b1220", foreground="#f8fafc", font=("Segoe UI", 23, "bold"))
        style.configure("BrandMark.TLabel", background="#06b6d4", foreground="#082f49", font=("Segoe UI", 17, "bold"))
        style.configure("Eyebrow.TLabel", background="#111c30", foreground="#67e8f9", font=("Segoe UI", 8, "bold"))
        style.configure("App.Eyebrow.TLabel", background="#0b1220", foreground="#67e8f9", font=("Segoe UI", 8, "bold"))
        style.configure("Detail.Eyebrow.TLabel", background="#0e192b", foreground="#67e8f9", font=("Segoe UI", 8, "bold"))
        style.configure("Muted.TLabel", background="#111c30", foreground="#94a3b8")
        style.configure("App.Muted.TLabel", background="#0b1220", foreground="#94a3b8")
        style.configure("Detail.Muted.TLabel", background="#0e192b", foreground="#94a3b8")
        style.configure("Section.TLabel", background="#111c30", foreground="#f1f5f9", font=("Segoe UI", 12, "bold"))
        style.configure("Detail.Section.TLabel", background="#0e192b", foreground="#f1f5f9", font=("Segoe UI", 12, "bold"))
        style.configure("MetricLabel.TLabel", background="#111c30", foreground="#94a3b8", font=("Segoe UI", 8, "bold"))
        style.configure("MetricValue.TLabel", background="#111c30", foreground="#f8fafc", font=("Segoe UI", 21, "bold"))
        style.configure("DetailText.TLabel", background="#0e192b", foreground="#cbd5e1", font=("Segoe UI", 10))
        style.configure("TButton", background="#1e293b", foreground="#e2e8f0", padding=(11, 7), borderwidth=0)
        style.map("TButton", background=[("active", "#334155"), ("disabled", "#172033")])
        style.configure("Primary.TButton", background="#0891b2", foreground="#f0fdfa", font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#06b6d4")])
        style.configure(
            "TEntry", fieldbackground="#0b1220", foreground="#e2e8f0", insertcolor="#e2e8f0",
            bordercolor="#26364f", padding=8,
        )
        style.configure(
            "TSpinbox", fieldbackground="#0b1220", foreground="#e2e8f0", arrowcolor="#94a3b8",
            bordercolor="#26364f", padding=5,
        )
        style.configure(
            "TCombobox", fieldbackground="#0b1220", foreground="#e2e8f0", arrowcolor="#94a3b8",
            bordercolor="#26364f", padding=7,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#0b1220")],
            foreground=[("readonly", "#e2e8f0")],
            selectbackground=[("readonly", "#0b1220")],
            selectforeground=[("readonly", "#e2e8f0")],
        )
        style.configure(
            "Treeview", background="#0b1220", fieldbackground="#0b1220", foreground="#cbd5e1",
            rowheight=31, borderwidth=0, font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading", background="#17243a", foreground="#94a3b8",
            font=("Segoe UI", 8, "bold"), padding=(8, 9), relief="flat",
        )
        style.map("Treeview", background=[("selected", "#164e63")], foreground=[("selected", "#ecfeff")])
        style.configure(
            "Jarvis.Horizontal.TProgressbar", troughcolor="#17243a", background="#06b6d4",
            bordercolor="#17243a", lightcolor="#06b6d4", darkcolor="#06b6d4",
        )
        for severity, color in (
            ("High", "#fca5a5"),
            ("Medium", "#fcd34d"),
            ("Low", "#93c5fd"),
            ("Info", "#67e8f9"),
        ):
            style.configure(
                f"Severity.{severity}.TLabel",
                background="#0e192b",
                foreground=color,
                font=("Segoe UI", 9, "bold"),
            )

    def choose_folder(self):
        directory = filedialog.askdirectory(title="Select a project folder")
        if directory:
            self.directory.set(directory)

    def start_analysis(self):
        if not self.directory.get():
            self.choose_folder()
        if not self.directory.get():
            return
        self.progress.configure(value=0)
        self.status.set("Discovering Python files...")
        self.scan_button.configure(state=tk.DISABLED, text="Analyzing...")
        threading.Thread(target=self._analyze_in_background, daemon=True).start()

    def _analyze_in_background(self):
        try:
            report = analyze_project(
                self.directory.get(),
                max_function_lines=self.max_function_lines.get(),
                max_complexity=self.max_complexity.get(),
                excluded_directories={
                    name.strip()
                    for name in self.extra_ignored_directories.get().split(",")
                    if name.strip()
                },
                progress=self._update_progress,
            )
        except (ValueError, OSError) as error:
            self.root.after(0, lambda error=error: self._analysis_failed(error))
            return
        self.root.after(0, lambda: self._complete_analysis(report))

    def _analysis_failed(self, error):
        self.scan_button.configure(state=tk.NORMAL, text="Analyze project")
        self.progress.configure(value=0)
        self.status.set("Analysis failed.")
        messagebox.showerror("Analysis failed", str(error), parent=self.root)

    def _update_progress(self, current, total, path):
        self.root.after(
            0,
            lambda: (
                self.progress.configure(maximum=max(total, 1), value=current),
                self.status.set(f"Analyzing {current}/{total}: {path}"),
            ),
        )

    def _complete_analysis(self, report):
        self.scan_button.configure(state=tk.NORMAL, text="Analyze project")
        self.report = report
        categories = ("All", *sorted({item.category for item in report.findings}))
        self.category_box.configure(values=categories)
        self.category.set("All")
        metrics = report.metrics
        counts = metrics["severity_counts"]
        for key in ("files", "lines", "functions", "findings"):
            self.metric_values[key].set(f"{metrics[key]:,}")
        for key in ("high", "medium"):
            self.metric_values[key].set(f"{counts.get(key, 0):,}")
        self.skipped_button.configure(
            text=f"Skipped files ({len(report.skipped)})",
            state=tk.NORMAL if report.skipped else tk.DISABLED,
        )
        self.status.set(
            f"Analysis complete  |  {metrics['files']:,} Python files  |  "
            f"{metrics['lines']:,} lines  |  {metrics['findings']:,} findings"
        )
        self.render_findings()

    def filtered_findings(self):
        if not self.report:
            return []
        severity = self.severity.get().lower()
        category = self.category.get()
        query = self.search.get().lower().strip()
        return [
            item
            for item in self.report.findings
            if (severity == "all" or item.severity == severity)
            and (category == "All" or item.category == category)
            and (not query or query in " ".join(map(str, asdict(item).values())).lower())
        ]

    def render_findings(self):
        if not self.report:
            return
        findings = self.filtered_findings()
        self.visible_findings = findings
        self.finding_count.set(
            f"{len(findings):,} shown / {len(self.report.findings):,} total"
        )
        self.findings_tree.delete(*self.findings_tree.get_children())
        for index, item in enumerate(findings):
            self.findings_tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    item.severity.upper(),
                    f"{item.path}:{item.line}",
                    item.category,
                    item.message,
                ),
                tags=(item.severity,),
            )
        if findings:
            first = "0"
            self.findings_tree.selection_set(first)
            self.findings_tree.focus(first)
            self._set_finding_details(findings[0])
        else:
            self._show_empty_details()

    def _show_selected_finding(self, _event=None):
        selection = self.findings_tree.selection()
        if not selection:
            return
        self._set_finding_details(self.visible_findings[int(selection[0])])

    def _set_finding_details(self, finding):
        severity = finding.severity.capitalize()
        self.detail_severity.configure(text=severity, style=f"Severity.{severity}.TLabel")
        self.detail_title.configure(text=finding.category)
        self.detail_location.configure(text=f"{finding.path}:{finding.line}  ·  {finding.category}")
        self.detail_message.configure(text=finding.message)
        self.detail_suggestion.configure(text=finding.suggestion)

    def _show_empty_details(self):
        self.detail_severity.configure(text="No findings", style="Detail.Muted.TLabel")
        self.detail_title.configure(text="No matching findings")
        self.detail_location.configure(text="")
        if self.report.findings:
            message = "Try adjusting the severity, category, or search filters."
        else:
            message = "The analyzer did not find any issues in this project."
        self.detail_message.configure(text=message)
        self.detail_suggestion.configure(text="")

    def show_skipped_files(self):
        if not self.report or not self.report.skipped:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Skipped files")
        dialog.geometry("760x420")
        dialog.transient(self.root)
        content = scrolledtext.ScrolledText(
            dialog,
            wrap=tk.WORD,
            state=tk.NORMAL,
            font=("Consolas", 10),
            background="#0b1220",
            foreground="#cbd5e1",
            insertbackground="#e2e8f0",
            relief=tk.FLAT,
            padx=12,
            pady=12,
        )
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        content.insert(tk.END, "\n".join(self.report.skipped))
        content.configure(state=tk.DISABLED)

    def export_json(self):
        if not self.report:
            messagebox.showinfo("Nothing to export", "Analyze a project first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export analysis", defaultextension=".json", filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.report.as_dict(), indent=2), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Export failed", str(error))
            return
        self.status.set(f"Exported analysis to {path}")

    def export_markdown(self):
        if not self.report:
            messagebox.showinfo("Nothing to export", "Analyze a project first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export Markdown report",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
        )
        if not path:
            return
        try:
            Path(path).write_text(self.report.as_markdown(), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Export failed", str(error))
            return
        self.status.set(f"Exported Markdown report to {path}")

    def open_browser_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Jarvis Browser")
        dialog.transient(self.root)
        dialog.grab_set()
        address = tk.StringVar(value="https://www.google.com")
        ttk.Label(dialog, text="Website address").grid(row=0, column=0, padx=12, pady=(12, 4), sticky=tk.W)
        entry = ttk.Entry(dialog, textvariable=address, width=50)
        entry.grid(row=0, column=1, padx=12, pady=(12, 4))
        ttk.Label(dialog, text="Opens in Jarvis's embedded Edge WebView window.").grid(
            row=1, column=0, columnspan=2, padx=12, pady=4, sticky=tk.W
        )
        ttk.Button(
            dialog, text="Open", command=lambda: self._open_browser(dialog, address.get())
        ).grid(row=2, column=1, padx=12, pady=(4, 12), sticky=tk.E)
        entry.focus_set()
        entry.bind("<Return>", lambda _: self._open_browser(dialog, address.get()))

    def _open_browser(self, dialog, address):
        try:
            url = normalize_url(address)
        except ValueError as error:
            messagebox.showerror("Browser", str(error), parent=dialog)
            return
        dialog.destroy()
        try:
            if getattr(sys, "frozen", False):
                command = [sys.executable, "--browser", url]
            else:
                command = [sys.executable, str(Path(__file__).with_name("jarvis_browser.py")), url]
            subprocess.Popen(command)
        except OSError as error:
            messagebox.showerror("Browser failed", f"Could not launch the browser: {error}")
            return
        self.status.set(f"Opened Jarvis Browser: {url}")

    def manage_vpn_clients(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("VPN clients")
        dialog.transient(self.root)
        dialog.geometry("580x340")
        try:
            clients = load_vpn_clients()
        except RuntimeError as error:
            messagebox.showerror("VPN clients", str(error), parent=dialog)
            dialog.destroy()
            return

        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 6))

        def refresh():
            listbox.delete(0, tk.END)
            for client in clients:
                listbox.insert(tk.END, f"{client['name']} — {client['path']}")

        def add():
            executable = filedialog.askopenfilename(
                parent=dialog,
                title="Select VPN client executable",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")],
            )
            if not executable:
                return
            name = Path(executable).stem
            clients.append({"name": name, "path": executable})
            refresh()

        def remove():
            selection = listbox.curselection()
            if selection:
                clients.pop(selection[0])
                refresh()

        def launch():
            selection = listbox.curselection()
            if not selection:
                messagebox.showinfo("VPN clients", "Select a VPN client to launch.", parent=dialog)
                return
            client = clients[selection[0]]
            executable = Path(client["path"])
            if not executable.is_file():
                messagebox.showerror(
                    "VPN clients",
                    f"Configured executable no longer exists:\n{executable}",
                    parent=dialog,
                )
                return
            try:
                subprocess.Popen([str(executable)])
            except OSError as error:
                messagebox.showerror("VPN clients", f"Could not launch {client['name']}: {error}", parent=dialog)
                return
            self.status.set(f"Launched VPN client: {client['name']}")

        def save():
            try:
                save_vpn_clients(clients)
            except OSError as error:
                messagebox.showerror("VPN clients", f"Could not save settings: {error}", parent=dialog)
                return
            dialog.destroy()

        controls = ttk.Frame(dialog)
        controls.pack(fill=tk.X, padx=12, pady=(0, 12))
        ttk.Button(controls, text="Add executable", command=add).pack(side=tk.LEFT)
        ttk.Button(controls, text="Remove", command=remove).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(controls, text="Launch", command=launch).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(controls, text="Save", command=save).pack(side=tk.RIGHT)
        refresh()

    def export_csv(self):
        self._export_report("CSV", ".csv", [("CSV", "*.csv")], self.report.as_csv)

    def export_html(self):
        self._export_report("HTML", ".html", [("HTML", "*.html")], self.report.as_html)

    def _export_report(self, label, extension, filetypes, render):
        if not self.report:
            messagebox.showinfo("Nothing to export", "Analyze a project first.")
            return
        path = filedialog.asksaveasfilename(
            title=f"Export {label} report",
            defaultextension=extension,
            filetypes=filetypes,
        )
        if not path:
            return
        try:
            Path(path).write_text(render(), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Export failed", str(error))
            return
        self.status.set(f"Exported {label} report to {path}")

    def start_ai_review(self):
        if not self.report:
            messagebox.showinfo("No analysis", "Analyze a project before requesting an AI review.")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Local AI review")
        dialog.transient(self.root)
        dialog.grab_set()
        endpoint = tk.StringVar(value="http://127.0.0.1:11434/api/chat")
        models = ollama_models()
        model = tk.StringVar(value=models[0] if models else "")
        ttk.Label(dialog, text="Ollama endpoint").grid(row=0, column=0, padx=12, pady=(12, 4), sticky=tk.W)
        ttk.Entry(dialog, textvariable=endpoint, width=48).grid(row=0, column=1, padx=12, pady=(12, 4))
        ttk.Label(dialog, text="Model").grid(row=1, column=0, padx=12, pady=4, sticky=tk.W)
        if models:
            ttk.Combobox(dialog, textvariable=model, values=models, width=45, state="readonly").grid(
                row=1, column=1, padx=12, pady=4
            )
        else:
            ttk.Entry(dialog, textvariable=model, width=48).grid(row=1, column=1, padx=12, pady=4)
        connection_status = (
            f"Detected {len(models)} local model(s)." if models else "Ollama was not detected; enter an installed model name."
        )
        ttk.Label(dialog, text=connection_status).grid(
            row=2, column=0, columnspan=2, padx=12, pady=4, sticky=tk.W
        )
        ttk.Label(dialog, text="Only the analysis findings are sent to this endpoint.").grid(
            row=3, column=0, columnspan=2, padx=12, pady=4, sticky=tk.W
        )
        ttk.Button(
            dialog,
            text="Review",
            command=lambda: self._request_ai_review(dialog, endpoint.get(), model.get()),
        ).grid(row=4, column=1, padx=12, pady=(4, 12), sticky=tk.E)

    def _request_ai_review(self, dialog, endpoint, model):
        dialog.destroy()
        self.status.set("Requesting local AI review...")
        threading.Thread(target=self._ai_review_in_background, args=(endpoint, model), daemon=True).start()

    def _ai_review_in_background(self, endpoint, model):
        try:
            review = create_ai_review(self.report, endpoint, model)
        except RuntimeError as error:
            self.root.after(
                0, lambda error=error: messagebox.showerror("AI review failed", str(error), parent=self.root)
            )
            return
        self.root.after(0, lambda: self._show_ai_review(review))

    def _show_ai_review(self, review):
        dialog = tk.Toplevel(self.root)
        dialog.title("Local AI review")
        text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=100, height=32)
        text.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        text.insert(tk.END, review)
        text.configure(state=tk.DISABLED)
        self.status.set("Local AI review complete.")


def run_cli(arguments):
    parser = argparse.ArgumentParser(description="Analyze a Python project with Jarvis.")
    parser.add_argument("--analyze", metavar="DIRECTORY", help="Project folder to analyze.")
    parser.add_argument("--browser", metavar="URL", help="Open a URL in Jarvis Browser.")
    parser.add_argument(
        "--format", choices=("json", "markdown", "csv", "html"), default="json", help="Report format."
    )
    parser.add_argument("--output", metavar="PATH", help="Write the report to a file instead of stdout.")
    parser.add_argument(
        "--fail-on",
        choices=tuple(SEVERITY_ORDER),
        help="Exit with status 1 when findings meet or exceed this severity.",
    )
    parser.add_argument(
        "--max-file-lines", type=int, default=MAX_FILE_LINES, help="Skip files over this line count."
    )
    args = parser.parse_args(arguments)
    if args.browser:
        from jarvis_browser import open_browser

        open_browser(normalize_url(args.browser))
        return 0
    if not args.analyze:
        return None
    if args.max_file_lines < 1:
        parser.error("--max-file-lines must be at least 1")
    report = analyze_project(args.analyze, max_file_lines=args.max_file_lines)
    output = {
        "json": lambda: json.dumps(report.as_dict(), indent=2) + "\n",
        "markdown": report.as_markdown,
        "csv": report.as_csv,
        "html": report.as_html,
    }[args.format]()
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on]
        return int(any(SEVERITY_ORDER[item.severity] <= threshold for item in report.findings))
    return 0


def main(arguments=None):
    arguments = sys.argv[1:] if arguments is None else arguments
    if arguments:
        return run_cli(arguments)
    root = tk.Tk()
    JarvisApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
