from typing import Optional, OrderedDict, Dict, Any, Union, Literal
from dataclasses import dataclass, field

import time
import logging
import urllib

import requests

from .usercookie import UserCookie
from .options import RequestOptions, LoginPolicy, LuweiCookieFormat
from .response import ThreadResponse
from .utils import current_timestamp_ms_offset_to_utc8, calculate_bandwidth_usage
from .exceptions import ShouldNotReachException, RequiresLoginException


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

    def get_thread(self, id: int, page: int, options: RequestOptions = {}, for_analysis: bool = False) -> ThreadResponse:
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

        with_login = self.__check_login(page=page, options=options)
        max_attempts = self.__get_max_attempts(options)
        logging.debug(f"将获取串：{id} 第 {page} 页，已登陆：{with_login}")

        for i in range(1, max_attempts + 1):
            try:
                thread = self.__get_thread(
                    id, page=page, options=options, with_login=with_login)
                if for_analysis:
                    thread.replies = list(filter(
                        lambda post: post["userid"] != "芦苇", thread.replies))
            except (requests.exceptions.RequestException, ValueError) as e:
                if i < max_attempts:
                    logging.warning(
                        f'获取串 {id} 第 {page} 页失败: {e}. 尝试: {i}/{max_attempts}')
                else:
                    logging.error(
                        f'无法获取串 {id} 第 {page} 页: {e}. 已经失败 {max_attempts} 次. 放弃')
                    raise e
            else:
                return thread

    def __get_thread(self, id: int, page: int, options: RequestOptions, with_login: bool = False) -> ThreadResponse:

        self.__setup_headers(options=options, with_login=with_login)

        queries = OrderedDict()
        queries["page"] = page
        if self.appid != None:
            queries["appid"] = self.appid
        queries["__t"] = current_timestamp_ms_offset_to_utc8()
        url = f"https://{self.host}/Api/thread/id/{id}?" + \
            urllib.parse.urlencode(queries)
        resp = self.__session.get(url)

        return ThreadResponse(
            body=resp.json(object_pairs_hook=OrderedDict),
            bandwidth_usage=calculate_bandwidth_usage(resp),
        )

    def __setup_headers(self, options: RequestOptions, with_login: bool = False):

        if with_login:
            user_cookie = self.__get_user_cookie(options)
            assert(user_cookie != None)
            cookie = requests.cookies.create_cookie(
                name="userhash", value=user_cookie.userhash, domain=self.host,
            )
            self.__session.cookies.set_cookie(cookie)
        else:
            requests.cookies.remove_cookie_by_name(
                self.__session.cookies, "userhash", domain=self.host)

        luwei_cookie_format = self.__get_uses_luwei_cookie_format(options)
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

    def __check_login(self, page: int, options: RequestOptions = {}) -> bool:
        """
        Returns
        -------
        是否需要使用饼干请求服务器。
        """

        login_policy = self.__get_login_policy(options)
        has_cookie = self.has_cookie(options)
        gate_keeper_page_number = self.__get_gatekeeper_page_number(options)

        if login_policy == "enforce":
            if not has_cookie:
                raise RequiresLoginException()
            return True

        if ((not has_cookie or login_policy == "always_no")
                and page > gate_keeper_page_number):
            raise RequiresLoginException()

        if login_policy == "when_has_cookie":
            return has_cookie
        elif login_policy == "always_no":
            return False
        elif login_policy == "when_required":
            return page > gate_keeper_page_number

        raise ShouldNotReachException()

    def has_cookie(self, options: RequestOptions = {}) -> bool:
        return self.__get_user_cookie(options) != None

    def __get_user_cookie(self, options: RequestOptions = {}) -> UserCookie:
        return (
            options.get("user_cookie", None)
            or self.default_request_options.get("user_cookie", None)
        )

    def __get_login_policy(self, options: RequestOptions = {}) -> LoginPolicy:
        return (
            options.get("login_policy", None)
            or self.default_request_options.get("login_policy", "when_required")
        )

    def __get_gatekeeper_page_number(self, options: RequestOptions = {}) -> int:
        return (
            options.get("gatekeeper_page_number", None)
            or self.default_request_options.get("gatekeeper_page_number", 99)
        )

    def __get_uses_luwei_cookie_format(self, options: RequestOptions = {}) -> Union[Literal[False], LuweiCookieFormat]:
        return (
            options.get("uses_luwei_cookie_format", None)
            or self.default_request_options.get("uses_luwei_cookie_format", False)
        )

    def __get_max_attempts(self, options: RequestOptions = {}) -> int:
        return (
            options.get("max_attempts", None)
            or self.default_request_options.get("max_attempts", 3)
        )
