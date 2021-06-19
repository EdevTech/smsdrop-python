import datetime
import json
import logging

import httpx
from dataclasses import dataclass
from httpx import Request, Response, codes
from tenacity import retry, retry_if_exception_type, stop_after_attempt
from typing import List, Optional

from .constants import (
    BASE_URL,
    CAMPAIGN_BASE_PATH,
    CAMPAIGN_RETRY_PATH,
    LOGIN_PATH,
    SUBSCRIPTION_PATH,
    TOKEN_LIFETIME,
    USER_PATH,
)
from .exceptions import (
    BadCredentialsError,
    BadTokenError,
    InsufficientSmsError,
    ServerError,
    ValidationError,
)
from .helpers import get_json_response, log_request_error
from .models import Campaign, Subscription, User, campaign_public_fields
from .storages import BaseStorage, SimpleDict

_logger = logging.getLogger(__name__)


def log_request(request: Request):
    json_content = (
        json.loads(request.content) if request.method == "POST" else {}
    )
    _logger.debug(
        f"Request: {request.method} {request.url} - Waiting for response\n"
        f"Content: \n {json.dumps(json_content, indent=2, sort_keys=True)}"
    )


def log_response(response: Response):
    request = response.request
    _logger.debug(
        f"Response: {request.method} {request.url} - Status {response.status_code}\n"
        f"Content : \n {json.dumps(response.json(), indent=2, sort_keys=True)}"
    )


@dataclass
class Client:
    """Main module class that make the requests to the smsdrop api.

    :param str email: The email address of your smsdrop api account
    :param str password: Your account password, default to 1
    :param Optional[BaseStorage] storage: A storage object that will be use
    to store the api token
    :param Optional[str] context: Root url of the api, defaults to None
    :raises BadCredentialsError: If the password or/and email your provided
    are incorrect
    """

    email: str
    password: str
    context: str = BASE_URL
    storage: BaseStorage = SimpleDict()

    def __post_init__(self):
        self.logger = _logger
        self._http_client = httpx.Client(base_url=self.context)
        self._refresh_token()
        self._http_client.event_hooks = {
            "request": [log_request],
            "response": [log_response],
        }

    def _refresh_token(self):
        token = self._login()
        self._set_token(new_token=token)
        self._http_client.headers["Authorization"] = f"Bearer {self._token}"

    @property
    def _token_storage_key(self):
        return f"bearer_token_{self.password}"

    @property
    def _token(self):
        return self.storage.get(self._token_storage_key)

    def _set_token(self, new_token):
        self.storage.set(self._token_storage_key, new_token, ex=TOKEN_LIFETIME)

    @log_request_error
    def _login(self) -> str:
        response = httpx.post(
            url=self.context + LOGIN_PATH,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"username": self.email, "password": self.password},
        )
        if response.status_code == codes.BAD_REQUEST:
            raise BadCredentialsError("Your credentials are incorrect")
        if response.status_code == codes.OK:
            content = get_json_response(response)
            return content["access_token"]

    @retry(
        stop=stop_after_attempt(2),
        retry=retry_if_exception_type(BadTokenError),
        reraise=True,
    )
    @log_request_error
    def _send_request(
        self, path: str, payload: Optional[dict] = None
    ) -> httpx.Response:
        if not self._token:
            self._refresh_token()
        kwargs = {"url": path}
        if payload:
            kwargs.update(
                {
                    "json": payload,
                    "headers": {"content-type": "application/json"},
                }
            )
        get = getattr(self._http_client, "get")
        post = getattr(self._http_client, "post")
        response: httpx.Response = post(**kwargs) if payload else get(**kwargs)
        if response.status_code == codes.UNAUTHORIZED:
            self.storage.delete(self._token_storage_key)
            raise BadTokenError(response.request.url)
        if codes.is_server_error(response.status_code):
            raise ServerError("The server is failing, try later")
        if response.status_code == codes.UNPROCESSABLE_ENTITY:
            raise ValidationError(errors=response.json()["detail"])
        return response

    def send_message(
        self,
        message: str,
        sender: str,
        phone: str,
        dispatch_date: Optional[datetime.datetime] = None,
    ):
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
        """

        cp = Campaign(
            message=message,
            sender=sender,
            recipient_list=[phone],
            defer_until=dispatch_date,
        )
        self.launch_campaign(cp)
        return cp

    def launch_campaign(self, campaign: Campaign):
        """Send a request to the api to launch a new campaign from the
        `smsdrop.Campaign` instance provided

        Note that the campaign is always created even if an exception is raised,
        the instance your provide is updated with the response from the api.
        For example `campaign.id` will always be available even the campaign is
        not launched, it is always created except if there are some validation errors,
        you can use `client.retry(campaign.id)` to retry after you

        :param campaign: An instance of the class `smsdrop.Campaign`
        :raises InsufficientSmsError: If the number of sms available on your account is
        insufficient to launch the campaign
        :raises ValidationError: if the campaign data you provided is not valid
        :raises ServerError: If the server if failing for some obscure reasons
        """

        payload = campaign.as_dict(only=campaign_public_fields)
        response = self._send_request(path=CAMPAIGN_BASE_PATH, payload=payload)
        content = get_json_response(response)
        if response.status_code == codes.CREATED:
            campaign.update({"id": content["id"]})
            raise InsufficientSmsError(
                "Insufficient sms credits to launch this campaign"
            )
        campaign.update(data=content)

    def refresh_campaign(self, campaign: Campaign):
        """Refresh your campaign data from the api.

        :param campaign: An instance of the class `smsdrop.Campaign`
        :raises AssertionError: If the campaign you provided was not launched
        using `client.launch_campaign`
        :raises ServerError: If the server if failing for some obscure reasons
        """

        assert (
            Campaign.id
        ), "You can't refresh data for a campaign that hasn't yet been launched"
        refreshed_cp = self.read_campaign(id=campaign.id)
        campaign.update(refreshed_cp.as_dict())

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
                "Insufficient sms credits to launch this campaign"
            )

    def read_campaign(self, id: str) -> Optional[Campaign]:
        """Get a campaign data based on an id

        :param id: The cmapign id
        :return: An instance of `smsdrop.Campaign`
        """
        request_path = CAMPAIGN_BASE_PATH + f"{id}"
        response = self._send_request(path=request_path)
        if response.status_code == codes.NOT_FOUND:
            return None
        content = get_json_response(response)
        return Campaign.from_dict(data=content)

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
        camaigns = [Campaign.from_dict(cp) for cp in response.json()]
        return camaigns

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
