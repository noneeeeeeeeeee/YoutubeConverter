import os
import sys
import time
from typing import Dict, List, Optional, Callable

from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import subprocess
import json
import requests


def build_ydl_opts(
    base_dir: str,
    kind: str,
    fmt: str,
    ffmpeg_location: Optional[str] = None,
    progress_hook: Optional[Callable] = None,
    quality: Optional[str] = None,
):
    outtmpl = os.path.join(base_dir, "%(title).200s [%(id)s].%(ext)s")
    postprocessors = []
    # Normalize quality tokens
    q = (quality or "best").lower()

    def _parse_height(qv: str) -> Optional[int]:
        try:
            return int(qv.rstrip("p"))
        except Exception:
            return None

    def _parse_abr(qa: str) -> Optional[int]:
        try:
            return int(qa.rstrip("k"))
        except Exception:
            return None

    if kind == "audio":
        # Extract audio to target format
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": fmt,
                "preferredquality": "0",
            }
        ]
        if q != "best":
            abr = _parse_abr(q) or 0
            format_selector = f"bestaudio[abr>={abr}]/bestaudio/best"
        else:
            format_selector = "bestaudio/best"
        merge_out = None
    else:
        # Video selection, honoring container preference if mp4 requested
        height = _parse_height(q) if q != "best" else None
        if fmt.lower() == "mp4":
            if height:
                format_selector = (
                    f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"best[height<={height}][ext=mp4]/best[ext=mp4]/best"
                )
            else:
                format_selector = (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                )
        else:
            if height:
                format_selector = (
                    f"bestvideo[height<={height}]+bestaudio/"
                    f"best[height<={height}]/best"
                )
            else:
                format_selector = "bestvideo+bestaudio/best"
        merge_out = fmt

    opts = {
        "outtmpl": outtmpl,
        "format": format_selector,
        "noprogress": True,
        "quiet": True,
        "nocheckcertificate": True,
        "merge_output_format": merge_out,
        "postprocessors": postprocessors,
        "ffmpeg_location": ffmpeg_location or None,
        "noplaylist": False,
        "retries": 10,
        "fragment_retries": 10,
        "skip_unavailable_fragments": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.5",
        },
        # Use web client to avoid PO Token warnings
        "extractor_args": {"youtube": {"player_client": ["web"]}},
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


class InfoFetcher(QThread):
    finished_ok = pyqtSignal(dict)
    finished_fail = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "noprogress": True,
                "noplaylist": False,
                "extract_flat": False,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                "extractor_args": {"youtube": {"player_client": ["web"]}},
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
            self.finished_ok.emit(info)
        except Exception as e:
            self.finished_fail.emit(str(e))


class Downloader(QThread):
    itemProgress = pyqtSignal(
        int, float, float, object  # index, percent, speed, eta (int or None)
    )
    itemStatus = pyqtSignal(int, str)  # index, status text
    itemThumb = pyqtSignal(int, bytes)  # index, image bytes
    finished_all = pyqtSignal()

    def __init__(
        self,
        items: List[dict],
        base_dir: str,
        kind: str,
        fmt: str,
        ffmpeg_location: Optional[str] = None,
        quality: Optional[str] = None,
    ):
        super().__init__()
        self.items = items
        self.base_dir = base_dir
        self.kind = kind
        self.fmt = fmt
        self.ffmpeg_location = ffmpeg_location
        self.quality = quality or "best"

    def _hook_builder(self, idx: int):
        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimated") or 0
                downloaded = d.get("downloaded_bytes", 0)
                pct = (downloaded / total * 100.0) if total else 0.0
                speed = d.get("speed") or 0.0
                eta = d.get("eta")
                self.itemProgress.emit(idx, pct, speed, eta)
            elif d["status"] == "finished":
                self.itemStatus.emit(idx, "Processing...")
            # else ignored

        return hook

    def run(self):
        # Fetch thumbnails first
        for idx, it in enumerate(self.items):
            thumb_url = (
                (it.get("thumbnail") or it.get("thumbnails", [{}])[-1].get("url"))
                if it
                else None
            )
            if thumb_url:
                try:
                    import requests

                    r = requests.get(thumb_url, timeout=10)
                    if r.ok:
                        self.itemThumb.emit(idx, r.content)
                except Exception:
                    pass

        for idx, it in enumerate(self.items):
            url = it.get("webpage_url") or it.get("url")
            if not url:
                self.itemStatus.emit(idx, "Invalid URL")
                continue
            self.itemStatus.emit(idx, "Starting...")
            opts = build_ydl_opts(
                self.base_dir,
                self.kind,
                self.fmt,
                self.ffmpeg_location,
                self._hook_builder(idx),
                self.quality,
            )
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                self.itemProgress.emit(idx, 100.0, 0.0, 0)
                self.itemStatus.emit(idx, "Done")
            except Exception as e:
                self.itemStatus.emit(idx, f"Error: {e}")
        self.finished_all.emit()


