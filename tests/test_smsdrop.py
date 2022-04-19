import datetime
import string
import uuid

import httpx
import pytest
import secrets
from dataclasses import asdict
from faker import Faker
from pytest_httpx import HTTPXMock

from smsdrop import (
    Campaign,
    Client,
    DictStorage,
    MessageType,
    ShipmentState,
    Subscription,
    User,
)
from smsdrop.constants import (
    BASE_URL,
    CAMPAIGN_BASE_PATH,
    LOGIN_PATH,
    SUBSCRIPTION_PATH,
    USER_PATH,
)

TOKEN = secrets.token_urlsafe(32)
EMAIL = "degnonfrancis@gmail.com"


def get_user_dict(id_: str):
    return {
        "email": "jean@p.com",
        "id": id_,
        "is_active": True,
        "is_verified": True,
        "is_superuser": False,
    }


@pytest.fixture()
def client(httpx_mock: HTTPXMock) -> Client:
    def login_response(*args, **kwargs):
        return httpx.Response(
            json={"access_token": TOKEN},
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        login_response, url=BASE_URL + LOGIN_PATH, method="POST"
    )
    client = Client(
        email=EMAIL, password=secrets.token_urlsafe(12), storage=DictStorage()
    )
    # just to login
    client._login()  # noqa
    return client


@pytest.fixture()
def campaign(faker: Faker):
    return Campaign(
        title=faker.name(),
        message=faker.paragraph(nb_sentences=5),
        message_type=MessageType.PLAIN_TEXT,
        sender=secrets.choice(string.ascii_letters),
        recipient_list=[faker.phone_number()],
    )


def test_get_profile(client: Client, httpx_mock: HTTPXMock):
    id_ = str(uuid.uuid4())
    user = User.from_api_response(get_user_dict(id_))

    def custom_response(*args, **kwargs):
        return httpx.Response(
            json=get_user_dict(id_),
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        custom_response, method="GET", url=BASE_URL + USER_PATH
    )
    assert client.get_profile() == user


def test_read_subscription(client: Client, httpx_mock: HTTPXMock):
    created_at = datetime.datetime.now()
    sub_data = {"id": str(uuid.uuid4()), "nbr_sms": 1000}
    sub = Subscription(created_at=created_at, **sub_data)

    def custom_response(*args, **kwargs):
        sub_data["created_at"] = created_at.isoformat()
        return httpx.Response(
            json=sub_data,
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        custom_response, method="GET", url=BASE_URL + SUBSCRIPTION_PATH
    )
    assert client.get_subscription() == sub


def test_launch_campaign(
    client: Client, httpx_mock: HTTPXMock, campaign: Campaign
):
    id_ = str(uuid.uuid4())

    def custom_response(*args, **kwargs):
        return httpx.Response(
            json={
                **asdict(campaign),
                "id": id_,
                "status": ShipmentState.PENDING,
                "delivery_percentage": 0,
                "message_count": 1,
                "sms_count": 1,
                "created_at": datetime.datetime.now().isoformat()
            },
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        custom_response, method="POST", url=BASE_URL + CAMPAIGN_BASE_PATH
    )
    client.launch(campaign)
    assert campaign.id == id_


# def test_refresh_campaign(client: Client, httpx_mock: HTTPXMock):
#     pass


#
#
# def test_get_campaigns(client: Client, httpx_mock: HTTPXMock):
#     pass
#
#
# def test_send_message(client: Client, httpx_mock: HTTPXMock):
#     pass
#
#
# def test_retry_campaign(client: Client, httpx_mock: HTTPXMock):
#     pass
