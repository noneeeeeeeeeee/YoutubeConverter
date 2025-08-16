import json, os, stat, sys, tempfile, urllib.request, urllib.error, shutil, subprocess
from pathlib import Path
from typing import Callable, Optional, Tuple
from .settings import BIN_DIR

GITHUB_API_LATEST = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
UA = "YoutubeConverter/yt-dlp-updater"

def _asset_name() -> str:
    return "yt-dlp.exe" if os.name == "nt" else "yt-dlp"

def get_binary_path() -> str:
    return str(BIN_DIR / _asset_name())

def _http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _download(url: str, dest: Path, on_progress: Optional[Callable[[int, int], None]] = None):
    tmp = Path(str(dest) + ".download")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as f:
        total = int(resp.headers.get("Content-Length") or "0")
        done = 0
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if on_progress:
                on_progress(done, total)
    tmp.replace(dest)

def _chmod_x(p: Path):
    if os.name != "nt":
        try:
            p.chmod(p.stat().st_mode | stat.S_IEXEC)
        except Exception:
            pass

def current_version() -> Optional[str]:
    bin_path = get_binary_path()
    if not os.path.exists(bin_path):
        return None
    try:
        # Avoid console window on Windows
        kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}
        if os.name == "nt":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        proc = subprocess.run([bin_path, "--version"], **kwargs)
        out = (proc.stdout or "").strip()
        return out or None
    except Exception:
        return None

def _latest_release() -> Tuple[str, str]:
    # returns (version_tag, asset_download_url)
    data = _http_json(GITHUB_API_LATEST)
    ver = data.get("tag_name") or ""
    name = _asset_name()
    asset = next((a for a in data.get("assets", []) if a.get("name") == name), None)
    if not asset:
        raise RuntimeError(f"yt-dlp asset {name} not found in latest release")
    return ver, asset.get("browser_download_url")

def ensure_latest(on_status: Optional[Callable[[str], None]] = None,
                  on_progress: Optional[Callable[[int, int], None]] = None) -> Tuple[bool, Optional[str], str]:
    """
    Returns (updated, old_version, new_version)
    """
    if on_status: on_status("Checking yt-dlp…")
    bin_path = Path(get_binary_path())
    bin_path.parent.mkdir(parents=True, exist_ok=True)

    old_ver = current_version()
    latest_ver, url = _latest_release()

    if old_ver == latest_ver and bin_path.exists():
        if on_status: on_status(f"yt-dlp is up to date ({latest_ver}).")
        return (False, old_ver, latest_ver)

    action = "Installing" if not bin_path.exists() else "Updating"
    if on_status: on_status(f"{action} yt-dlp {latest_ver}…")

    tmp = Path(tempfile.gettempdir()) / f"{_asset_name()}.{os.getpid()}.tmp"
    _download(url, tmp, on_progress=on_progress)

    # Replace binary
    shutil.copyfile(str(tmp), str(bin_path))
    _chmod_x(bin_path)
    try:
        tmp.unlink(missing_ok=True)  # cleanup temp file
    except Exception:
        pass

    if on_status: on_status(f"yt-dlp updated to {latest_ver}.")
    return (True, old_ver, latest_ver)
