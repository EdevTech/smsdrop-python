import json
import logging

from httpx import Response, Request

logging.basicConfig(level=logging.DEBUG, format="%(message)s")


def get_json_response(response: Response) -> dict:
    default = {"responsecode": None}
    try:
        json_content = response.json()
    except json.decoder.JSONDecodeError:
        return default
    else:
        json_content = (
            json_content if json_content and isinstance(json_content, dict) else default
        )
        return json_content


def log_request(request: Request):
    json_content = json.loads(request.content) if request.method == "POST" else {}
    logging.debug(
        f"Request: {request.method} {request.url} - Waiting for response\n"
        f"Content: \n {json.dumps(json_content, indent=2, sort_keys=True)}"
    )


def log_response(response: Response):
    request = response.request
    logging.debug(
        f"Response: {request.method} {request.url} - Status {response.status_code}\n"
        f"Content : \n {json.dumps(response.json(), indent=2, sort_keys=True)}"
    )
