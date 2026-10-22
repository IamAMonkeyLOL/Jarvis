"""Create a consistent local copy of the chat database."""
from datetime import datetime
from jarvis.config import DB_PATH, ROOT
from jarvis.storage import Store

if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit("There is no chat database yet. Start Jarvis and send a message first.")
    target = ROOT / "backups" / f"jarvis-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3"
    print(Store(DB_PATH).backup(target))
