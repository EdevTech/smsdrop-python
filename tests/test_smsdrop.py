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
    __version__,
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


def test_version():
    assert __version__ == "0.1.0"


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
    return Client(
        email=EMAIL, password=secrets.token_urlsafe(12), storage=DictStorage()
    )


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
    assert client._token == TOKEN
    assert client.context == BASE_URL


def test_read_me(client: Client, httpx_mock: HTTPXMock):
    user = User(id=str(uuid.uuid4()), email=EMAIL, is_active=True)

    def custom_response(*args, **kwargs):
        return httpx.Response(
            json=asdict(user),
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        custom_response, method="GET", url=BASE_URL + USER_PATH
    )
    user_result = client.read_me()
    assert user_result == user


def test_read_subscription(client: Client, httpx_mock: HTTPXMock):
    sub = Subscription(id=str(uuid.uuid4()), nbr_sms=1000)

    def custom_response(*args, **kwargs):
        return httpx.Response(
            json=asdict(sub),
            status_code=httpx.codes.OK,
        )

    httpx_mock.add_callback(
        custom_response, method="GET", url=BASE_URL + SUBSCRIPTION_PATH
    )
    sub_result = client.read_subscription()
    assert sub_result == sub


def test_launch_campaign(
    client: Client, httpx_mock: HTTPXMock, campaign: CampaignCreate
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
    cp_result = client.launch_campaign(campaign)
    assert cp_result == cp


def test_read_campaign(client: Client, httpx_mock: HTTPXMock):
    pass


def test_read_campaigns(client: Client, httpx_mock: HTTPXMock):
    pass


def test_send_message(client: Client, httpx_mock: HTTPXMock):
    pass


def test_retry_campaign(client: Client, httpx_mock: HTTPXMock):
    pass
