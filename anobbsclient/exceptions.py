from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ShouldNotReachException(Exception):
    """
    到达了不应该到达的代码时会抛出的异常。
    """
    pass


@dataclass
class ClientException(Exception):
    """
    与客户端有关的异常。
    """

    message: str
    """记载可读的异常信息。"""


@dataclass
class NoPermissionException(ClientException):
    """
    进行没有权限的操作时会抛出的异常。
    """

    def __init__(self, extra_message: Optional[str] = None):
        message = "无操作权限"
        if extra_message != None:
            message += "：" + extra_message
        super(NoPermissionException, self).__init__(
            message=message,
        )


@dataclass
class RequiresLoginException(NoPermissionException):
    """
    需要登录而未登录时会抛出的异常。
    """

    def __init__(self):
        super(RequiresLoginException, self).__init__(
            extra_message="操作需要有效饼干，但客户端并未设置饼干",
        )


@dataclass
class GatekeptException(NoPermissionException):
    """
    发现出现「卡99」现象时会抛出的异常。
    """

    context: str
    current_page_number: Optional[int]
    gatekeeper_post_id: Optional[int] = field(default=None)
    """
    对于版块，此处为空。

    TODO: 依版块/串细分
    """

    def __init__(self, context: str, current_page_number: int, gatekeeper_post_id: int):
        super(GatekeptException, self).__init__(
            extra_message="出现「卡99现象」",
        )

        self.context = context
        self.current_page_number = current_page_number
        self.gatekeeper_post_id = gatekeeper_post_id


@dataclass
class ResourceNotExistsException(ClientException):
    def __init__(self):
        super(ResourceNotExistsException, self).__init__(
            message="目标资源不存在",
        )


@dataclass
class UnreachableLowerBoundPostIDException(ClientException):
    """
    在从后向前遍历时串，发生「到达串的头部时还没有到达下界」这一诡异现象时抛出的异常？
    """

    lower_bound_post_id: int

    def __init__(self, lower_bound_post_id: int):
        super(UnreachableLowerBoundPostIDException, self).__init__(
            message="串号下界比串首串号小",
        )

        self.lower_bound_post_id = lower_bound_post_id


@dataclass
class UnexpectedLowerBoundPostIDException(ClientException):

    current_page_number: int
    expected_lower_bound_page_number: int
    lower_bound_post_id: int

    def __init__(self, current_page_number: int, expected_lower_bound_page_number: int, lower_bound_post_id: int):
        super(UnexpectedLowerBoundPostIDException, self).__init__(
            message="非预期地提前遇到了串号下界",
        )

        self.current_page_number = current_page_number
        self.expected_lower_bound_page_number = expected_lower_bound_page_number
        self.lower_bound_post_id = lower_bound_post_id
