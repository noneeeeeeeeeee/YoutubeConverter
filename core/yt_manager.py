import os
import sys
from typing import Dict, List, Optional, Callable
from threading import Event  # added

from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import subprocess
import requests
import json  # added

# --- yt-dlp binary management (paths and helpers) ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YTDLP_DIR = os.path.join(ROOT_DIR, "yt-dlp-bin")
YTDLP_EXE = os.path.join(YTDLP_DIR, "yt-dlp.exe")


def get_latest_release_info(branch: str) -> dict:
    # Map branches to repos and asset URLs
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
        # Typical output: 2025.08.11
        return (out.decode(errors="ignore").strip().split()[0]) if out else ""
    except Exception:
        return ""


def ensure_ytdlp_dir():
    os.makedirs(YTDLP_DIR, exist_ok=True)


def clear_ytdlp_cache():
    """Best-effort cache cleanup to avoid stale/corrupt cache."""
    try:
        if os.path.exists(YTDLP_EXE):
            subprocess.run([YTDLP_EXE, "--rm-cache-dir"], timeout=15)
    except Exception:
        pass


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
        "socket_timeout": 15,  # add: avoid long hangs
        "extractor_retries": 2,  # add: limit extractor retries
        "skip_unavailable_fragments": True,
        # Disable disk cache to avoid slowdowns and stale data
        "cachedir": False,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.5",
        },
        # Prefer TV client to avoid SABR/PO token slow paths
        "extractor_args": {"youtube": {"player_client": ["tv"]}},
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


