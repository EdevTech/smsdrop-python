from __future__ import annotations

import datetime

from dataclasses import asdict, dataclass
from typing import Optional

from .utils import MessageType, ShipmentState


@dataclass
class Campaign:
    """Represent a sms campaign
    :param str title: A title intended to help you identify this campaign,
        a random name will be generated if you do not provide one
    :param str message: The content of your message
    :param MessageType message_type: The message type, the possible values are
        `MessageType.PLAIN_TEXT`, `MessageType.UNICODE`, `MessageType.FLASH_MESSAGE`
    :param str sender:  The sender name that will be displayed on the recipient's phone.
    :param Optional[datetime.datetime] defer_until: The launch date of your campaign.
    It is recommended to specify your timezone infos in order to avoid surprises.
    :param Optional[int] defer_by: The number of seconds the launch will be postponed.
    :param List[str] recipient_list: The list of users the message will be sent to.
    Ex ["phone1", "phone2"]. The phone number format is '{code}{local_number}' ,
    Ex: +22963588213, the "+" at the beginning is optional.
    """

    message: str
    sender: str
    recipient_list: list[str]
    message_type: MessageType = MessageType.PLAIN_TEXT
    defer_until: Optional[datetime.datetime] = None
    defer_by: Optional[int] = None
    id: str | None = None
    title: str | None = None
    delivery_percentage: int = 0
    message_count: int = 0
    sms_count: int = 1
    status: ShipmentState = ShipmentState.PENDING
    created_at: datetime.datetime | None = None

    def __post_init__(self):
        assert not (
            self.defer_until and self.defer_by
        ), "use either 'defer_until' or 'defer_by' or neither, not both"
        cond_a = self.sender.isalnum() and len(self.sender) > 11
        cond_b = self.sender.isnumeric() and len(self.sender) > 18
        assert not cond_a, "must be <= 11 character if alphanumeric"
        assert not cond_b, "must be <= 18 character if numeric"
        assert (
            len(self.recipient_list) >= 1
        ), "recipient list must contain at least one phone number"

    def as_dict(self) -> dict:
        data = asdict(self)
        data.pop("created_at")
        if self.defer_until:
            data["defer_until"] = self.defer_until.isoformat()
        return data

    def update(self, data: dict) -> None:
        self.status = ShipmentState(data["status"])
        self.delivery_percentage = data["delivery_percentage"]
        self.sms_count = data["sms_count"]
        self.message_count = data["message_count"]
        self.id = data["id"]
        self.title = data["title"]
        self.created_at = datetime.datetime.fromisoformat(data["created_at"])

    @classmethod
    def from_api_response(cls, data) -> "Campaign":
        message_type = MessageType(data.pop("message_type"))
        status = ShipmentState(data.pop("status"))
        created_at = datetime.datetime.fromisoformat(data.pop("created_at"))
        defer_until = data.pop("defer_until")
        if defer_until:
            defer_until = datetime.datetime.fromisoformat(defer_until)
        return Campaign(
            **data,
            message_type=message_type,
            status=status,
            created_at=created_at,
            defer_until=defer_until,
        )


@dataclass(frozen=True)
class User:
    """Base user class"""

    id: str
    email: str
    is_active: bool
    is_verified: bool

    @classmethod
    def from_api_response(cls, data: dict) -> "User":
        data.pop("is_superuser")
        return cls(**data)


@dataclass(frozen=True)
class Subscription:
    """Base subscription class"""

    id: str
    nbr_sms: int
    created_at: datetime.datetime

    @classmethod
    def from_api_response(cls, data: dict) -> "Subscription":
        created_at = datetime.datetime.fromisoformat(data.pop("created_at"))
        return Subscription(**data, created_at=created_at)
