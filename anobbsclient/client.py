from typing import Optional, OrderedDict, Dict, Any, Union, Literal, NamedTuple, Tuple, Callable
from dataclasses import dataclass, field

import time
import logging
import urllib

import requests
import requests_toolbelt

from .usercookie import UserCookie
from .options import RequestOptions, LoginPolicy, LuweiCookieFormat
from .objects import Board, Thread
from .utils import current_timestamp_ms_offset_to_utc8
from .exceptions import ShouldNotReachException, RequiresLoginException, NoPermissionException, ResourceNotExistsException


class BandwidthUsage(NamedTuple):
    uploaded: int
    downloaded: int


@dataclass
class Client:
    """
    AnoBBS 客户端

    Fields
    ------
    user_agent : str
        User Agent。

    host : str
        API服务器的主机名。

    appid : str
        appid。

    default_request_options : RequestOptions
        请求的默认设置。
    """

    user_agent: str

    host: str

    appid: Optional[str] = None

    default_request_options: RequestOptions = field(default_factory=dict)

    __session: requests.Session = field(
        init=False,
        default_factory=requests.Session,
    )

    def get_board_page(self, board_id: int, page: int, options: RequestOptions = {}) -> Tuple[Board, BandwidthUsage]:
        """
        获取指定串的指定页。

        board_id : int
            版块 ID。

        page : int
            页数。

        options : RequestOptions
            请求选项。
        """

        if page > self.get_board_gatekeeper_page_number(options):
            raise NoPermissionException()

        with_login = self.get_login_policy(
            options) in ["enforce", "when_has_cookie"]
        if with_login and not self.has_cookie(options):
            raise RequiresLoginException()

        logging.debug(f"将获取版块：{board_id} 第 {page} 页，已登陆：{with_login}")

        def fn(): return self.__get_board_page(
            board_id, page=page, options=options, with_login=with_login)

        (board_page, bandwidth_usage) = _try_request(
            fn, f"获取版块 {id} 第 {page} 页", self.get_max_attempts(options))

        return board_page, bandwidth_usage

    def __get_board_page(self, board_id: int, page: int, options: RequestOptions = {}, with_login: bool = False) -> Tuple[Board, BandwidthUsage]:

        self.__setup_headers(options=options, with_login=with_login)

        queries = OrderedDict()
        queries["id"] = board_id
        queries["page"] = page
        if self.appid != None:
            queries["appid"] = self.appid
        queries["__t"] = current_timestamp_ms_offset_to_utc8()
        url = f"https://{self.host}/Api/showf?" + \
            urllib.parse.urlencode(queries)
        resp = self.__session.get(url)
        resp.raise_for_status()

        threads = resp.json(object_pairs_hook=OrderedDict)
        return list(map(lambda thread: Thread(thread), threads)), _calculate_bandwidth_usage(resp)

    def get_thread_page(self, id: int, page: int, options: RequestOptions = {}, for_analysis: bool = False) -> Tuple[Thread, BandwidthUsage]:
        """
        获取指定串的指定页。

        id : int
            串号。

        page : int
            页数。

        options : RequestOptions
            请求选项。

        for_analysis : bool
            如果为真，将会过滤掉与分析无关的内容，以方便分析。
        """

        with_login = self.thread_page_requires_login(
            page=page, options=options)
        if with_login and not self.has_cookie(options):
            raise RequiresLoginException()

        logging.debug(f"将获取串：{id} 第 {page} 页，已登陆：{with_login}")

        def fn(): return self.__get_thread_page(
            id, page=page, options=options, with_login=with_login)

        (thread_page, bandwidth_usage) = _try_request(
            fn, f"获取串 {id} 第 {page} 页", self.get_max_attempts(options))

        if for_analysis:
            thread_page.replies = list(filter(
                lambda post: post.user_id != "芦苇", thread_page.replies))

        return thread_page, bandwidth_usage

    def __get_thread_page(self, id: int, page: int, options: RequestOptions, with_login: bool = False) -> Tuple[Thread, BandwidthUsage]:

        self.__setup_headers(options=options, with_login=with_login)

        queries = OrderedDict()
        queries["page"] = page
        if self.appid != None:
            queries["appid"] = self.appid
        queries["__t"] = current_timestamp_ms_offset_to_utc8()
        url = f"https://{self.host}/Api/thread/id/{id}?" + \
            urllib.parse.urlencode(queries)
        resp = self.__session.get(url)
        resp.raise_for_status()
        if resp.json() == '该主题不存在':
            raise ResourceNotExistsException()

        return Thread(resp.json(object_pairs_hook=OrderedDict)), _calculate_bandwidth_usage(resp)

    def __setup_headers(self, options: RequestOptions, with_login: bool = False):

        if with_login:
            user_cookie = self.get_user_cookie(options)
            assert(user_cookie != None)
            cookie = requests.cookies.create_cookie(
                name="userhash", value=user_cookie.userhash, domain=self.host,
            )
            self.__session.cookies.set_cookie(cookie)
        else:
            requests.cookies.remove_cookie_by_name(
                self.__session.cookies, "userhash", domain=self.host)

        luwei_cookie_format = self.get_uses_luwei_cookie_format(options)
        if isinstance(luwei_cookie_format, dict):
            # 芦苇岛搞错了？
            for (k, v) in {
                "expires": luwei_cookie_format["expires"],
                "domains": self.host,
                "path": "/",
            }.items():
                if k not in self.__session.cookies.keys():
                    cookie = requests.cookies.create_cookie(
                        name=k, value=v, domain=self.host,
                    )
                    self.__session.cookies.set_cookie(cookie)

        self.__session.headers.update({
            "Accept": "application/json",
            "User-Agent": self.user_agent,
            "Accept-Language": "en-us",
            "Accept-Encoding": "gzip, deflate, br",
        })

    def thread_page_requires_login(self, page: int, options: RequestOptions = {}) -> bool:
        """
        Returns
        -------
        是否需要使用饼干请求服务器。
        """

        login_policy = self.get_login_policy(options)
        has_cookie = self.has_cookie(options)
        gate_keeper_page_number = self.get_thread_gatekeeper_page_number(
            options)

        if login_policy == "enforce":
            return True

        if login_policy == "when_has_cookie":
            return has_cookie or page > gate_keeper_page_number
        elif login_policy in ("always_no", "when_required"):
            return page > gate_keeper_page_number

        raise ShouldNotReachException()

    def has_cookie(self, options: RequestOptions = {}) -> bool:
        return self.get_user_cookie(options) != None

    def __get_option_value(self, external_options: RequestOptions, key: str, default: Any = None) -> Any:
        return (
            external_options.get(key, None)
            or self.default_request_options.get(key, default)
        )

    def get_user_cookie(self, options: RequestOptions = {}) -> UserCookie:
        if self.get_login_policy(options) == "always_no":
            return None
        return self.__get_option_value(options, "user_cookie")

    def get_login_policy(self, options: RequestOptions = {}) -> LoginPolicy:
        return self.__get_option_value(options, "login_policy", "when_required")

    def get_thread_gatekeeper_page_number(self, options: RequestOptions = {}) -> int:
        return self.__get_option_value(options, "thread_gatekeeper_page_number", 100)

    def get_board_gatekeeper_page_number(self, options: RequestOptions = {}) -> int:
        return self.__get_option_value(options, "board_gatekeeper_page_number", 100)

    def get_uses_luwei_cookie_format(self, options: RequestOptions = {}) -> Union[Literal[False], LuweiCookieFormat]:
        return self.__get_option_value(options, "uses_luwei_cookie_format", False)

    def get_max_attempts(self, options: RequestOptions = {}) -> int:
        return self.__get_option_value(options, "max_attempts", 3)


