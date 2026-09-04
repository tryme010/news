"""Retry helper with exponential backoff, used for all external API calls
(AI providers, Blogger, search engines, Telegram)."""
from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def retry_with_backoff(
    func: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
) -> T:
    """Call `func` with retries. Raises the last exception if all attempts fail."""
    attempt = 0
    last_exc: Exception | None = None
    while attempt < max_attempts:
        try:
            return func()
        except exceptions as exc:  # noqa: BLE001
            last_exc = exc
            attempt += 1
            if attempt >= max_attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.25)
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
