from typing import Tuple

import time

import requests


def current_timestamp_ms_offset_to_utc8() -> int:
    return int((time.time() + 60*60*8)*1000)


def calculate_bandwidth_usage(resp: requests.Response) -> Tuple[int, int]:
    """
    …

    See: https://stackoverflow.com/a/33217154
    """

    request_line_size = len(resp.request.method) + \
        len(resp.request.path_url) + 12
    request_size = request_line_size + \
        __calculate_header_size(resp.request.headers) + \
        int(resp.request.headers.get("content-length", 0)
            )  # 没有 body 就不会生成 Content-Length?

    response_line_size = len(resp.reason) + 15
    response_size = response_line_size + \
        __calculate_header_size(resp.headers) + \
        int(resp.headers["content-length"])

    return (request_size, response_size)


def __calculate_header_size(headers) -> int:
    return sum(len(key) + len(value) + 4 for key, value in headers.items()) + 2