class YtDlpUpdateWorker(QThread):
    status = pyqtSignal(str)

    def __init__(self, branch: str = "stable", check_only: bool = True):
        super().__init__()
        self.branch = branch
        self.check_only = check_only

    def run(self):
        try:
            # Check current version
            import subprocess

            ver = ""
            try:
                out = subprocess.check_output(
                    [sys.executable, "-m", "yt_dlp", "--version"],
                    stderr=subprocess.STDOUT,
                    timeout=30,
                )
                ver = out.decode().strip()
            except Exception:
                pass
            if self.check_only:
                self.status.emit(f"yt-dlp version: {ver or 'unknown'}")
                return

            self.status.emit("Updating yt-dlp...")
            cmd = [sys.executable, "-m", "pip", "install", "-U"]
            if self.branch == "stable":
                cmd += ["yt-dlp"]
            elif self.branch == "nightly":
                cmd += ["yt-dlp-nightly"]
            else:  # master
                cmd += ["git+https://github.com/yt-dlp/yt-dlp@master"]
            import subprocess

            subprocess.check_call(cmd)
            self.status.emit("yt-dlp updated.")
        except Exception as e:
            self.status.emit(f"yt-dlp update failed: {e}")


class AppUpdateWorker(QThread):
    status = pyqtSignal(str)
    updated = pyqtSignal(bool)  # True if updated applied

    def __init__(self, repo: str, channel: str, current_version: str, do_update: bool):
        super().__init__()
        self.repo = repo  # "owner/name"
        self.channel = channel  # "release"|"prerelease"
        self.current_version = current_version
        self.do_update = do_update

    def _is_newer(self, tag: str) -> bool:
        def norm(v: str):
            v = v.lstrip("vV")
            return [
                int(p) if p.isdigit() else p for p in v.replace("-", ".").split(".")
            ]

        try:
            return norm(tag) > norm(self.current_version)
        except Exception:
            return tag != self.current_version

    def run(self):
        try:
            self.status.emit("Checking app updates...")
            url = f"https://api.github.com/repos/{self.repo}/releases"
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            releases = r.json()
            if self.channel == "release":
                rel = next((x for x in releases if not x.get("prerelease")), None)
            else:
                rel = next((x for x in releases if x.get("prerelease")), None) or (
                    releases[0] if releases else None
                )
            if not rel:
                self.status.emit("No releases found.")
                self.updated.emit(False)
                return
            tag = rel.get("tag_name") or rel.get("name") or ""
            if not tag or not self._is_newer(tag):
                self.status.emit("App is up-to-date.")
                self.updated.emit(False)
                return
            self.status.emit(f"Update available: {tag}")
            if not self.do_update:
                self.updated.emit(False)
                return
            self.status.emit("Updating app...")
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-U",
                f"git+https://github.com/{self.repo}.git@{tag}",
            ]
            subprocess.check_call(cmd)
            self.status.emit("App updated.")
            self.updated.emit(True)
        except Exception as e:
            self.status.emit(f"App update failed: {e}")
            self.updated.emit(False)
            self.updated.emit(True)
        except Exception as e:
            self.status.emit(f"App update failed: {e}")
            self.updated.emit(False)
