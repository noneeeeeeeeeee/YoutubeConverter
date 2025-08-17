import os
import sys
import subprocess
import requests
import zipfile
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

# Paths shared with yt_manager
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YTDLP_DIR = os.path.join(ROOT_DIR, "yt-dlp-bin")
YTDLP_EXE = os.path.join(YTDLP_DIR, "yt-dlp.exe")


def get_latest_release_info(branch: str) -> dict:
    if branch == "nightly":
        repo = "yt-dlp/yt-dlp-nightly-builds"
        api = f"https://api.github.com/repos/{repo}/releases/latest"
        dl = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp.exe"
    elif branch == "master":
        repo = "yt-dlp/yt-dlp-master-builds"
        api = f"https://api.github.com/repos/{repo}/releases/latest"
        dl = "https://github.com/yt-dlp/yt-dlp-master-builds/releases/latest/download/yt-dlp.exe"
    else:
        repo = "yt-dlp/yt-dlp"
        api = f"https://api.github.com/repos/{repo}/releases/latest"
        dl = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    tag = ""
    try:
        r = requests.get(api, timeout=15)
        r.raise_for_status()
        rel = r.json()
        tag = rel.get("tag_name") or rel.get("name") or ""
    except Exception:
        pass
    return {"repo": repo, "api": api, "download_url": dl, "tag": tag}


def current_binary_version() -> str:
    if not os.path.exists(YTDLP_EXE):
        return ""
    try:
        out = subprocess.check_output([YTDLP_EXE, "--version"], timeout=10)
        return (out.decode(errors="ignore").strip().split()[0]) if out else ""
    except Exception:
        return ""


def ensure_ytdlp_dir():
    os.makedirs(YTDLP_DIR, exist_ok=True)


def clear_ytdlp_cache():
    try:
        if os.path.exists(YTDLP_EXE):
            subprocess.run([YTDLP_EXE, "--rm-cache-dir"], timeout=15)
    except Exception:
        pass


class YtDlpUpdateWorker(QThread):
    status = pyqtSignal(str)

    def __init__(self, branch: str = "stable", check_only: bool = True):
        super().__init__()
        self.branch = branch
        self.check_only = check_only

    def run(self):
        try:
            ensure_ytdlp_dir()
            current = current_binary_version()
            rel = get_latest_release_info(self.branch)
            latest = rel.get("tag", "")
            dl_url = rel.get("download_url")
            if self.check_only:
                if latest and current:
                    if current == latest:
                        self.status.emit(f"yt-dlp binary up-to-date ({current})")
                    else:
                        self.status.emit(
                            f"yt-dlp binary current {current}; latest {latest}"
                        )
                elif current:
                    self.status.emit(f"yt-dlp binary current {current}; latest unknown")
                else:
                    self.status.emit("yt-dlp binary not installed")
                return
            if latest and current and current == latest and os.path.exists(YTDLP_EXE):
                self.status.emit("yt-dlp is up-to-date.")
                return
            if not dl_url:
                self.status.emit("Cannot resolve yt-dlp download URL")
                return
            self.status.emit("Downloading yt-dlp binary...")
            tmp_path = YTDLP_EXE + ".tmp"
            with requests.get(dl_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(256 * 1024):
                        if chunk:
                            f.write(chunk)
            if os.path.exists(YTDLP_EXE):
                try:
                    os.remove(YTDLP_EXE)
                except Exception:
                    pass
            os.replace(tmp_path, YTDLP_EXE)
            try:
                os.chmod(YTDLP_EXE, 0o755)
            except Exception:
                pass
            self.status.emit("yt-dlp updated.")
            clear_ytdlp_cache()
        except Exception as e:
            self.status.emit(f"yt-dlp update failed: {e}")


class AppUpdateWorker(QThread):
    status = pyqtSignal(str)
    updated = pyqtSignal(bool)

    def __init__(self, repo: str, channel: str, current_version: str, do_update: bool):
        super().__init__()
        self.repo = repo
        self.channel = (channel or "release").lower()  # release|prerelease|nightly
        self.current_version = current_version
        self.do_update = do_update

    def _local_version(self) -> str:
        try:
            vp = os.path.join(ROOT_DIR, "version.txt")
            if os.path.exists(vp):
                with open(vp, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass
        return self.current_version or ""

    def _get_release_json(self) -> Optional[dict]:
        base = f"https://api.github.com/repos/{self.repo}/releases"
        try:
            if self.channel == "nightly":
                url = f"{base}/tags/nightly"
                r = requests.get(url, timeout=20)
                r.raise_for_status()
                return r.json()
            r = requests.get(base, timeout=20)
            r.raise_for_status()
            releases = r.json() or []
            if self.channel == "release":
                return next((x for x in releases if not x.get("prerelease")), None)
            else:
                return next((x for x in releases if x.get("prerelease")), None) or (
                    releases[0] if releases else None
                )
        except Exception:
            return None

    def _pick_zip_asset(self, rel: dict) -> Optional[dict]:
        assets = rel.get("assets") or []
        for a in assets:
            n = (a.get("name") or "").lower()
            if n.startswith("youtubeconverter") and n.endswith(".zip"):
                return a
        for a in assets:
            n = (a.get("name") or "").lower()
            if n.endswith(".zip"):
                return a
        return None

    def _extract_zip_flat(self, zip_path: str, dest_dir: str):
        with zipfile.ZipFile(zip_path) as zf:
            for m in zf.infolist():
                name = m.filename.replace("\\", "/")
                parts = name.split("/")
                rel = "/".join(parts[1:]) if len(parts) > 1 else parts[0]
                if not rel or rel.endswith("/"):
                    continue
                out_path = os.path.join(dest_dir, rel)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with zf.open(m) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())

    def run(self):
        try:
            self.status.emit("Checking app updates...")
            rel = self._get_release_json()
            if not rel:
                self.status.emit("No releases found.")
                self.updated.emit(False)
                return
            tag = rel.get("tag_name") or rel.get("name") or ""
            remote_ver = (tag or "").strip()
            local_ver = self._local_version()
            if not self.do_update:
                if remote_ver and local_ver:
                    if remote_ver == local_ver:
                        self.status.emit(
                            f"App up-to-date ({local_ver}) [{self.channel}]"
                        )
                    else:
                        self.status.emit(
                            f"Update available {local_ver} -> {remote_ver} [{self.channel}]"
                        )
                else:
                    self.status.emit(f"Update check complete [{self.channel}]")
                self.updated.emit(False)
                return
            asset = self._pick_zip_asset(rel)
            if not asset:
                self.status.emit("No zip asset found in release.")
                self.updated.emit(False)
                return
            url = asset.get("browser_download_url")
            name = asset.get("name") or "update.zip"
            self.status.emit(f"Downloading {name}...")
            tmp_zip = os.path.join(ROOT_DIR, "_update_tmp.zip")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp_zip, "wb") as f:
                    for chunk in r.iter_content(256 * 1024):
                        if chunk:
                            f.write(chunk)
            self.status.emit("Applying update...")
            self._extract_zip_flat(tmp_zip, ROOT_DIR)
            try:
                os.remove(tmp_zip)
            except Exception:
                pass
            self.status.emit("App updated.")
            self.updated.emit(True)
        except Exception as e:
            self.status.emit(f"App update failed: {e}")
            self.updated.emit(False)
