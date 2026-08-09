# apps/core/timing.py
import time

def normalize_response_time(start: float, min_seconds: float = 0.5) -> None:
    """
    Pad the response so it takes at least `min_seconds`,
    preventing timing-based enumeration attacks.
    """
    elapsed = time.monotonic() - start
    if elapsed < min_seconds:
        time.sleep(min_seconds - elapsed)