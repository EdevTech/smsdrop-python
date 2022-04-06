from __future__ import annotations

import datetime
import logging
from functools import partial

import httpx
from dataclasses import dataclass, field
from tenacity import retry, retry_if_exception_type, stop_after_attempt
from typing import List, Optional

from .constants import (
    ACCESS_TOKEN_STORAGE_KEY,
    BASE_URL,
    CAMPAIGN_BASE_PATH,
    CAMPAIGN_RETRY_PATH,
    SUBSCRIPTION_PATH,
    USER_PATH,
)
from .errors import (
    BadTokenError,
    InsufficientSmsError,
    ServerError,
    ValidationError,
)
from .models import Campaign, Subscription, User
from .storages import DictStorage, Storage
from .utils import (
    cast_message_type,
    get_access_token,
    get_json_response,
    log_request,
    log_response,
)

_logger = logging.getLogger(__name__)


@dataclass
class Client:
    """Main module class that make the requests to the smsdrop api
    :argument str email: The email address of your smsdrop account, defaults to [None]
    :argument str password: Your smsdrop account password
    :argument Optional[str] context: Root url of the api
    :argument Optional[BaseStorage] storage: A storage object that will be use
    to store the api token
    :argument Optional[logging.Logger] logger: A logger instance with your own config
    :raises BadCredentialsError: If the password or/and email your provided
    are incorrect
    """

    email: str
    password: str
    context: str = BASE_URL
    storage: Storage = DictStorage()
    logger: logging.Logger = _logger
    _http_client: httpx.Client = field(default=None, repr=False, init=False)
    _get_token: callable = field(default=None, repr=False, init=False)

    def __post_init__(self):
        self._http_client = httpx.Client(
            base_url=self.context,
            timeout=15,
            event_hooks={
                "request": [lambda request: log_request(request, self.logger)],
                "response": [
                    lambda response: log_response(response, self.logger)
                ],
            },
        )
        self._get_token = partial(
            get_access_token,
            storage=self.storage,
            email=self.email,
            password=self.password,
            http_client=self._http_client,
        )

    @retry(
        stop=stop_after_attempt(2),
        retry=retry_if_exception_type(BadTokenError),
        reraise=True,
    )
    def _send_request(
        self, path: str, payload: dict | None = None
    ) -> httpx.Response:
        kwargs = {"url": path}
        if payload:
            kwargs.update(
                {
                    "json": {
                        key: value for key, value in payload.items() if value
                    },
                    "headers": {"content-type": "application/json"},
                }
            )
        get = getattr(self._http_client, "get")
        post = getattr(self._http_client, "post")
        response: httpx.Response = post(**kwargs) if payload else get(**kwargs)
        if response.status_code == httpx.codes.UNAUTHORIZED:
            self._http_client.headers[
                "Authorization"
            ] = f"Bearer {self._get_token()}"
            self.storage.delete(ACCESS_TOKEN_STORAGE_KEY)
            raise BadTokenError(response.request.url)
        if httpx.codes.is_server_error(response.status_code):
            raise ServerError("The server is failing, try later")
        if response.status_code == httpx.codes.UNPROCESSABLE_ENTITY:
            raise ValidationError(errors=response.json()["detail"])
        return response

    def send_message(
        self,
        message: str,
        sender: str,
        phone: str,
        dispatch_date: Optional[datetime.datetime] = None,
    ) -> Campaign:
        """Send a simple message to a single recipient.

        This is just a convenient helper to send sms to a unique recipient,
        internally it work exactly as a campaign and create a new campaign.

        :param message: The content of your message
        :param sender: The sender that will be displayed on the recipient phone
        :param phone: The recipient's phone number, Ex: +229XXXXXXXX
        :param dispatch_date: The date you want the message to be sent
        :return: An instance of the class py:class::`smsdrop.Campaign`
        :rtype: Campaign
        :raises ValidationError: if some of the data you provided are not valid
        :raises ServerError: If the server if failing for some obscure reasons
        :raises InsufficientSmsError: If the number of sms available on your account is
        insufficient to send the message
        """

        cp = Campaign(
            message=message,
            sender=sender,
            recipient_list=[phone],
            defer_until=dispatch_date,
        )
        return self.launch_campaign(cp)

    def launch_campaign(self, campaign: Campaign) -> Campaign:
        """Send a request to the api to launch a new campaign from the
        `smsdrop.CampaignIn` instance provided

        Note that the campaign is always created even if an exception is raised,
        the instance your provide is updated with the response from the api.
        For example `campaign.id` will always be available even the campaign is
        not launched, it is always created except if there are some validation errors,
        you can use `client.retry(campaign.id)` to retry after you

        :param campaign: An instance of the class `smsdrop.CampaignIn`
        :raises InsufficientSmsError: If the number of sms available on your account is
        insufficient to launch the campaign
        :raises ValidationError: if the campaign data you provided is not valid
        :raises ServerError: If the server if failing for some obscure reasons
        """

        response = self._send_request(
            path=CAMPAIGN_BASE_PATH, payload=campaign.as_dict()
        )
        content = get_json_response(response)
        if response.status_code == httpx.codes.CREATED:
            raise InsufficientSmsError(
                content["id"],
                "Insufficient sms credits to launch this campaign",
            )
        return Campaign(**cast_message_type(content))

    def retry_campaign(self, id: str):
        """Retry a campaign if it was not launch due to insufficient sms on the user
         account

        :param id: The id of your campaign
        :raises ServerError: If the server if failing for some obscure reasons
        """

        payload = {"id": id}
        response = self._send_request(
            path=CAMPAIGN_RETRY_PATH, payload=payload
        )
        if response.status_code == codes.CREATED:
            raise InsufficientSmsError(
                id, "Insufficient sms credits to launch this campaign"
            )

    def read_campaign(self, id: str) -> Optional[Campaign]:
        """Get a campaign data based on an id

        :param id: The cmapign id
        :return: An instance of `smsdrop.CampaignIn`
        """

        request_path = CAMPAIGN_BASE_PATH + f"{id}"
        response = self._send_request(path=request_path)
        if response.status_code == codes.NOT_FOUND:
            return None
        content = get_json_response(response)
        return Campaign(**cast_message_type(content))

    def read_campaigns(
        self, skip: int = 0, limit: int = 100
    ) -> List[Campaign]:
        """Get mutliple campaigns from the api

        :param skip: starting index
        :param limit: The maximum amount of element to get
        :return:
        """
        request_path = CAMPAIGN_BASE_PATH + f"?skip={skip}&limit={limit}"
        response = self._send_request(path=request_path)
        return [Campaign(**cast_message_type(cp)) for cp in response.json()]

    def read_subscription(self) -> Subscription:
        """Get your subsctiption informations

        :raises ServerError: If the server if failing for some obscure reasons
        :return: An instance of the `smsdrop.Subscription` class
        """

        response = self._send_request(path=SUBSCRIPTION_PATH)
        content = get_json_response(response)
        return Subscription(id=content["id"], nbr_sms=content["nbr_sms"])

    def read_me(self) -> User:
        """Get your profile informations

        :raises ServerError: If the server if failing for some obscure reasons
        :return: An instance of the `smsdrop.User` class
        """

        response = self._send_request(path=USER_PATH)
        content = get_json_response(response)
        return User(
            email=content["email"],
            id=content["id"],
            is_active=content["is_active"],
        )
