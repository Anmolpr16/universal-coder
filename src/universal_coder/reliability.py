from __future__ import annotations
from dataclasses import dataclass

TRANSIENT_MARKERS = (
    'timeout', 'timed out', 'temporarily unavailable', 'connection reset',
    'connection refused', 'connection aborted', 'try again', 'rate limit',
    '429', '503', '502', '504', 'resource temporarily unavailable',
)

@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0

    def delay(self, retry_number: int) -> float:
        return min(self.max_delay, self.base_delay * (2 ** max(0, retry_number - 1)))

def classify_error(error: str) -> tuple[str, bool]:
    value = (error or '').lower()
    if any(marker in value for marker in TRANSIENT_MARKERS):
        return 'transient', True
    if 'permission denied' in value or 'blocked dangerous' in value or 'denied' in value:
        return 'policy', False
    if 'unknown tool' in value or 'json' in value or 'keyerror' in value:
        return 'invalid_request', False
    return 'permanent', False
