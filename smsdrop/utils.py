import csv
import json
import logging
import os

import httpx
from enum import Enum, IntEnum
from httpx import Request, Response
from typing import Generator, cast

from .constants import ACCESS_TOKEN_STORAGE_KEY, LOGIN_PATH
from .errors import BadCredentialsError
from .storages import Storage

ACCEPTED_CSV_HEADERS = [
    "phone",
    "phones",
    "phone_number",
    "phone_numbers",
    "tel",
]


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


def split_str_content(content: str) -> Generator:
    s = csv.Sniffer()
    sep = cast(str, s.sniff(content).delimiter)
    sep_size = len(sep)
    start = 0
    while True:
        idx = content.find(sep, start)
        if idx == -1:
            yield content[start:]
            return
        yield content[start:idx]
        start = idx + sep_size


def parse_file_for_phones(filepath: str) -> Generator[str, None, None]:
    with open(filepath) as file:
        _, extension = os.path.splitext(filepath)
        if extension != ".csv":
            csv_content = csv.DictReader(file)
            phone_headers = list(
                filter(
                    bool,
                    map(
                        lambda h: h if h in ACCEPTED_CSV_HEADERS else None,
                        csv_content.fieldnames,
                    ),
                )
            )
            if phone_headers:
                phone_header = phone_headers[0]
                for d in csv_content:
                    yield d[phone_header]
        else:
            for line in file.read().splitlines():
                for d in split_str_content(line):
                    if d:
                        yield d


def get_access_token(
    storage: Storage, email: str, password: str, http_client: httpx.Client
) -> str:
    token = storage.get(ACCESS_TOKEN_STORAGE_KEY)
    if token:
        return token
    response = http_client.post(
        url=LOGIN_PATH,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": email, "password": password},
    )
    if response.status_code == httpx.codes.BAD_REQUEST:
        raise BadCredentialsError("Your credentials are incorrect")
    assert response.status_code == httpx.codes.OK
    token = get_json_response(response)["access_token"]
    storage.set(token)
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


def cast_message_type(content: dict) -> dict:
    if "message_type" in content:
        content["message_type"] = MessageType(content["message_type"])
    return content


def get_json_response(response: Response) -> dict:
    default = {"responsecode": None}
    try:
        json_content = response.json()
    except json.decoder.JSONDecodeError:
        return default
    else:
        json_content = (
            json_content
            if json_content and isinstance(json_content, dict)
            else default
        )
        return json_content
