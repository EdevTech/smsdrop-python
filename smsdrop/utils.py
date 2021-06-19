import csv
import os

from typing import Generator, List, Union

csv_headers = ["phone", "phones", "phone_number", "phone_numbers", "tel"]


def split_str_content(content: str) -> Generator:
    s = csv.Sniffer()
    sep = s.sniff(content).delimiter
    sepsize = len(sep)
    start = 0
    while True:
        idx = content.find(sep, start)
        if idx == -1:
            yield content[start:]
            return
        yield content[start:idx]
        start = idx + sepsize


def make_recipient_list(data: Union[List[str], str]) -> Generator:
    if isinstance(data, list):
        for d in data:
            yield str(d)
    assert isinstance(data, str), "data cannot be processed"
    try:
        file = open(data, "r")
    except FileNotFoundError:
        for d in split_str_content(content=data):
            if d:
                yield d
    else:
        _, extension = os.path.splitext(data)
        if extension == ".csv":
            csv_content = csv.DictReader(file)
            phone_headers = list(
                filter(
                    bool,
                    map(
                        lambda h: h if h in csv_headers else None,
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
        file.close()
