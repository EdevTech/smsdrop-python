from abc import ABCMeta, abstractmethod

import redis
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class BaseStorage(metaclass=ABCMeta):
    @abstractmethod
    def get(self, key, **kwargs):
        pass

    @abstractmethod
    def set(self, key, value, expires, **kwargs):
        pass

    @abstractmethod
    def delete(self, key, **kwargs):
        pass


@dataclass
class DummyStorage(BaseStorage):
    @abstractmethod
    def get(self, *args, **kwargs):
        pass

    @abstractmethod
    def set(self, *args, **kwargs):
        pass

    @abstractmethod
    def delete(self, key, **kwargs):
        pass


@dataclass
class DictStorage(BaseStorage):
    data: dict = field(default_factory=dict)

    def get(self, key, **_):
        return self.data.get(key, None)

    def set(self, key, value, **kwargs):
        self.data[key] = value

    def delete(self, key, **_):
        self.data.pop(key)


@dataclass
class RedisStorage(BaseStorage):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    username: Optional[str] = None
    password: Optional[str] = None

    def __post_init__(self):
        self._client = redis.Redis(**asdict(self), decode_responses=True)

    def get(self, key, **_):
        return self._client.get(key)

    def set(self, key, value, expires: int, **_):
        self._client.set(name=key, value=value, ex=expires)

    def delete(self, key, **_):
        self._client.delete(key)
