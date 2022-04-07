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


@pytest.fixture()
def client(httpx_mock: HTTPXMock) -> Client:
    def custom_response(*args, **kwargs):
        return httpx.Response(
            json={"access_token": TOKEN},
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        custom_response, url=BASE_URL + LOGIN_PATH, method="POST"
    )
    client = Client(
        email=EMAIL, password=secrets.token_urlsafe(12), storage=DictStorage()
    )
    # just to login
    client.get_profile()
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


def test_faker(faker):
    assert isinstance(faker.name(), str)


def test_client(client: Client):
    assert client._get_access_token() == TOKEN
    assert client.context == BASE_URL


def test_get_profile(client: Client, httpx_mock: HTTPXMock):
    user = User(
        id=str(uuid.uuid4()), email=EMAIL, is_active=True, is_verified=False
    )

    def custom_response(*args, **kwargs):
        return httpx.Response(
            json=asdict(user),
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        custom_response, method="GET", url=BASE_URL + USER_PATH
    )
    user_result = client.get_profile()
    assert user_result == user


def test_read_subscription(client: Client, httpx_mock: HTTPXMock):
    sub = Subscription(
        id=str(uuid.uuid4()), nbr_sms=1000, created_at=datetime.datetime.now()
    )

    def custom_response(*args, **kwargs):
        return httpx.Response(
            json=asdict(sub),
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        custom_response, method="GET", url=BASE_URL + SUBSCRIPTION_PATH
    )
    sub_result = client.get_subscription()
    assert sub_result == sub


def test_launch_campaign(
    client: Client, httpx_mock: HTTPXMock, campaign: Campaign
):
    cp = Campaign(
        **asdict(campaign),
        id=str(uuid.uuid4()),
        status=ShipmentState.PENDING,
        delivery_percentage=0,
        message_count=1,
        sms_count=1,
    )

    def custom_response(*args, **kwargs):
        return httpx.Response(
            json=asdict(cp),
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        custom_response, method="POST", url=BASE_URL + CAMPAIGN_BASE_PATH
    )
    client.launch(campaign)
    assert cp == campaign


def test_refresh_campaign(client: Client, httpx_mock: HTTPXMock):
    pass


def test_get_campaigns(client: Client, httpx_mock: HTTPXMock):
    pass


def test_send_message(client: Client, httpx_mock: HTTPXMock):
    pass


def test_retry_campaign(client: Client, httpx_mock: HTTPXMock):
    pass
