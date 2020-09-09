from typing import Optional
from dataclasses import dataclass


class ShouldNotReachException(Exception):
    pass


@dataclass(frozen=True)
class ClientException(Exception):

    message: str


@dataclass(frozen=True)
class RequiresLoginException(ClientException):

    def __init__(self):
        super(RequiresLoginException, self).__init__(
            message="操作需要有效饼干，但客户端并未设置饼干",
        )


@dataclass(frozen=True)
class NoPermissionException(ClientException):

    def __init__(self):
        super(NoPermissionException, self).__init__(
            message="无操作权限",
        )


@dataclass
class GatekeptException(Exception):
    # TODO: extends ClientException

    context: str
    current_page_number: int
    gatekeeper_post_id: int


@dataclass
class UnreachableLowerBoundPostIDException(Exception):
    # TODO: extends ClientException?

    lower_bound_post_id: int


@dataclass
class UnexpectedLowerBoundPostIDException(Exception):
    # TODO: extends ClientException?

    current_page_number: int
    expected_lower_bound_page_number: int
    lower_bound_post_id: int
