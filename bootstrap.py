"""Windows launcher helper. Creates an isolated environment on first launch."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    if sys.version_info < (3, 11):
        print("Jarvis needs Python 3.11 or newer. Python 3.12 is the tested version.")
        return 1
    os.chdir(ROOT)
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Creating Jarvis's Python environment...", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True)
    requirements = ROOT / "requirements.txt"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = ROOT / ".venv" / ".jarvis_requirements"
    healthy = subprocess.run([str(python), "-c", "import streamlit; assert streamlit.__version__ == '1.66.0'"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not healthy or not marker.exists() or marker.read_text().strip() != digest:
        print("Installing app dependencies. Internet is needed for this first setup...", flush=True)
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements)], check=True)
        marker.write_text(digest)
    if "--test" in sys.argv:
        command = [str(python), "-m", "unittest", "discover", "-s", "tests", "-v"]
    elif "--check" in sys.argv:
        command = [str(python), "doctor.py"]
    else:
        print("Opening Jarvis at http://127.0.0.1:8501", flush=True)
        print("Keep this window open. Press Ctrl+C here to stop Jarvis.", flush=True)
        command = [str(python), "-m", "streamlit", "run", "app.py", "--server.address", "127.0.0.1", "--server.port", "8501", "--server.headless", "false"]
    return subprocess.call(command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nJarvis stopped. Your saved conversations remain in the data folder.")
    except (subprocess.CalledProcessError, OSError) as error:
        print(f"Setup did not finish: {error}")
        print("Check the error above, your internet connection, and free disk space. You can run the launcher again.")
        raise SystemExit(1)