def _try_request(fn: Callable[[], Any], description: str, max_attempts: int) -> Any:
    for i in range(1, max_attempts + 1):
        can_retry = False
        try:
            return fn()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as _e:
            # 对连接、超时相关的问题重试
            can_retry = True
            e = _e
        except requests.exceptions.HTTPError as _e:
            if _e.response != None and _e.response.status_code == 404:
                e = ResourceNotExistsException()
            else:
                e = _e
        except Exception as _e:
            e = _e

        if can_retry and i < max_attempts:
            logging.warning(
                f'执行「{description}」失败: {e}. 尝试: {i}/{max_attempts}')
        else:
            msg = f'无法执行「{description}」: {e}'
            if can_retry:
                msg += '. 已经失败 {max_attempts} 次, 超过最大尝试次数, 放弃'
            else:
                msg += '. 将不重试, 放弃'
            if isinstance(e, requests.exceptions.RequestException):
                msg += ". dump: " + \
                    requests_toolbelt.utils.dump.dump_all(
                        e.response).decode('utf-8')
            logging.error(msg)

            raise e


def _calculate_bandwidth_usage(resp: requests.Response) -> BandwidthUsage:
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

    return BandwidthUsage(request_size, response_size)


def __calculate_header_size(headers) -> int:
    return sum(len(key) + len(value) + 4 for key, value in headers.items()) + 2
