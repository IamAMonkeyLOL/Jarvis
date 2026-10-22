"""Read-only environment check. Does not install anything or upload a report."""
import platform
import shutil
import sqlite3
import subprocess
import sys
from jarvis.config import DATA_DIR, MODEL, ROOT
from jarvis.ollama import OllamaClient, OllamaError


def main():
    print("JARVIS SETUP CHECK")
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"System: {platform.system()} {platform.release()}")
    print(f"SQLite: {sqlite3.sqlite_version}")
    print(f"Project: {ROOT}")
    print(f"Chat data: {DATA_DIR}")
    print(f"Free space on project drive: {shutil.disk_usage(ROOT).free / 1024**3:.1f} GiB")
    print("Ollama may store models on a different drive; check that drive too.")
    for executable, args in (("git", ["--version"]), ("ollama", ["--version"]), ("nvidia-smi", ["--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])):
        path = shutil.which(executable)
        if not path:
            print(f"{executable}: not found on PATH")
            continue
        try:
            result = subprocess.run([path, *args], capture_output=True, text=True, timeout=15)
            print(f"{executable}: {(result.stdout or result.stderr).strip()}")
        except (OSError, subprocess.TimeoutExpired):
            print(f"{executable}: check did not finish")
    try:
        installed = OllamaClient().check()
    except OllamaError as error:
        print(f"\nNOT READY: {error}")
        return 1
    print(f"\n{'READY' if installed else 'NOT READY'}: {MODEL} {'is installed' if installed else 'needs downloading with SETUP_MODEL.bat'}.")
    print("While generating a reply, run 'ollama ps' in a second terminal to inspect GPU use.")
    return 0 if installed else 1


if __name__ == "__main__":
    raise SystemExit(main())
