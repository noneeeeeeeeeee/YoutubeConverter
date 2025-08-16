import json, time
from typing import List, Dict
from pathlib import Path
from .settings import DATA_DIR, ensure_app_dirs

HIST_PATH = DATA_DIR / "history.json"
RETENTION_DAYS = 7

def _load() -> List[Dict]:
    if HIST_PATH.exists():
        try:
            return json.loads(HIST_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save(items: List[Dict]):
    ensure_app_dirs()
    HIST_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")

def add_entry(title: str, url: str, path: str):
    items = _load()
    items.append({"ts": time.time(), "title": title, "url": url, "path": path})
    # keep last 1000 entries
    if len(items) > 1000:
        items = items[-1000:]
    _save(items)

def recent() -> List[Dict]:
    items = _load()
    cutoff = time.time() - RETENTION_DAYS * 86400
    items = [i for i in items if i.get("ts", 0) >= cutoff]
    items.sort(key=lambda i: i.get("ts", 0), reverse=True)
    return items
    cutoff = int(time.time()) - days * 86400
    return [i for i in items if i.get("ts", 0) >= cutoff]
