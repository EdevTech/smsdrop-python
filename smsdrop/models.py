import datetime
from abc import ABCMeta

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import List, Optional


class MessageType(IntEnum):
    PLAIN_TEXT = 0
    FLASH_MESSAGE = 1
    UNICODE = 2


@dataclass(order=True, frozen=True)
class CampaignBase(metaclass=ABCMeta):
    """Common property for campaign"""

    message: str
    sender: str
    recipient_list: List[str] = field(repr=False, compare=False)
    title: str
    message_type: MessageType
    defer_until: datetime.datetime = field(hash=False)
    defer_by: int


@dataclass(order=True, frozen=True)
class CampaignCreate(CampaignBase):
    """Data class use to create a new campaign.

    :param str title: A title intended to help you identify this campaign,
    a random name will be generated if you do not provide one.
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

    title: str = None
    message_type: MessageType = MessageType.PLAIN_TEXT
    defer_until: Optional[datetime.datetime] = None
    defer_by: Optional[int] = None

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
        if self.defer_until:
            data["defer_until"] = self.defer_until.isoformat()
        return data


@dataclass(frozen=True, order=True)
class Campaign(CampaignBase):
    """Data returned to the user"""

    delivery_percentage: int
    message_count: int
    sms_count: int
    status: str
    id: str = field(compare=False)


@dataclass(frozen=True)
class User:
    """Base user class"""

    id: str
    email: str
    is_active: bool


@dataclass(frozen=True)
class Subscription:
    """Base subscription class"""

    id: str
    nbr_sms: int
