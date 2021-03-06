from typing import NamedTuple, Callable, Any, OrderedDict

import logging
import urllib3
import json
import io

import requests
import requests_toolbelt

from .exceptions import ResourceNotExistsException


class BandwidthUsage(NamedTuple):
    """
    用于封装与客户端操作产生的流量有关的信息。
    """
    uploaded: int
    """上传字节数。"""
    downloaded: int
    """下载字节数。"""


def try_request(fn: Callable[[], Any], description: str, max_attempts: int) -> Any:
    """
    尝试进行请求。

    Parameters
    ----------
    fn : Callable[[], Any]
        请求本身。
    description : str
        对于请求的可读描述。
    max_attempts : int
        最多可尝试的次数。
    """

    for i in range(1, max_attempts + 1):
        try:
            return fn()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            # 对于连接、超时等可以重试的问题进行重试
            msg = f'执行「{description}」失败：{e}。'
            if i < max_attempts:
                logging.warning(msg + f'将会重试。尝试次数：{i}/{max_attempts}')
            else:
                logging.error(msg + f'已经失败 {max_attempts} 次，超过最大尝试次数，放弃')
        except Exception as e:
            msg = f'执行「{description}」失败：{e}。将不重试，放弃'
            if isinstance(e, requests.exceptions.HTTPError):
                # pylint: disable=maybe-no-member
                if e.response != None and e.response.status_code == 404:
                    # 如果能够确认是 404，那就抛出 :class:`ResourceNotExistsException`
                    e = ResourceNotExistsException()
            elif isinstance(e, requests.exceptions.RequestException):
                # pylint: disable=maybe-no-member
                dump = requests_toolbelt.utils.dump.dump_all(e.response)
                msg += "。dump：" + dump.decode('utf-8')

            logging.error(msg)

            raise e


def get_json(session: requests.Session, url: str):
    # TODO: 不要 hardcode timeout
    with session.get(url, stream=True, timeout=20) as resp:
        resp.raise_for_status()
        raw_content = resp.raw.read()

    bandwidth_usage = BandwidthUsage(
        __calculate_request_size(resp),
        __calculate_response_size(resp, raw_content),
    )

    headers = {
        'Content-Encoding': resp.headers.get('content-encoding', '')
    }

    with io.BytesIO(raw_content) as f:
        fake_resp = urllib3.response.HTTPResponse(
            body=f,
            headers=headers,
        )
        decoded_content = fake_resp.data
        obj = json.loads(decoded_content, object_pairs_hook=OrderedDict)

    return obj, bandwidth_usage


def __calculate_request_size(resp: requests.Response) -> BandwidthUsage:
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

    return request_size


def __calculate_response_size(resp: requests.Response, raw_content):

    response_line_size = len(resp.reason) + 15
    response_size = response_line_size + \
        __calculate_header_size(resp.headers) + \
        len(raw_content)

    return response_size


def __calculate_header_size(headers) -> int:
    return sum(len(key) + len(value) + 4 for key, value in headers.items()) + 2
