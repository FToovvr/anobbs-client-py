from typing import Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class UserCookie:
    """
    代表一个用户饼干。
    """

    userhash: str
    """饼干的 ``userhash``。"""

    mark_name: Optional[str] = None
    """辅助标记用的饼干名，可不填。"""
