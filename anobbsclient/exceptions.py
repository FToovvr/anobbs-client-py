from typing import Optional
from dataclasses import dataclass


@dataclass
class ShouldNotReachException(Exception):
    pass


@dataclass
class ClientException(Exception):

    message: str


@dataclass
class NoPermissionException(ClientException):

    def __init__(self, extra_message: Optional[str] = None):
        message = "无操作权限"
        if extra_message != None:
            message += "：" + extra_message
        super(NoPermissionException, self).__init__(
            message=message,
        )


@dataclass
class RequiresLoginException(NoPermissionException):

    def __init__(self):
        super(RequiresLoginException, self).__init__(
            extra_message="操作需要有效饼干，但客户端并未设置饼干",
        )


@dataclass
class GatekeptException(NoPermissionException):
    # TODO: extends ClientException

    context: str
    current_page_number: int
    gatekeeper_post_id: int

    def __init__(self, context: str, current_page_number: int, gatekeeper_post_id: int):
        super(GatekeptException, self).__init__(
            extra_message="出现「卡99现象」",
        )

        self.context = context
        self.current_page_number = current_page_number
        self.gatekeeper_post_id = gatekeeper_post_id


@dataclass
class UnreachableLowerBoundPostIDException(ClientException):
    # TODO: extends ClientException?

    lower_bound_post_id: int

    def __init__(self, lower_bound_post_id: int):
        super(UnreachableLowerBoundPostIDException, self).__init__(
            message="串号下界比串首串号小",
        )

        self.lower_bound_post_id = lower_bound_post_id


@dataclass
class UnexpectedLowerBoundPostIDException(ClientException):
    # TODO: extends ClientException?

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


@dataclass
class ResourceNotExistsException(ClientException):
    def __init__(self):
        super(ResourceNotExistsException, self).__init__(
            message="目标资源不存在",
        )
