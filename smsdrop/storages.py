from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional

import redis


@dataclass
class BaseStorage(metaclass=ABCMeta):
    @abstractmethod
    def get(self, *args, **kwargs):
        pass

    @abstractmethod
    def set(self, *args, **kwargs):
        pass

    @abstractmethod
    def delete(self, *args, **kwargs):
        pass


@dataclass
class Dummy(BaseStorage):
    def get(self, *args, **kwargs):
        pass

    def set(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass


@dataclass
class SimpleDict(BaseStorage):
    data: dict = field(default_factory=dict)

    def get(self, key):
        return self.data.get(key, None)

    def set(self, key, value):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key)


@dataclass
class Redis(BaseStorage):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    username: Optional[str] = None
    password: Optional[str] = None

    def __post_init__(self):
        self._client = redis.Redis(**asdict(self), decode_responses=True)

    def get(self, key):
        return self._client.get(key)

    def set(self, key, value, ex: int):
        self._client.set(name=key, value=value, ex=ex)

    def delete(self, key):
        self._client.delete(key)
