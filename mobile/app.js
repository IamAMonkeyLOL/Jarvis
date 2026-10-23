const rules = [
  {
    severity: "high",
    expression: /\b(?:eval|exec)\s*\(/,
    message: "Dynamic code execution found. Validate input or replace it with explicit logic.",
  },
  {
    severity: "high",
    expression: /\b(?:password|secret|api[_-]?key|token)\s*=\s*["'][^"']{8,}["']/i,
    message: "Possible hard-coded credential. Load secrets from a secure configuration source.",
  },
  {
    severity: "high",
    expression: /\.execute\s*\(\s*(?:f["']|["'][^"']*(?:%|\+))/,
    message: "Possible SQL string interpolation. Use parameterized queries.",
  },
  {
    severity: "medium",
    expression: /\brequests\.(?:get|post|put|patch|delete)\s*\((?![^)]*\btimeout\s*=)/,
    message: "HTTP request may not set a timeout. Add an explicit timeout.",
  },
  {
    severity: "medium",
    expression: /except\s*(?:Exception)?\s*:\s*(?:\n\s*)?pass/,
    message: "Exception handler silently ignores an error. Handle or log it.",
  },
  {
    severity: "medium",
    expression: /from\s+\S+\s+import\s+\*/,
    message: "Wildcard import found. Import only the names that are used.",
  },
  {
    severity: "info",
    expression: /\b(?:print|breakpoint)\s*\(/,
    message: "Debug output or breakpoint found. Remove it before release.",
  },
  {
    severity: "info",
    expression: /#\s*(?:TODO|FIXME|XXX)\b/i,
    message: "Unresolved maintenance marker found.",
  },
];

const source = document.querySelector("#source");
const findings = document.querySelector("#findings");
const summary = document.querySelector("#summary");
const installButton = document.querySelector("#install");
let installPrompt;

function lineNumber(text, index) {
  return text.slice(0, index).split("\n").length;
}

function review() {
  const code = source.value;
  findings.replaceChildren();
  const results = [];

  for (const rule of rules) {
    const match = rule.expression.exec(code);
    if (match) {
      results.push({ ...rule, line: lineNumber(code, match.index) });
    }
  }

  if (!code.trim()) {
    summary.textContent = "Paste code to begin.";
    return;
  }

  results.sort((left, right) => {
    const rank = { high: 0, medium: 1, info: 2 };
    return rank[left.severity] - rank[right.severity] || left.line - right.line;
  });
  summary.textContent = `${results.length} finding${results.length === 1 ? "" : "s"} in ${code.split("\n").length} lines.`;

  for (const result of results) {
    const item = document.createElement("li");
    item.className = result.severity;
    item.textContent = `${result.severity.toUpperCase()} · line ${result.line} — ${result.message}`;
    findings.append(item);
  }
}

document.querySelector("#analyze").addEventListener("click", review);
document.querySelector("#clear").addEventListener("click", () => {
  source.value = "";
  review();
  source.focus();
});

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  installPrompt = event;
  installButton.hidden = false;
});

installButton.addEventListener("click", async () => {
  if (!installPrompt) {
    return;
  }
  installPrompt.prompt();
  await installPrompt.userChoice;
  installPrompt = undefined;
  installButton.hidden = true;
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("service-worker.js"));
}
