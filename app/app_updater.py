from typing import Optional, Tuple, Callable

def check_update(_channel: str) -> Optional[Tuple[str, str]]:
    """
    Return (version, download_url) if an app update is available.
    Stubbed to None; implement against your release pipeline if needed.
    """
    return None

def download_and_run_installer(_url: str, on_progress: Callable[[int, int], None]):
    """
    Stub: No-op. Implement to download your installer and run it silently.
    """
    on_progress(1, 1)
