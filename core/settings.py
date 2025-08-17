import json
import os
from dataclasses import dataclass, asdict, field

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
SETTINGS_PATH = os.path.join(ROOT_DIR, "settings.json")


@dataclass
class UISettings:
    auto_advance: bool = True
    reset_after_downloads: bool = True
    accent_color_hex: str = "#F28C28"
    auto_fetch_urls: bool = True
    auto_search_text: bool = True
    clear_input_after_fetch: bool = True
    live_search: bool = True  # New: debounce live search while typing
    search_debounce_seconds: int = 3  # New: inactivity time before searching
    fast_paste_enabled: bool = True  # New: use fast paste logic for URLs
    quality_refetch_seconds: int = 1  # New: refetch delay on Quality tab


# Hidden (For first start only)
@dataclass
class DefaultsSettings:
    kind: str = "audio"
    format: str = "mp3"


@dataclass
class YtDlpSettings:
    auto_update: bool = True
    branch: str = "stable"


@dataclass
class AppUpdateSettings:
    auto_update: bool = True
    channel: str = "prerelease"


@dataclass
class AppSettings:
    last_download_dir: str = field(
        default_factory=lambda: os.path.expanduser("~/Downloads")
    )
    ui: UISettings = field(default_factory=UISettings)
    defaults: DefaultsSettings = field(default_factory=DefaultsSettings)
    ytdlp: YtDlpSettings = field(default_factory=YtDlpSettings)
    app: AppUpdateSettings = field(default_factory=AppUpdateSettings)


class SettingsManager:
    def load(self) -> AppSettings:
        if not os.path.exists(SETTINGS_PATH):
            return AppSettings()
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Migrate/merge
            ui = UISettings(**data.get("ui", {}))
            defaults = DefaultsSettings(**data.get("defaults", {}))
            ytdlp = YtDlpSettings(**data.get("ytdlp", {}))
            app = AppUpdateSettings(**data.get("app", {}))
            return AppSettings(
                last_download_dir=data.get(
                    "last_download_dir", AppSettings().last_download_dir
                ),
                ui=ui,
                defaults=defaults,
                ytdlp=ytdlp,
                app=app,
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings):
        data = asdict(settings)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
