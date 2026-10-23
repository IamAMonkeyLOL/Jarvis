import sys


def open_browser(url):
    try:
        import webview
    except ImportError as error:
        raise SystemExit(
            "The embedded browser requires pywebview. Run: py -m pip install -r requirements.txt"
        ) from error
    webview.create_window("Jarvis Browser", url, width=1280, height=800)
    webview.start()


def main(arguments=None):
    arguments = sys.argv[1:] if arguments is None else arguments
    if len(arguments) != 1:
        raise SystemExit("Usage: py jarvis_browser.py <https://website>")
    open_browser(arguments[0])

 
if __name__ == "__main__":
    main()
