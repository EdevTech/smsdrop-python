import datetime
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Optional, List


class ShipmentState(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    SCHEDULED = "SCHEDULED"


class MessageType(IntEnum):
    PLAIN_TEXT = 0
    FLASH_MESSAGE = 1
    UNICODE = 2


campaign_private_fields = [
    "_id",
    "_sms_count",
    "_message_count",
    "_delivery_percentage",
    "_status",
]
campaign_public_fields = [
    "title",
    "message",
    "message_type",
    "sender",
    "recipient_list",
    "defer_until",
    "defer_by",
]


@dataclass
class Campaign:
    message: str
    sender: str
    recipient_list: List[str] = field(repr=False)
    title: Optional[str] = None
    message_type: MessageType = MessageType.PLAIN_TEXT
    defer_until: Optional[datetime.datetime] = None
    defer_by: Optional[int] = None

    # private fields
    _status: ShipmentState = field(
        init=False, default=ShipmentState.PENDING, repr=False
    )
    _delivery_percentage: int = field(init=False, default=0, repr=False)
    _message_count: int = field(init=False, default=1, repr=False)
    _sms_count: int = field(init=False, default=1, repr=False)
    _id: Optional[str] = field(init=False, repr=False)

    def __post_init__(self):
        assert not (
            self.defer_until and self.defer_by
        ), "use either 'defer_until' or 'defer_by' or neither, not both"

    @property
    def id(self):
        return self._id

    @property
    def status(self):
        return self._status

    @property
    def delivery_percentage(self):
        return self._delivery_percentage

    @property
    def message_count(self):
        return self._message_count

    @property
    def sms_count(self):
        return self._sms_count

    def as_dict(
        self, strip: Optional[list] = None, only: Optional[list] = None
    ) -> dict:
        assert not (strip and only), "use either 'strip' or 'only' or neither, not both"
        # strip the '_' from the private fields
        fields = campaign_public_fields + [f[1:] for f in campaign_private_fields]
        fields = only if only else fields
        fields = filter(lambda f: f not in strip, fields) if strip else fields
        data = {
            key: getattr(self, key)
            for key in fields
            if getattr(self, key, None) is not None
        }
        if self.defer_until:
            data["defer_until"] = self.defer_until.isoformat()
        return data

    def update(self, data: dict):
        for f in campaign_private_fields:
            setattr(self, f, data.get(f[1:]))
        self.title = data["title"]

    @classmethod
    def from_response(cls, data: dict):
        defer_until = data["defer_until"]
        if defer_until:
            defer_until = datetime.datetime.fromisoformat(defer_until)
        private_data = {key: data.pop(key[1:]) for key in campaign_private_fields}
        cp = Campaign(**data)
        cp.message_type = MessageType(data["message_type"])
        for f in campaign_private_fields:
            setattr(cp, f, private_data[f])
        cp.defer_until = defer_until
        return cp


@dataclass(frozen=True)
class User:
    id: str
    email: str
    is_active: bool


@dataclass(frozen=True)
class Subscription:
    id: str
    nbr_sms: int
