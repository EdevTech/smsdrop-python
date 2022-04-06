from __future__ import annotations

import redis
from dataclasses import asdict, dataclass, field
from typing import Protocol


class Storage(Protocol):
    def get(self, key: str) -> str | None:
        pass

    def set(self, key: str, value: str) -> None:
        pass

    def delete(self, key: str) -> str | None:
        pass


class DummyStorage:
    def get(self, key: str) -> str | None:
        pass

    def set(self, key: str, value: str) -> None:
        pass

    def delete(self, key: str) -> str | None:
        pass


@dataclass
class DictStorage:
    _data: dict = field(default_factory=dict, repr=False)

    def get(self, key) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value

    def delete(self, key: str) -> str | None:
        return self._data.pop(key, None)


@dataclass
class RedisStorage:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    username: str | None = None
    password: str | None = None
    expires_seconds: int | None = None

    def __post_init__(self):
        credentials = asdict(self)
        credentials.pop("expires_seconds")
        self._client = redis.Redis(**credentials, decode_responses=True)

    def get(self, key: str) -> str | None:
        return self._client.get(key)

    def set(self, key: str, value: str):
        self._client.set(name=key, value=value, ex=self.expires_seconds)

    def delete(self, key: str) -> str | None:
        return self._client.delete(key)