class InfoFetcher(QThread):
    finished_ok = pyqtSignal(dict)
    finished_fail = pyqtSignal(str)

    def __init__(self, url: str, timeout_sec: int = 60):  # increase default timeout
        super().__init__()
        self.url = url
        self.timeout_sec = timeout_sec

    def _is_search(self) -> bool:
        return isinstance(self.url, str) and self.url.startswith("ytsearch")

    def _is_playlist(self) -> bool:
        try:
            u = str(self.url)
            return ("list=" in u) or ("playlist?" in u)
        except Exception:
            return False

    def _extract_with_binary(self) -> dict:
        is_search = self._is_search()
        is_playlist = self._is_playlist()
        args = [
            YTDLP_EXE,
            "-J",
            "--ignore-config",
            "--no-warnings",
            "--no-progress",
            "--skip-download",
            "--no-write-comments",
            "--no-write-playlist-metafiles",
            "--no-cache-dir",  # NEW: disable cache
            "--extractor-retries",
            "1",
            # extractor args (can repeat)
            "--extractor-args",
            "youtube:player_client=tv",
            "--extractor-args",
            "youtube:skip=dash,hls",
            "--extractor-args",
            "youtubetab:skip=webpage",
        ]
        # Flat metadata is faster for searches and playlists
        if is_search or is_playlist:
            args.append("--flat-playlist")
        args.append(self.url)

        env = os.environ.copy()
        env["YTDLP_NO_PLUGINS"] = "1"

        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=self.timeout_sec, env=env
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "yt-dlp binary failed")
        if not proc.stdout:
            raise RuntimeError("Empty response from yt-dlp")
        return json.loads(proc.stdout)

    def _extract_with_python_api(self) -> dict:
        is_search = self._is_search()
        is_playlist = self._is_playlist()
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "noprogress": True,
            "noplaylist": False,
            "extract_flat": True if (is_search or is_playlist) else False,
            "socket_timeout": 15,
            "extractor_retries": 1 if (is_search or is_playlist) else 2,
            # Disable disk cache
            "cachedir": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.5",
            },
            "extractor_args": {
                "youtube": {"player_client": ["tv"], "skip": ["dash", "hls"]},
                "youtubetab": {"skip": ["webpage"]},
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(self.url, download=False)

    def run(self):
        try:
            # Prefer binary with hard timeout to avoid limbo hangs
            if os.path.exists(YTDLP_EXE):
                info = self._extract_with_binary()
            else:
                info = self._extract_with_python_api()
            self.finished_ok.emit(info)
        except subprocess.TimeoutExpired:
            self.finished_fail.emit("Timed out while fetching info")
        except Exception:
            # Fallback once via Python API if binary failed
            try:
                info = self._extract_with_python_api()
                self.finished_ok.emit(info)
            except Exception as e2:
                self.finished_fail.emit(str(e2))


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
        # Control
        self._pause_evt = Event()
        self._pause_evt.set()  # running
        self._stop = False
        self._meta_threads: Dict[int, InfoFetcher] = {}  # idx -> fetcher

    # External controls
    def pause(self):
        self._pause_evt.clear()
        for idx, _ in enumerate(self.items):
            self.itemStatus.emit(idx, "Paused")

    def resume(self):
        self._pause_evt.set()
        for idx, _ in enumerate(self.items):
            self.itemStatus.emit(idx, "Resuming...")

    def is_paused(self) -> bool:
        return not self._pause_evt.is_set()

    def stop(self):
        self._stop = True

    def _hook_builder(self, idx: int):
        def hook(d):
            # Pause handling
            self._pause_evt.wait()
            if self._stop:
                raise yt_dlp.utils.DownloadError("Stopped by user")
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
        # Thumbs prefetch
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

        # Start metadata fetchers for items missing metadata
        for idx, it in enumerate(self.items):
            if self._stop:
                break
            if self._needs_metadata(it):
                url = it.get("webpage_url") or it.get("url")
                if url:
                    self._start_meta_fetch(idx, url)

        # Build processing order: ready items first, then awaiting ones
        ready = [i for i, it in enumerate(self.items) if not self._needs_metadata(it)]
        waiting = [i for i, it in enumerate(self.items) if self._needs_metadata(it)]
        order: List[int] = ready + waiting

        stalled_rounds = 0
        while order and not self._stop:
            idx = order.pop(0)
            it = self.items[idx]
            url = it.get("webpage_url") or it.get("url")
            if not url:
                self.itemStatus.emit(idx, "Invalid URL")
                continue

            if self._needs_metadata(it):
                # Still waiting for metadata -> skip for now
                order.append(idx)
                stalled_rounds += 1
                if stalled_rounds >= len(order) + 1:
                    # Avoid tight loop; give metadata fetchers time
                    QThread.msleep(100)
                    stalled_rounds = 0
                continue
            stalled_rounds = 0

            # Download now that metadata is ready
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
                if not self._stop:
                    self.itemProgress.emit(idx, 100.0, 0.0, 0)
                    self.itemStatus.emit(idx, "Done")
            except Exception as e:
                if self._stop:
                    self.itemStatus.emit(idx, "Stopped")
                    break
                self.itemStatus.emit(idx, f"Error: {e}")

        self.finished_all.emit()

    def _start_meta_fetch(self, idx: int, url: str):
        # Avoid duplicate starts
        if idx in self._meta_threads:
            return
        self.itemStatus.emit(idx, "Fetching metadata...")
        f = InfoFetcher(url)

        def _ok(meta: dict, i=idx):
            try:
                # Merge metadata
                self.items[i] = {**self.items[i], **(meta or {})}
                # Emit new thumbnail if available
                thumb_url = self.items[i].get("thumbnail") or (
                    self.items[i].get("thumbnails") or [{}]
                )[-1].get("url")
                if thumb_url:
                    try:
                        r = requests.get(thumb_url, timeout=10)
                        if r.ok:
                            self.itemThumb.emit(i, r.content)
                    except Exception:
                        pass
                title = self.items[i].get("title") or "Untitled"
                self.itemStatus.emit(i, f"Metadata ready: {title}")
            finally:
                self._meta_threads.pop(i, None)

        def _fail(err: str, i=idx):
            self.itemStatus.emit(i, f"Metadata fetch failed, will try best available")
            self._meta_threads.pop(i, None)

        f.finished_ok.connect(_ok)
        f.finished_fail.connect(_fail)
        self._meta_threads[idx] = f
        f.start()

    def _needs_metadata(self, it: dict) -> bool:
        # Heuristic: fast-paste placeholders usually have only url/title and lack id/thumbnail
        if not it:
            return True
        if not it.get("url") and not it.get("webpage_url"):
            return False  # invalid item handled elsewhere
        has_core = (
            bool(it.get("id")) or bool(it.get("duration")) or bool(it.get("extractor"))
        )
        has_thumb = bool(it.get("thumbnail")) or bool(it.get("thumbnails"))
        return not (has_core and has_thumb)

    def _extract_info_quick(self, url: str) -> dict:
        # Lightweight metadata extraction (no download), cache disabled
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "noprogress": True,
            "noplaylist": False,
            "socket_timeout": 15,
            "extractor_retries": 1,
            "cachedir": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.5",
            },
            "extractor_args": {
                "youtube": {"player_client": ["tv"], "skip": ["dash", "hls"]},
                "youtubetab": {"skip": ["webpage"]},
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)


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
            # Compare versions when available
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

            # If we know both and are equal, skip download
            if latest and current and current == latest and os.path.exists(YTDLP_EXE):
                self.status.emit("yt-dlp is up-to-date.")
                return

            # Download/update binary
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
            # Replace atomically
            if os.path.exists(YTDLP_EXE):
                try:
                    os.remove(YTDLP_EXE)
                except Exception:
                    pass
            os.replace(tmp_path, YTDLP_EXE)
            # Ensure executable (mostly for POSIX; no-op on Windows)
            try:
                os.chmod(YTDLP_EXE, 0o755)
            except Exception:
                pass
            self.status.emit("yt-dlp updated.")
            # NEW: purge old caches after update
            clear_ytdlp_cache()
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
            self.status.emit(f"App update failed: {e}")
            self.updated.emit(False)
            self.updated.emit(True)
        except Exception as e:
            self.status.emit(f"App update failed: {e}")
            self.updated.emit(False)
            self.status.emit(f"App update failed: {e}")
            self.updated.emit(False)
