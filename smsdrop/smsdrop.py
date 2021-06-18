import datetime
import json
import logging
from dataclasses import dataclass
from typing import Optional, List

import httpx
from httpx import codes, Request, Response
from tenacity import retry, stop_after_attempt, retry_if_exception_type

from .constants import (
    BASE_URL,
    LOGIN_PATH,
    USER_PATH,
    SUBSCRIPTION_PATH,
    CAMPAIGN_BASE_PATH,
    CAMPAIGN_RETRY_PATH,
    TOKEN_LIFETIME,
)
from .exceptions import (
    ServerError,
    BadCredentialsError,
    InsufficientSmsError,
    ValidationError,
    BadTokenError,
)
from .helpers import get_json_response, log_request_error
from .models import (
    Campaign,
    User,
    Subscription,
    MessageType,
    campaign_public_fields,
)
from .storages import BaseStorage, SimpleDict

_logger = logging.getLogger(__name__)


def log_request(request: Request):
    json_content = json.loads(request.content) if request.method == "POST" else {}
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
        # The api set it token to expire after 1 hour
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

    def send_sms(
        self,
        message: str,
        sender: str,
        phone: str,
        dispatch_date: Optional[datetime.datetime] = None,
    ):
        payload = {
            "message": message,
            "message_type": MessageType.PLAIN_TEXT,
            "sender": sender,
            "recipient_list": [phone],
        }
        if dispatch_date:
            payload["dispatch_date"] = dispatch_date
        response = self._send_request(path=CAMPAIGN_BASE_PATH + "/", payload=payload)
        content = get_json_response(response)
        if response.status_code == codes.CREATED:
            raise InsufficientSmsError(
                "Insufficient sms credits to launch this campaign"
            )
        return Campaign.from_response(content)

    def launch_campaign(self, campaign: Campaign):
        payload = campaign.as_dict(only=campaign_public_fields)
        response = self._send_request(path=CAMPAIGN_BASE_PATH + "/", payload=payload)
        content = get_json_response(response)
        if response.status_code == codes.CREATED:
            raise InsufficientSmsError(
                "Insufficient sms credits to launch this campaign"
            )
        campaign.update(data=content)

    def refresh_campaign(self, campaign: Campaign):
        assert (
            Campaign.id
        ), "You can't refresh data for a campaign that hasn't yet been launched"
        refreshed_cp = self.read_campaign(id=campaign.id)
        campaign.update(refreshed_cp.as_dict())

    def retry_campaign(self, id: str):
        payload = {"id": id}
        response = self._send_request(path=CAMPAIGN_RETRY_PATH, payload=payload)
        if response.status_code == codes.CREATED:
            raise InsufficientSmsError(
                "Insufficient sms credits to launch this campaign"
            )

    def read_campaign(self, id: str) -> Optional[Campaign]:
        request_path = CAMPAIGN_BASE_PATH + f"/{id}"
        response = self._send_request(path=request_path)
        if response.status_code == codes.NOT_FOUND:
            return None
        content = get_json_response(response)
        return Campaign.from_response(data=content)

    def read_campaigns(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        request_path = CAMPAIGN_BASE_PATH + f"/?skip={skip}&limit={limit}"
        response = self._send_request(path=request_path)
        camaigns = [Campaign.from_response(cp) for cp in response.json()]
        return camaigns

    def read_subscription(self) -> Subscription:
        response = self._send_request(path=SUBSCRIPTION_PATH + "/")
        content = get_json_response(response)
        return Subscription(id=content["id"], nbr_sms=content["nbr_sms"])

    def read_me(self) -> User:
        response = self._send_request(path=USER_PATH)
        content = get_json_response(response)
        return User(
            email=content["email"], id=content["id"], is_active=content["is_active"]
        )
