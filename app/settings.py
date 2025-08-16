import json, os
from pathlib import Path
from typing import Optional
from .version import APP_NAME

if os.name == "nt":
    BASE_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    APP_DIR = BASE_DIR / APP_NAME
else:
    BASE_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    APP_DIR = BASE_DIR / APP_NAME

BIN_DIR = APP_DIR / "bin"
DATA_DIR = APP_DIR / "data"
CFG_PATH = APP_DIR / "config.json"

def ensure_app_dirs():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _load_cfg() -> dict:
    if CFG_PATH.exists():
        try:
            return json.loads(CFG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_cfg(cfg: dict):
    ensure_app_dirs()
    CFG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def get_last_path() -> str:
    cfg = _load_cfg()
    p = cfg.get("last_path")
    if p and os.path.isdir(p):
        return p
    # sensible default: user's Downloads
    default = str(Path.home() / "Downloads")
    return default

def set_last_path(path: str):
    cfg = _load_cfg()
    cfg["last_path"] = path
    _save_cfg(cfg)

def get_update_channel() -> str:
    cfg = _load_cfg()
    return cfg.get("update_channel", "stable")

def set_update_channel(ch: str):
    cfg = _load_cfg()
    cfg["update_channel"] = ch
    _save_cfg(cfg)

def set_retention_days(days: int):
    cfg = _load_cfg()
    cfg["history_retention_days"] = max(1, int(days))
    _save_cfg(cfg)
