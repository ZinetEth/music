from collections.abc import Callable
from time import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Small in-memory helper for inexpensive process-local caching."""

    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        value = self._store.get(key)
        if value is None:
            return None
        expires_at, payload = value
        if expires_at < time():
            self._store.pop(key, None)
            return None
        return payload

    def set(self, key: str, value: T) -> None:
        self._store[key] = (time() + self.ttl_seconds, value)

    def get_or_set(self, key: str, factory: Callable[[], T]) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value)
        return value

