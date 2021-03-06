from __future__ import annotations
from typing import Union, List, Tuple, Optional, Iterable, Callable, Any
from dataclasses import dataclass, field

import anobbsclient


@dataclass(frozen=True)
class EndCondition:
    pass


@dataclass(frozen=True)
class LowerBoundPageEndCondition(EndCondition):
    """
    Fields
    ------
    page : int
        页数下界。
        获取的页面截止到此处，但可能因需要补漏，使获取页面的页数小于此页数。

    page_seen_max_post_id : int
        前次获取的下界页面中最大的串号，也是本次的串号下界。
        在到达或越过页数下界后，遇到此串号的回应一般代表已经没有缺漏。
        当然，极端情况下也可能是「卡99」了，这里不做考虑。
        在串号下界为第一页时，此参数应为空。
    """
    page: int
    page_seen_max_post_id: Optional[int]

    def __post_init__(self):
        assert(self.page >= 1)
        if self.page > 1:
            assert(self.page_seen_max_post_id != None)
        else:
            assert(self.page_seen_max_post_id == None)


@dataclass
class ThreadPageReverseWalker:

    client: anobbsclient.Client
    """获取页面用的客户端。"""

    thread_id: int
    """目标串的串号。"""
    upper_bound_page: int
    """页数上界。
    从此处开始获取页面。
    """
    end_condition: LowerBoundPageEndCondition
    """ 结束条件。"""
    gatekeeper_post_id: int
    """在获取比页数下界页数小的页面中遇到的最大的串号。
    如果获取的页面有串号越过（小于）此串号，则表示可能「卡99」了。
    不过如果该页面已经越过页数下界，且在越过的页面中有回应的串号大于 lower_bound_post_id，则应该没有「卡99」。
    （但也可能是在这一过程中「卡99」）
    """

    request_options: anobbsclient.RequestOptions = field(default_factory=dict)

    __current_page_number: int = field(init=False)

    __previous_page_min_post_id: Optional[int] = field(init=None, default=None)

    __done: bool = False

    def __post_init__(self):

        self.__current_page_number = self.upper_bound_page

    def __iter__(self) -> ThreadPageReverseWalker:
        return self

    def __next__(self) -> Tuple[int, anobbsclient.Thread, anobbsclient.BandwidthUsage]:
        """
        Returns
        -------
        当前获取到的页面。
        顺序为页数倒叙。

        Raises
        ------
        RequiresLoginException
            如果需要登录，但并未登录。

        GatekeepedException
            如果检测到「卡99」。

        UnreachableLowerBoundPostIDException
            如果提前遇到了下界串号。

        UnexpectedLowerBoundPostIDException
            如果下界串号比第一页中第一个回应的串号还要小。
        """

        self.__check_should_stop()

        (page, bandwidth_usage) = self.client.get_thread_page(
            self.thread_id, page=self.__current_page_number, options=self.request_options, for_analysis=True)

        if self.__has_lower_bound_page_end_condition:
            lower_bound_index = None
            if self.__lower_bound_post_id != None:
                lower_bound_index = self.__try_find_lower_bound_index(page)

            if lower_bound_index != None:
                # 找到下界串号了，代表抓取结束，没有遗漏
                self.__check_current_page_can_be_lower_bound()

                if page.replies[lower_bound_index].id == self.__lower_bound_post_id:
                    page.replies = page.replies[lower_bound_index+1:]

                self.__done = True
                # TODO: 原来对应的是 ``self.__lower_bound_page_number``，应该是原来写错了？
                return (self.__current_page_number, page, bandwidth_usage)

        needs_login = self.client.thread_page_requires_login(
            page=self.__current_page_number)
        if needs_login:
            self.__check_gatekept(page)

        self.previous_page_min_post_id = page.replies[0].id

        current_page_number = self.__current_page_number
        self.__current_page_number -= 1
        return (current_page_number, page, bandwidth_usage)

    def __check_should_stop(self) -> bool:
        if self.__done:
            raise StopIteration

        if self.__current_page_number == 0:
            # 向下越过了第一页
            if (isinstance(self.end_condition, LowerBoundPageEndCondition)
                    and self.end_condition.page_seen_max_post_id != None):
                raise anobbsclient.UnreachableLowerBoundPostIDException(
                    self.end_condition.page_seen_max_post_id)

            raise StopIteration

    @property
    def __has_lower_bound_page_end_condition(self) -> bool:
        return isinstance(self.end_condition, LowerBoundPageEndCondition)

    @property
    def __lower_bound_post_id(self) -> int:
        assert(self.__has_lower_bound_page_end_condition)
        if isinstance(self.end_condition, LowerBoundPageEndCondition):
            return self.end_condition.page_seen_max_post_id

    @property
    def __lower_bound_page_number(self) -> int:
        assert(self.__has_lower_bound_page_end_condition)
        if isinstance(self.end_condition, LowerBoundPageEndCondition):
            return self.end_condition.page

    def __try_find_lower_bound_index(self, page: anobbsclient.Thread) -> Optional[int]:
        lower_bound_index = _find_first_index(
            reversed(page.replies), lambda post: post.id <= self.__lower_bound_post_id)
        if lower_bound_index != None:
            lower_bound_index = len(page.replies) - 1 - lower_bound_index
        return lower_bound_index

    def __check_current_page_can_be_lower_bound(self):
        if self.__current_page_number > self.__lower_bound_page_number:
            # 不应该在下界页面前找到下界串号
            if self.__lower_bound_page_number == self.client.get_thread_gatekeeper_page_number(self.request_options):
                raise anobbsclient.GatekeptException(
                    context="lower_bound_post_id",
                    current_page_number=self.__current_page_number,
                    gatekeeper_post_id=self.__lower_bound_post_id,
                )
            raise anobbsclient.UnexpectedLowerBoundPostIDException(
                self.__current_page_number, self.__lower_bound_page_number, self.__lower_bound_post_id)

    def __check_gatekept(self, page: anobbsclient.Thread):
        if page.replies[0].id <= self.gatekeeper_post_id:
            # 作为「守门页」后的页面，有串的串号比「之前获取到的「守门页」中最大的串号」要小，代表「卡99」了。
            # 但如果「获取「守门页」最大串号」与「获取当前页」期间，「守门页」或之前连抽了19串或以上，即使「卡99」了也无法发现。
            # 由于间隔越长，连抽19串的可能越大，因此应该在每一轮转存前都获取一次「守门串号」。
            # 由于每一轮从第二页之后都可以用备用方案，之后便不成问题
            raise anobbsclient.GatekeptException(
                "gatekeeper_post_id", self.__current_page_number, self.gatekeeper_post_id)
        if self.__previous_page_min_post_id != None and page.replies[0].id >= self.__previous_page_min_post_id:
            # 新获取的前一页没有串的串号比旧的后一页要小，要不然就是两页获取期间连抽了19串以上，要不然就是「卡99」了。
            # 鉴于前者的可能性应该不大，这里便忽略此可能，判定为「卡99」
            raise anobbsclient.GatekeptException(
                "previous_page_min_post_id", self.__current_page_number, self.__previous_page_min_post_id)


def _find_first_index(iter: Iterable[Any], where: Callable[[Any], bool]) -> Optional[int]:
    try:
        return next(i for i, v in enumerate(iter) if where(v))
    except StopIteration:
        return None
