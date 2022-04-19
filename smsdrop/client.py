from __future__ import annotations

import datetime
import logging
from functools import cached_property, partial

import httpx
from dataclasses import dataclass
from tenacity import retry, retry_if_exception_type, stop_after_attempt
from typing import Any, List, Optional

from . import constants, errors, utils
from .constants import LOGIN_PATH
from .logger import logger as _logger
from .models import Campaign, Subscription, User
from .storages import DictStorage, Storage


@dataclass
class Client:
    """Main module class that make the requests to the smsdrop api
    :argument str email: The email address of your smsdrop account, defaults to [None]
    :argument str password: Your smsdrop account password
    :argument Optional[str] base_url: Root url of the api
    :argument Optional[BaseStorage] storage: A storage object that will be use
    to store the api token
    :argument Optional[logging.Logger] logger: A logger instance with your own config
    :raises BadCredentialsError: If the password or/and email your provided
    are incorrect
    """

    email: str
    password: str
    base_url: str = constants.BASE_URL
    storage: Storage = DictStorage()
    logger: logging.Logger = _logger

    def __del__(self):
        self._http_client.close()

    @cached_property
    def _http_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            timeout=15,
            event_hooks={
                "request": [partial(utils.log_request, logger=self.logger)],
                "response": [partial(utils.log_response, logger=self.logger)],
            },
        )

    def _login(self) -> None:
        token = self.storage.get(constants.ACCESS_TOKEN_STORAGE_KEY)
        if not token:
            response = self._http_client.post(
                url=LOGIN_PATH,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"username": self.email, "password": self.password},
            )
            if response.status_code == httpx.codes.BAD_REQUEST:
                raise errors.BadCredentialsError(
                    "Your credentials are incorrect"
                )
            assert response.status_code == httpx.codes.OK, "Error login to API"
            token = utils.get_json_response(response)["access_token"]
            assert token is not None
            self.storage.set(constants.ACCESS_TOKEN_STORAGE_KEY, token)
        self._http_client.headers["Authorization"] = f"Bearer {token}"

    def _logout(self) -> None:
        self.storage.delete(constants.ACCESS_TOKEN_STORAGE_KEY)
        self._http_client.headers["Authorization"] = ""

    @retry(
        stop=stop_after_attempt(2),
        retry=retry_if_exception_type(errors.BadTokenError),
        reraise=True,
    )
    def _send_request(
            self, path: str, payload: dict[str, Any] | None = None
    ) -> httpx.Response:
        self._login()
        kwargs: dict[str, Any] = {"url": path}
        if payload:
            kwargs["json"] = payload
            kwargs["headers"] = {"content-type": "application/json"}
        get = getattr(self._http_client, "get")
        post = getattr(self._http_client, "post")
        response: httpx.Response = post(**kwargs) if payload else get(**kwargs)
        if response.status_code == httpx.codes.UNAUTHORIZED:
            self._logout()
            raise errors.BadTokenError(response.request.url)
        if httpx.codes.is_server_error(response.status_code):
            raise errors.ServerError("The server is failing, try later")
        if response.status_code == httpx.codes.UNPROCESSABLE_ENTITY:
            raise errors.ValidationError(errors=response.json()["detail"])
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
        internally it works exactly as a campaign and create a new campaign
        :param message: The content of your message
        :param sender: The sender that will be displayed on the recipient phone
        :param phone: The recipient's phone number, Ex: +229XXXXXXXX
        :param dispatch_date: The date you want the message to be sent
        :return: An instance of the class py:class::`smsdrop.Campaign`
        :rtype: Campaign
        :raises ValidationError: if some data you provided are not valid
        :raises ServerError: If the server is failing for some obscure reasons
        :raises InsufficientSmsError: If the number of sms available on your account is
        insufficient to send the message
        """

        cp = Campaign(
            message=message,
            sender=sender,
            recipient_list=[phone],
            defer_until=dispatch_date,
        )
        self.launch(cp)
        return cp

    def launch(self, campaign: Campaign) -> None:
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
            path=constants.CAMPAIGN_BASE_PATH, payload=campaign.as_dict()
        )
        content = utils.get_json_response(response)
        if response.status_code == httpx.codes.CREATED:
            raise errors.InsufficientSmsError(
                content["id"],
                "Insufficient sms credits to launch this campaign",
            )
        campaign.update(content)

    def retry(self, campaign: Campaign) -> None:
        """Retry a campaign if it was not launch due to insufficient sms on the user
         account
        :param campaign: Your original campaign object
        :raises ServerError: If the server is failing for some obscure reasons
        """

        payload = {"id": campaign.id}
        response = self._send_request(
            path=constants.CAMPAIGN_RETRY_PATH, payload=payload
        )
        if response.status_code == httpx.codes.CREATED:
            raise errors.InsufficientSmsError(
                id, "Insufficient sms credits to launch this campaign"
            )

    def refresh(self, campaign: Campaign) -> None:
        """Get a campaign data based on an id
        :param campaign: Your campaign object
        :return: An instance of `smsdrop.CampaignIn`
        """

        request_path = constants.CAMPAIGN_BASE_PATH + f"{id}"
        response = self._send_request(path=request_path)
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        content = utils.get_json_response(response)
        campaign.update(content)

    def get_campaigns(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        """Get multiple campaigns from the api
        :param skip: starting index
        :param limit: The maximum amount of element to get
        :return:
        """
        request_path = (
                constants.CAMPAIGN_BASE_PATH + f"?skip={skip}&limit={limit}"
        )
        response = self._send_request(path=request_path)
        content = utils.get_json_response(response)
        return [Campaign.from_api_response(cp) for cp in content]

    def get_subscription(self) -> Subscription:
        """Get your subscription information
        :raises ServerError: If the server is failing for some obscure reasons
        :return: An instance of the `smsdrop.Subscription` class
        """

        response = self._send_request(path=constants.SUBSCRIPTION_PATH)
        return Subscription.from_api_response(
            utils.get_json_response(response)
        )

    def get_profile(self) -> User:
        """Get your profile information
        :raises ServerError: If the server is failing for some obscure reasons
        :return: An instance of the `smsdrop.User` class
        """

        response = self._send_request(path=constants.USER_PATH)
        return User.from_api_response(utils.get_json_response(response))
