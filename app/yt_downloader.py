import json, os, re, subprocess
from pathlib import Path
from typing import Callable, Dict, List, Tuple, Optional, TextIO
from .updater_ytdlp import get_binary_path

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

def _run_json(args: List[str]) -> dict:
    binp = get_binary_path()
    cmd = [binp] + args
    kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}
    if os.name == "nt":
        kwargs["creationflags"] = CREATE_NO_WINDOW
    p = subprocess.run(cmd, **kwargs)
    out = (p.stdout or "").strip()
    return json.loads(out) if out else {}

def search(query: str, limit: int = 10) -> List[Dict]:
    if not query:
        return []
    # ytsearchN:query and return flat list for speed
    data = _run_json(["-J", f"ytsearch{limit}:{query}", "--flat-playlist", "--no-warnings"])
    results: List[Dict] = []
    for e in data.get("entries", []) or []:
        title = e.get("title") or e.get("alt_title") or "Unknown"
        url = e.get("webpage_url")
        if not url:
            vid = e.get("id")
            if vid:
                url = f"https://www.youtube.com/watch?v={vid}"
        if url:
            results.append({"title": title, "url": url})
    return results

def list_quality_options(_video_url: str) -> List[Tuple[str, str]]:
    # Static presets covering common cases
    # mark param as used to satisfy linters/type-checkers
    _ = _video_url
    return [
        ("Best (video+audio)", "bv*+ba/b"),
        ("Best audio only", "ba/bestaudio"),
        ("1080p (<=1080)", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
        ("720p (<=720)", "bestvideo[height<=720]+bestaudio/best[height<=720]"),
        ("360p (<=360)", "bestvideo[height<=360]+bestaudio/best[height<=360]"),
    ]

def _probe_title(url: str) -> str:
    try:
        data = _run_json(["-J", url, "--no-warnings"])
        return data.get("title") or "Video"
    except Exception:
        return "Video"
def download(url: str, fmt: str, outdir: str,
             on_progress: Optional[Callable[[float, float], None]] = None) -> Dict:
    """
    Returns minimal info: {"title": str}
    on_progress(pct, speed) pct in 0..100 (speed currently 0)
    """
    title = _probe_title(url)
    binp = get_binary_path()
    Path(outdir).mkdir(parents=True, exist_ok=True)
    cmd = [
        binp,
        "-f", fmt,
        "-P", outdir,
        "-o", "%(title)s.%(ext)s",
        "--newline",
        "--no-color",
        url
    ]
    kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True, "bufsize": 1}
    if os.name == "nt":
        kwargs["creationflags"] = CREATE_NO_WINDOW
    proc = subprocess.Popen(cmd, **kwargs)

    pct_re = re.compile(r"(\d+(?:\.\d+)?)%")
    try:
        # yt-dlp prints progress to stderr with --newline
        stderr = proc.stderr
        stdout = proc.stdout
        if stderr is None:
            raise RuntimeError("Failed to capture yt-dlp stderr")
        if stdout is None:
            raise RuntimeError("Failed to capture yt-dlp stdout")

        for line in stderr:
            if not line:
                continue
            m = pct_re.search(line)
            if m and on_progress:
                try:
                    pct = float(m.group(1))
                except Exception:
                    pct = 0.0
                on_progress(pct, 0.0)
        proc.wait()
    finally:
        try:
            if proc.stderr is not None:
                proc.stderr.close()
        except Exception:
            pass
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except Exception:
            pass
    if proc.returncode and proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed with code {proc.returncode}")
    return {"title": title}