import os
import sys
import subprocess
import requests
import zipfile
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
import logging
import time


if getattr(sys, "frozen", False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YTDLP_DIR = os.path.join(ROOT_DIR, "yt-dlp-bin")
YTDLP_EXE = os.path.join(YTDLP_DIR, "yt-dlp.exe")
STAGING_DIR = os.path.join(ROOT_DIR, "_update_staging")


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


def _hidden_subprocess_kwargs():  # NEW
    kwargs = {}
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        kwargs["startupinfo"] = si
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def current_binary_version() -> str:
    if not os.path.exists(YTDLP_EXE):
        return ""
    try:
        kwargs = _hidden_subprocess_kwargs()
        out = subprocess.check_output([YTDLP_EXE, "--version"], timeout=10, **kwargs)
        return (out.decode(errors="ignore").strip().split()[0]) if out else ""
    except Exception:
        return ""


def ensure_ytdlp_dir():
    os.makedirs(YTDLP_DIR, exist_ok=True)


def clear_ytdlp_cache():
    try:
        if os.path.exists(YTDLP_EXE):
            kwargs = _hidden_subprocess_kwargs()
            subprocess.run([YTDLP_EXE, "--rm-cache-dir"], timeout=15, **kwargs)
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
    available = pyqtSignal(str, str)

    def __init__(self, repo: str, channel: str, current_version: str, do_update: bool):
        super().__init__()
        self.repo = repo
        self.channel = (channel or "release").lower()
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
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "YoutubeConverter-Updater",
        }

        def _get(url: str):
            try:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code == 403:
                    self.status.emit(f"GitHub API rate limited (403) for {url}")
                elif r.status_code == 404:
                    self.status.emit(f"Not found (404) for {url}")
                r.raise_for_status()
                return r.json()
            except requests.exceptions.RequestException as e:
                self.status.emit(f"GitHub API error: {e}")
                return None

        # Nightly: try release-by-tag first, then fallback to tags list
        if self.channel == "nightly":
            rel = _get(f"{base}/tags/nightly")
            if rel:
                return rel
            # Fallback: tags endpoint
            tags = (
                _get(f"https://api.github.com/repos/{self.repo}/tags?per_page=100")
                or []
            )
            tag = next(
                (t for t in tags if (t.get("name") or "").lower() == "nightly"), None
            )
            if not tag:
                return None
            # Try resolving the tag to a release (if a Release exists for that tag)
            rel = _get(f"{base}/tags/{tag.get('name')}")
            # If still none, return a minimal dict so callers can at least show availability
            return rel or {"tag_name": tag.get("name"), "assets": []}

        # Non-nightly: list releases
        rels = _get(base) or []
        if rels:
            if self.channel == "release":
                rel = next((x for x in rels if not x.get("prerelease")), None)
                if rel:
                    return rel
            elif self.channel == "prerelease":
                rel = next(
                    (
                        x
                        for x in rels
                        if x.get("prerelease")
                        and (x.get("tag_name") or "").lower() != "nightly"
                    ),
                    None,
                ) or next((x for x in rels if x.get("prerelease")), None)
                if rel:
                    return rel
            else:
                return rels[0]

        # Fallback when there are no Releases objects: try tags
        tags = _get(f"https://api.github.com/repos/{self.repo}/tags?per_page=100") or []
        if not tags:
            return None
        # Prefer version-like tags for release channel
        if self.channel == "release":
            ver = next(
                (t for t in tags if (t.get("name") or "").lower().startswith("v")), None
            )
            chosen = ver or tags[0]
        elif self.channel == "prerelease":
            # No strict rule; take first non-nightly tag
            chosen = next(
                (t for t in tags if (t.get("name") or "").lower() != "nightly"), tags[0]
            )
        else:
            chosen = tags[0]

        # Try resolve tag to a release (if one exists); if not, return minimal info
        rel = _get(f"{base}/tags/{chosen.get('name')}")
        return rel or {"tag_name": chosen.get("name"), "assets": []}

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

    @staticmethod
    def _normalize_version(v: str) -> str:
        """
        Normalize version strings for comparison:
        - Trim whitespace
        - Drop leading 'v' (common in tags) when followed by a digit
        - Lower-case for stability
        """
        if not v:
            return ""
        s = v.strip()
        if len(s) >= 2 and (s[0] in ("v", "V")) and s[1].isdigit():
            s = s[1:]
        return s.strip().lower()

    def run(self):
        try:
            self.status.emit(f"Checking app updates from {self.repo}...")
            rel = self._get_release_json()
            if not rel:
                self.status.emit(f"No releases found for {self.repo} [{self.channel}].")
                self.updated.emit(False)
                return
            if self.channel == "nightly":
                tag = rel.get("name") or rel.get("tag_name") or ""
            else:
                tag = rel.get("tag_name") or rel.get("name") or ""
            raw_remote_ver = (tag or "").strip()
            raw_local_ver = self._local_version()

            remote_ver = self._normalize_version(raw_remote_ver)
            local_ver = self._normalize_version(raw_local_ver)

            if remote_ver and local_ver and remote_ver == local_ver:
                self.status.emit(
                    f"App up-to-date ({raw_local_ver or local_ver}) [{self.channel}]"
                )
                self.updated.emit(False)
                return

            if not self.do_update:
                if remote_ver and local_ver and remote_ver != local_ver:
                    self.status.emit(
                        f"Update available {raw_local_ver or local_ver} -> {raw_remote_ver or remote_ver} [{self.channel}]"
                    )
                    self.available.emit(
                        raw_remote_ver or remote_ver, raw_local_ver or local_ver
                    )  # NEW
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
            os.makedirs(STAGING_DIR, exist_ok=True)
            tmp_zip = os.path.join(STAGING_DIR, "_update_tmp.zip")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp_zip, "wb") as f:
                    for chunk in r.iter_content(256 * 1024):
                        if chunk:
                            f.write(chunk)

            self.status.emit("Preparing update...")
            # Extract into staging (no in-place overwrite while running)
            for root, dirs, files in os.walk(STAGING_DIR):
                for fn in files:
                    if fn != "_update_tmp.zip":
                        try:
                            os.remove(os.path.join(root, fn))
                        except Exception:
                            pass
            self._extract_zip_flat(tmp_zip, STAGING_DIR)
            try:
                os.remove(tmp_zip)
            except Exception:
                pass
            try:
                with open(os.path.join(STAGING_DIR, ".pending"), "w") as f:
                    f.write(remote_ver or "")
            except Exception:
                pass
            self.status.emit("Update ready. It will be applied on restart.")
            self.updated.emit(True)
        except Exception as e:
            self.status.emit(f"App update failed: {e}")
            self.updated.emit(False)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("update_debugger")

    def status_callback(message):
        logger.info(message)
        print(message)

    def available_callback(remote_ver, local_ver):
        logger.info(f"Update available: {local_ver} -> {remote_ver}")
        print(f"Update available: {local_ver} -> {remote_ver}")

    # Test YT-DLP updater
    logger.info("Testing YT-DLP updater...")
    ytdlp_worker = YtDlpUpdateWorker(branch="stable", check_only=True)
    ytdlp_worker.status.connect(status_callback)
    ytdlp_worker.start()
    ytdlp_worker.wait()
    logger.info("Testing App update check...")
    app_worker = AppUpdateWorker(
        repo="noneeeeeeeeeee/YoutubeConverter",
        channel="release",
        current_version="0.0.0",
        do_update=False,
    )
    app_worker.status.connect(status_callback)
    app_worker.available.connect(available_callback)
    app_worker.start()
    app_worker.wait()
    # Test if we're hitting rate limits
    logger.info("Testing GitHub API rate limit...")
    try:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "YoutubeConverter-Updater",
        }
        r = requests.get(
            "https://api.github.com/rate_limit", headers=headers, timeout=10
        )
        r.raise_for_status()
        rate_info = r.json()
        core_limit = rate_info.get("resources", {}).get("core", {})
        remaining = core_limit.get("remaining", 0)
        reset_time = core_limit.get("reset", 0)
        reset_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(reset_time))
        logger.info(
            f"GitHub API Rate Limit: {remaining} requests remaining, resets at {reset_datetime}"
        )
        print(
            f"GitHub API Rate Limit: {remaining} requests remaining, resets at {reset_datetime}"
        )
        if remaining < 10:
            logger.warning("GitHub API rate limit is low!")
            print("WARNING: GitHub API rate limit is low!")
    except Exception as e:
        logger.error(f"Failed to check rate limit: {e}")
        print(f"ERROR: Failed to check rate limit: {e}")
