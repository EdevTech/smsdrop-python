import json
import logging

import httpx
from enum import Enum, IntEnum
from httpx import Request, Response

from .constants import LOGIN_PATH
from .errors import BadCredentialsError


class MessageType(IntEnum):
    PLAIN_TEXT = 0
    FLASH_MESSAGE = 1
    UNICODE = 2


class ShipmentState(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    SCHEDULED = "SCHEDULED"


def get_access_token(
    email: str, password: str, http_client: httpx.Client
) -> str:
    response = http_client.post(
        url=LOGIN_PATH,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": email, "password": password},
    )
    if response.status_code == httpx.codes.BAD_REQUEST:
        raise BadCredentialsError("Your credentials are incorrect")
    assert response.status_code == httpx.codes.OK
    token = get_json_response(response)["access_token"]
    return token


def log_request(request: Request, logger: logging.Logger) -> None:
    json_content = (
        json.loads(request.content) if request.method == "POST" else {}
    )
    logger.debug(
        f"Request: {request.method} {request.url} - Waiting for response\n"
        f"Content: \n {json.dumps(json_content, indent=2, sort_keys=True)}"
    )


def log_response(response: Response, logger: logging.Logger) -> None:
    request = response.request
    logger.debug(
        f"Response: {request.method} {request.url} - Status {response.status_code}\n"
        f"Content : \n {json.dumps(response.json(), indent=2, sort_keys=True)}"
    )


def get_json_response(response: Response) -> dict:
    try:
        data = response.json()
    except json.decoder.JSONDecodeError:
        data = {}
    return data
