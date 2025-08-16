# filepath: c:\dev\Github\YoutubeConverter\app\main.py
import os, sys, threading, queue, time, webbrowser
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Allow running both as "python -m app.main" and "python app/main.py"
try:
    from .version import __version__, APP_NAME
    from .settings import get_last_path, set_last_path, get_update_channel, set_update_channel
    from .settings import ensure_app_dirs, APP_DIR
    from .history import add_entry, recent
    from .updater_ytdlp import ensure_latest as ensure_latest_ytdlp, current_version as ytdlp_version
    from .updater_ytdlp import get_binary_path as ytdlp_path
    from .yt_downloader import search as yt_search, list_quality_options, download as yt_download
    from .app_updater import check_update, download_and_run_installer
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from app.version import __version__, APP_NAME
    from app.settings import get_last_path, set_last_path, get_update_channel, set_update_channel
    from app.settings import ensure_app_dirs, APP_DIR
    from app.history import add_entry, recent
    from app.updater_ytdlp import ensure_latest as ensure_latest_ytdlp, current_version as ytdlp_version
    from app.updater_ytdlp import get_binary_path as ytdlp_path
    from app.yt_downloader import search as yt_search, list_quality_options, download as yt_download
    from app.app_updater import check_update, download_and_run_installer

def restart_app():
    python = sys.executable
    os.execl(python, python, *sys.argv)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{__version__}")
        self.geometry("880x560")
        self.minsize(720, 480)

        self.status_q = queue.Queue()
        self.download_thread = None
        self.ytdlp_check_thread = None

        self._build_ui()
        self.after(300, self._kickoff_updates)

    def _build_ui(self):
        style = ttk.Style(self)
        try:
            self.call("tk", "scaling", 1.25)
        except Exception:
            pass
        # Header
        header = ttk.Frame(self, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="Step 1: Paste or Search", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(header, text="History", command=self._show_history).pack(side="right")
        ttk.Button(header, text="Advanced ▸", command=self._toggle_advanced).pack(side="right", padx=(0, 8))

        # Step 1
        s1 = ttk.Frame(self, padding=(16, 8))
        s1.pack(fill="x")
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(s1, textvariable=self.url_var, font=("Segoe UI", 12))
        url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(s1, text="Paste", command=self._paste_clipboard).pack(side="left")
        ttk.Button(s1, text="Search", command=self._do_search).pack(side="left", padx=(8,0))

        # Results
        self.results = tk.Listbox(self, height=8)
        self.results.pack(fill="both", expand=False, padx=16, pady=(0, 12))
        self.results.bind("<<ListboxSelect>>", self._pick_result)

        # Step 2
        s2h = ttk.Frame(self, padding=(16, 4)); s2h.pack(fill="x")
        ttk.Label(s2h, text="Step 2: Choose Quality", font=("Segoe UI", 12, "bold")).pack(side="left")
        s2 = ttk.Frame(self, padding=(16, 4)); s2.pack(fill="x")
        self.quality_var = tk.StringVar()
        self.quality_map = list_quality_options("")
        labels = [l for (l, _) in self.quality_map]
        self.quality = ttk.Combobox(s2, values=labels, textvariable=self.quality_var, state="readonly")
        self.quality.current(0)
        self.quality.pack(side="left", fill="x", expand=True)
        ttk.Button(s2, text="Refresh options", command=self._refresh_quality).pack(side="left", padx=(8, 0))

        # Step 3
        s3h = ttk.Frame(self, padding=(16, 4)); s3h.pack(fill="x")
        ttk.Label(s3h, text="Step 3: Choose Download Path", font=("Segoe UI", 12, "bold")).pack(side="left")
        s3 = ttk.Frame(self, padding=(16, 8)); s3.pack(fill="x")
        self.path_var = tk.StringVar(value=get_last_path())
        ttk.Entry(s3, textvariable=self.path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(s3, text="Browse…", command=self._browse).pack(side="left", padx=(8, 0))
        ttk.Button(s3, text="Download", command=self._download).pack(side="left", padx=(8, 0))

        # Progress + info
        prog = ttk.Frame(self, padding=(16, 4)); prog.pack(fill="x")
        self.pbar = ttk.Progressbar(prog, mode="determinate"); self.pbar.pack(fill="x", expand=True)
        info = ttk.Frame(self, padding=(16, 4)); info.pack(fill="x")
        self.info_lbl = ttk.Label(info, text="Ready."); self.info_lbl.pack(side="left")
        self.ytdlp_lbl = ttk.Label(info, text=f"yt-dlp: {ytdlp_version() or 'checking…'}    ({ytdlp_path()})")
        self.ytdlp_lbl.pack(side="right")

        # Advanced (hidden)
        self.adv_frame = ttk.Frame(self, padding=(16, 8), relief="groove")
        self.adv_visible = False
        self.channel_var = tk.StringVar(value=get_update_channel())
        ttk.Label(self.adv_frame, text="Update channel (app):").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(self.adv_frame, text="Stable", value="stable", variable=self.channel_var,
                        command=lambda: set_update_channel(self.channel_var.get())).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(self.adv_frame, text="Prerelease", value="prerelease", variable=self.channel_var,
                        command=lambda: set_update_channel(self.channel_var.get())).grid(row=0, column=2, sticky="w")
        ttk.Radiobutton(self.adv_frame, text="Nightly", value="nightly", variable=self.channel_var,
                        command=lambda: set_update_channel(self.channel_var.get())).grid(row=0, column=3, sticky="w")
        for i in range(4): self.adv_frame.grid_columnconfigure(i, weight=1)

        # Bottom update banner
        self.banner = ttk.Frame(self, padding=(16, 10))
        self.banner.pack(side="bottom", fill="x")
        self.banner_lbl = ttk.Label(self.banner, foreground="#0a7")
        self.banner_lbl.pack(side="left")
        self.banner_prog = ttk.Progressbar(self.banner, mode="determinate", length=160)
        self.banner_prog.pack(side="right")
        self._set_banner("")
    def _set_banner(self, text: str, pct: Optional[float] = None, warn: bool = False):
        self.banner_lbl.configure(text=text or "")
        if pct is None:
            self.banner_prog["value"] = 0
        else:
            self.banner_prog["value"] = max(0, min(100, pct))
        self.banner_lbl.configure(foreground="#d66" if warn else "#0a7")

    def _toggle_advanced(self):
        if self.adv_visible:
            self.adv_frame.pack_forget()
        else:
            self.adv_frame.pack(fill="x", padx=16, pady=8)
        self.adv_visible = not self.adv_visible

    def _paste_clipboard(self):
        try:
            self.url_var.set(self.clipboard_get())
        except Exception:
            pass

    def _do_search(self):
        q = self.url_var.get().strip()
        if not q:
            return
        self.results.delete(0, tk.END)
        self.info_lbl.configure(text="Searching…")
        def worker():
            try:
                results = yt_search(q, 10)
                self.status_q.put(("search_done", results))
            except Exception as e:
                self.status_q.put(("error", f"Search failed: {e}"))
        threading.Thread(target=worker, daemon=True).start()
        self.after(50, self._poll_status)

    def _pick_result(self, _evt):
        sel = self.results.curselection()
        if not sel: return
        title, url = self.results.get(sel[0]).split(" | ", 1)
        self.url_var.set(url)

    def _refresh_quality(self):
        # Keep it simple; presets already set
        messagebox.showinfo("Info", "Quality options refreshed.")

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.path_var.get() or get_last_path(), title="Select download folder")
        if d:
            self.path_var.set(d)
            set_last_path(d)

    def _download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Paste a YouTube link or search first.")
            return
        outdir = self.path_var.get().strip() or get_last_path()
        Path(outdir).mkdir(parents=True, exist_ok=True)
        set_last_path(outdir)
        # Map label -> format
        label = self.quality_var.get() or "Best (video+audio)"
        fmt = next((f for (l, f) in self.quality_map if l == label), "bv*+ba/b")
        self.pbar["value"] = 0
        self.info_lbl.configure(text="Starting download…")
        def worker():
            try:
                def onp(pct, _spd):
                    self.status_q.put(("dl_progress", pct))
                info = yt_download(url, fmt, outdir, on_progress=onp)
                title = info.get("title") or "Video"
                outfiles = []
                if "requested_downloads" in info and info["requested_downloads"]:
                    outfiles = [d.get("filepath") for d in info["requested_downloads"] if d.get("filepath")]
                elif "filepath" in info:
                    outfiles = [info["filepath"]]
                outpath = outfiles[0] if outfiles else outdir
                add_entry(title, url, outpath)
                self.status_q.put(("dl_done", title))
            except Exception as e:
                self.status_q.put(("error", f"Download failed: {e}"))
        self.download_thread = threading.Thread(target=worker, daemon=True)
        self.download_thread.start()
        self.after(50, self._poll_status)

    def _poll_status(self):
        try:
            while True:
                tag, payload = self.status_q.get_nowait()
                if tag == "search_done":
                    self.results.delete(0, tk.END)
                    for item in payload:
                        self.results.insert(tk.END, f"{item['title']} | {item['url']}")
                    self.info_lbl.configure(text=f"Found {len(payload)} result(s).")
                elif tag == "dl_progress":
                    self.pbar["value"] = float(payload)
                    self.info_lbl.configure(text=f"Downloading… {payload:.1f}%")
                elif tag == "dl_done":
                    self.pbar["value"] = 100
                    self.info_lbl.configure(text=f"Done: {payload}")
                elif tag == "ytdlp_status":
                    self._set_banner(payload)
                elif tag == "ytdlp_progress":
                    done, total = payload
                    pct = (done / total * 100) if total else 0
                    self._set_banner(f"Updating yt-dlp… {pct:.0f}%. App will restart when done.", pct)
                elif tag == "ytdlp_updated":
                    self._set_banner(f"yt-dlp updated to {payload}. Restarting…", 100)
                    self.after(800, restart_app)
                elif tag == "app_update_available":
                    ver = payload
                    self._set_banner(f"New app version {ver} available. Downloading…", 0)
                elif tag == "app_update_progress":
                    done, total = payload
                    pct = (done / total * 100) if total else 0
                    self._set_banner(f"Downloading update… {pct:.0f}%", pct)
                elif tag == "error":
                    self._set_banner(str(payload), warn=True)
                    messagebox.showerror("Error", str(payload))
        except queue.Empty:
            pass
        if (self.download_thread and self.download_thread.is_alive()) or (self.ytdlp_check_thread and self.ytdlp_check_thread.is_alive()):
            self.after(100, self._poll_status)

    def _kickoff_updates(self):
        # 1) Ensure yt-dlp latest
        def ytdlp_worker():
            try:
                def st(msg): self.status_q.put(("ytdlp_status", msg))
                def pr(done, total): self.status_q.put(("ytdlp_progress", (done, total)))
                st("Checking yt-dlp…")
                updated, old, new = ensure_latest_ytdlp(on_status=st, on_progress=pr)
                self.ytdlp_lbl.configure(text=f"yt-dlp: {ytdlp_version() or new}    ({ytdlp_path()})")
                if updated:
                    self.status_q.put(("ytdlp_updated", new))
                else:
                    self._set_banner(f"yt-dlp is up to date ({new}).", None)
                    # 2) Optionally check for app update (silent)
                    ch = get_update_channel()
                    upd = check_update(ch)
                    if upd:
                        ver, url = upd
                        self.status_q.put(("app_update_available", ver))
                        def onp(done, total): self.status_q.put(("app_update_progress", (done, total)))
                        download_and_run_installer(url, on_progress=onp)
                        # Allow installer to start, then exit
                        time.sleep(1.0)
                        self.quit()
            except Exception as e:
                self.status_q.put(("error", f"yt-dlp update failed: {e}"))
        self.ytdlp_check_thread = threading.Thread(target=ytdlp_worker, daemon=True)
        self.ytdlp_check_thread.start()
        self.after(50, self._poll_status)

    def _show_history(self):
        win = tk.Toplevel(self)
        win.title("History (last 7 days)")
        win.geometry("640x360")
        cols = ("When", "Title", "Open")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols: tree.heading(c, text=c)
        tree.pack(fill="both", expand=True)
        import datetime as dt, time as tm
        for item in recent():
            when = dt.datetime.fromtimestamp(item["ts"]).strftime("%Y-%m-%d %H:%M")
            title = item.get("title") or ""
            path = item.get("path") or ""
            tree.insert("", "end", values=(when, title, "Open"), tags=(path,))
        def on_click(e):
            sel = tree.selection()
            if not sel: return
            path = tree.item(sel[0], "tags")[0]
            if path and os.path.exists(path):
                folder = path if os.path.isdir(path) else os.path.dirname(path)
                os.startfile(folder) if sys.platform.startswith("win") else webbrowser.open(f"file://{folder}")
        tree.bind("<Double-1>", on_click)

if __name__ == "__main__":
    ensure_app_dirs()
    app = App()
    app.mainloop()