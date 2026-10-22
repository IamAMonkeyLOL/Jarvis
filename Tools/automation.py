import subprocess
import webbrowser

try:
    import pyautogui
except ImportError:
    pyautogui = None


def open_website(url):
    webbrowser.open(url)
    return f"Opened {url}"


def open_notepad():
    subprocess.Popen("notepad.exe")
    return "Opened Notepad"


def open_calculator():
    subprocess.Popen("calc.exe")
    return "Opened Calculator"


def type_text(text):
    if pyautogui is None:
        raise RuntimeError("pyautogui is not installed")
    pyautogui.write(text, interval=0.03)
    return "Typed text"
