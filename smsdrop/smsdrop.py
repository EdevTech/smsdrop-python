import datetime
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, List

import httpx
import redis
from httpx import codes

from .constants import (
    BASE_URL,
    LOGIN_PATH,
    USER_PATH,
    SUBSCRIPTION_PATH,
    CAMPAIGN_BASE_PATH,
    CAMPAIGN_RETRY_PATH,
)
from .exceptions import (
    ServerError,
    BadCredentialsError,
    InsufficientSmsError,
    ValidationError,
)
from .helpers import log_request, log_response, get_json_response
from .models import (
    Campaign,
    User,
    Subscription,
    MessageType,
    campaign_public_fields,
    Redis,
)

logger = logging.getLogger(__name__)


@dataclass
class Client:
    email: str
    password: str
    active_logging: bool = False
    storage: Redis = Redis()
    _collected_responses: List[httpx.Response] = field(default_factory=list)

    def __post_init__(self):
        self._storage_client = redis.Redis(
            **asdict(self.storage), decode_responses=True
        )
        self._set_token(new_token=self._login())
        self._http_client = httpx.Client(
            base_url=BASE_URL, headers={"Authorization": f"Bearer {self._token}"}
        )
        if self.active_logging:
            self._http_client.event_hooks = {
                "request": [log_request],
                "response": [log_response, self._update_responses],
            }

    def _update_responses(self, r: httpx.Response):
        self._collected_responses.append(r)

    @property
    def _token_storage_key(self):
        return f"bearer_token_{self.password}"

    @property
    def _token(self):
        return self._storage_client.get(self._token_storage_key)

    def _set_token(self, new_token):
        self._storage_client.set(self._token_storage_key, new_token)

    def _login(self) -> str:
        response = httpx.post(
            url=BASE_URL + LOGIN_PATH,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"username": self.email, "password": self.password},
        )
        content = get_json_response(response)
        if response.status_code == codes.OK:
            return content["access_token"]
        elif response.status_code == codes.BAD_REQUEST:
            raise BadCredentialsError("Your credentials are incorrect")
        elif codes.is_server_error(response.status_code):
            raise ServerError("The server is failing, try later")
        else:
            logger.info(response.text)

    def _token_has_expired(self) -> bool:
        try:
            response = httpx.get(
                url=BASE_URL + USER_PATH,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.RequestError as e:
            logger.error(e)
        else:
            return response.status_code == codes.UNAUTHORIZED

    def _send_request(
        self, path: str, payload: Optional[dict] = None
    ) -> httpx.Response:
        if self._token_has_expired():
            self._set_token(new_token=self._login())
        try:
            response = (
                self._http_client.post(
                    url=path, json=payload, headers={"content-type": "application/json"}
                )
                if payload
                else self._http_client.get(url=path)
            )
        except httpx.RequestError as e:
            logger.error(e)
        else:
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
        response = self._send_request(path=CAMPAIGN_BASE_PATH, payload=payload)
        content = get_json_response(response)
        if response.status_code == codes.CREATED:
            raise InsufficientSmsError(
                "Insufficient sms credits to launch this campaign"
            )
        return Campaign.from_response(content)

    def launch_campaign(self, campaign: Campaign):
        payload = campaign.as_dict(only=campaign_public_fields)
        response = self._send_request(path=CAMPAIGN_BASE_PATH, payload=payload)
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
        response = self._send_request(path=SUBSCRIPTION_PATH)
        content = get_json_response(response)
        return Subscription(id=content["id"], nbr_sms=content["nbr_sms"])

    def read_me(self) -> User:
        response = self._send_request(path=USER_PATH)
        content = get_json_response(response)
        return User(
            email=content["email"], id=content["id"], is_active=content["is_active"]
        )
