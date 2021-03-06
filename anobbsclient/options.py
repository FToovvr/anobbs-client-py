from typing import Optional, TypedDict, Union, Literal

from .usercookie import UserCookie

LoginPolicy = Union[
    Literal["enforce"],
    Literal["when_has_cookie"],
    Literal["when_required"],
    Literal["always_no"],
]
"""
是否向服务端告知登录的策略。

Cases
-----
"enforce"
    无视其他条件，必须设置饼干，并使用该饼干请求服务器。
    如果没有设置用户饼干，将抛出 :exc:`RequiresLoginException`。

"when_has_cookie"
    只要设置了用户饼干，就使用该饼干请求服务器。

"when_required"
    只有在需要时（如获取串的 100 页之后的页面）才使用设置的饼干，否则会以无饼干状态请求服务器。

"always_no"
    即使设置了饼干，也会以无饼干状态请求服务器。

"""


class LuweiCookieFormat(TypedDict, total=False):
    expires: str


class RequestOptions(TypedDict, total=False):
    """
    客户端相关的请求设置。
    """

    user_cookie: UserCookie
    """
    使用的用户饼干，默认为 ``None``。

    若为 ``None``, 则不使用饼干。
    """

    login_policy: LoginPolicy
    """饼干登录的策略。"""

    board_gatekeeper_page_number: int
    """版块「卡99」的页数，默认为 ``100``。"""
    thread_gatekeeper_page_number: int
    """
    串「卡99」的页数，默认为 ``100``。

    如果操作获取串的页数超过该值，但并无可用饼干，会抛出 :exc:`RequiresLoginException`。
    """

    uses_luwei_cookie_format: Union[Literal[False], LuweiCookieFormat]
    """
    是否使用芦苇客户端的格式填充 HTTP ``Cookie`` Header，默认为 ``False``。

    芦苇客户端填充的 ``Cookie`` Header 包含不必要的 ``expires``, ``domains`` 及 ``path`` 字段，大概率是填错了。  
    为了保持与芦苇客户端一致，可以开启此项。
    """

    max_attempts: int
    """最多由于网络连接问题进行尝试的次数，默认为 ``5``。"""
