import os
import shutil
import tempfile
import zipfile
import requests
from PyQt6.QtCore import QThread, pyqtSignal

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF_DIR = os.path.join(ROOT_DIR, "ffmpeg")
FF_EXE = os.path.join(FF_DIR, "ffmpeg.exe")
FP_EXE = os.path.join(FF_DIR, "ffprobe.exe")

FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def ensure_ffmpeg_in_path() -> bool:
    # If local exists, ensure PATH includes it
    if os.path.exists(FF_EXE):
        add_to_path(FF_DIR)
        return True
    # If discoverable in PATH, ok
    if shutil.which("ffmpeg"):
        return True
    return False


def add_to_path(directory: str):
    current = os.environ.get("PATH", "")
    if directory not in current:
        os.environ["PATH"] = directory + os.pathsep + current


class FfmpegInstaller(QThread):
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal(str)
    finished_fail = pyqtSignal(str)

    def run(self):
        try:
            os.makedirs(FF_DIR, exist_ok=True)
            # Download zip
            tmp_fd, tmp_zip = tempfile.mkstemp(suffix=".zip")
            os.close(tmp_fd)
            with requests.get(FFMPEG_ZIP_URL, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0)) or None
                downloaded = 0
                with open(tmp_zip, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if not chunk:
                            continue
                        f.write(chunk)
                        if total:
                            downloaded += len(chunk)
                            self.progress.emit(int(downloaded * 100 / total))
            # Extract ffmpeg.exe and ffprobe.exe
            with zipfile.ZipFile(tmp_zip, "r") as z:
                # Find files
                names = z.namelist()
                ffmpeg_name = next(
                    (n for n in names if n.endswith("/bin/ffmpeg.exe")), None
                )
                ffprobe_name = next(
                    (n for n in names if n.endswith("/bin/ffprobe.exe")), None
                )
                if not ffmpeg_name or not ffprobe_name:
                    raise RuntimeError("ffmpeg.exe or ffprobe.exe not found in archive")
                z.extract(ffmpeg_name, FF_DIR)
                z.extract(ffprobe_name, FF_DIR)
                # Move from nested folder to FF_DIR root
                src_ff = os.path.join(FF_DIR, ffmpeg_name)
                src_fp = os.path.join(FF_DIR, ffprobe_name)
                final_ff = os.path.join(FF_DIR, "ffmpeg.exe")
                final_fp = os.path.join(FF_DIR, "ffprobe.exe")
                # Ensure parent dir
                os.makedirs(FF_DIR, exist_ok=True)
                # Move/replace
                if os.path.exists(final_ff):
                    os.remove(final_ff)
                if os.path.exists(final_fp):
                    os.remove(final_fp)
                os.replace(src_ff, final_ff)
                os.replace(src_fp, final_fp)
                # Cleanup extracted dirs
                top = ffmpeg_name.split("/")[0]
                top_dir = os.path.join(FF_DIR, top)
                if os.path.isdir(top_dir):
                    shutil.rmtree(top_dir, ignore_errors=True)
            os.remove(tmp_zip)
            add_to_path(FF_DIR)
            self.finished_ok.emit(FF_DIR)
        except Exception as e:
            self.finished_fail.emit(str(e))
