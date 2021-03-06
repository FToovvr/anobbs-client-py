from typing import Optional, Dict, Any, Union, Literal, NamedTuple
from dataclasses import dataclass, field

import requests
from http.cookiejar import CookieJar

from .options import RequestOptions, UserCookie, LoginPolicy, LuweiCookieFormat
from .exceptions import RequiresLoginException


@dataclass
class BaseClient:
    """
    客户端基类。

    不实现实际的请求功能。
    """

    user_agent: str
    """发送请求时要使用的 User Agent。"""

    host: str
    """要请求的 API 服务器的主机名。"""

    appid: Optional[str] = None
    """appid。"""

    default_request_options: RequestOptions = field(default_factory=dict)
    """默认的发送请求时的相关设置。"""

    cookiejar_store: Dict[str, CookieJar] = field(default_factory=dict)
    """
    每个饼干配有独立的 :class:`CookieJar`。
    键为 ``userhash``。
    
    这是因为服务器响应可能会根据饼干要求添加不同的新 cookies，
    这么做可以防止不同饼干间新 cookies 的混淆。

    FIXME: 线程不安全。
    """

    def _make_session(self, options: RequestOptions, needs_login: bool = False) -> requests.Session:
        """
        根据请求设置创建一个新的会话。

        Parameters
        ----------
        options : RequestOptions
            请求设置。
        needs_login : bool
            是否需要携带饼干。

        Returns
        -------
        新的会话。
        """

        session = requests.Session()
        self.__setup_headers(session, options=options,
                             needs_login=needs_login)
        return session

    def __setup_headers(self, session, options: RequestOptions, needs_login: bool = False):
        """
        根据请求选项设置好会话的 headers。

        Parameters
        ----------
        session : requests.Session
            会话。
        options : RequestOptions
            请求设置。
        needs_login : bool
            是否需要登录。
        """

        if needs_login:
            # 若需要登录，配置 cookies

            user_cookie = self.get_user_cookie(options)
            if user_cookie is None:
                raise RequiresLoginException()

            if user_cookie.userhash in self.cookiejar_store:
                cookiejar = self.cookiejar_store[user_cookie.userhash]
            else:
                cookiejar: CookieJar = requests.cookies.cookiejar_from_dict({})
                cookie = requests.cookies.create_cookie(
                    name="userhash", value=user_cookie.userhash, domain=self.host,
                )
                cookiejar.set_cookie(cookie)
                self.cookiejar_store[user_cookie.userhash] = cookiejar
            session.cookies = cookiejar

        luwei_cookie_format = self.get_uses_luwei_cookie_format(options)
        if isinstance(luwei_cookie_format, dict):
            # 芦苇岛似乎搞错了要放置的 cookies。
            # 如有要求，便会照着芦苇岛将错就错
            for (k, v) in {
                "expires": luwei_cookie_format["expires"],
                "domains": self.host,
                "path": "/",
            }.items():
                if k not in session.cookies.keys():
                    cookie = requests.cookies.create_cookie(
                        name=k, value=v, domain=self.host,
                    )
                    session.cookies.set_cookie(cookie)

        session.headers.update({
            "Accept": "application/json",
            "User-Agent": self.user_agent,
            "Accept-Language": "en-us",
            "Accept-Encoding": "gzip, deflate, br",
        })

    def _get_option_value(self, external_options: RequestOptions, key: str, default: Any = None) -> Any:
        """
        获取请求设置中指定键的值。

        如果外部请求设置中有值，优先返回来自外部的值；
        其次可能的话返回内部默认请求设置中的值；
        否则返回指定的默认值。

        Parameters
        ----------
        external_options : RequestOptions
            外部请求的设置。
        key : str
            要获取其值的键。
        default : Any
            内外都没有值时的 fallback。

        Returns
        -------
        要获取的值。
        """
        return (
            external_options.get(key, None)
            or self.default_request_options.get(key, default)
        )

    def get_user_cookie(self, options: RequestOptions = {}) -> UserCookie:
        """获取用户饼干。"""
        if self.get_login_policy(options) == "always_no":
            return None
        return self._get_option_value(options, "user_cookie")

    def has_cookie(self, options: RequestOptions = {}) -> bool:
        """返回是否设置了用户饼干。"""
        return self.get_user_cookie(options) != None

    def get_login_policy(self, options: RequestOptions = {}) -> LoginPolicy:
        """获取登录策略，见 :class:`LoginPolicy`。"""
        return self._get_option_value(options, "login_policy", "when_required")

    def get_uses_luwei_cookie_format(self, options: RequestOptions = {}) -> Union[Literal[False], LuweiCookieFormat]:
        """获取是否要照着芦苇岛岛规则设置请求的 cookies。"""
        return self._get_option_value(options, "uses_luwei_cookie_format", False)

    def get_max_attempts(self, options: RequestOptions = {}) -> int:
        """
        获取最大尝试次数。

        默认为5。
        """
        return self._get_option_value(options, "max_attempts", 5)
