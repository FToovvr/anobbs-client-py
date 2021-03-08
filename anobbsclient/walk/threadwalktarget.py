from typing import Optional, Tuple, OrderedDict, Dict, Any
from dataclasses import dataclass, field

import anobbsclient

from .walktarget import WalkTargetInterface


@dataclass
class ReversalThreadWalkTargetState():
    last_page_min_id: Optional[int] = None


@dataclass(frozen=True)
class ReversalThreadWalkTarget(WalkTargetInterface):
    """
    从后向前，一路游荡到第一页，或者遇到的回复的串号/发布时间比预定的小/早时结束。

    可以保证不遗漏地归档串。
    """

    thread_id: int
    """要遍历的串的串号。"""

    gatekeeper_post_id: int
    """
    不需要登录能看到的串号最大的串的串号。
    
    用于检测是否发生卡页。
    """

    # overriding
    start_page_number: int

    stop_before_post_id: Optional[int] = field(default=None)
    """
    停止串号。
    在看到小于等于此串号的回复时停止。

    如果为 ``None``，则会一路游荡到第一页。
    """

    expected_stop_page_number: Optional[int] = field(default=None)
    """
    如果串号是停止条件，可以设置此值，表示停止串号应该在此页或越过此页后找到。

    由于a岛只存在删串不存在增串，已知一个串号曾经出现在某页，
    则「反向遍历时先于预期遇到/超越此串号」只可能是出现「卡页」现象，
    服务器返回了这么遍历会更靠后才会遇到的页面。
    """

    # overriding
    def create_state(self) -> ReversalThreadWalkTargetState:
        return ReversalThreadWalkTargetState()

    # overriding
    def get_page(self, current_page_number: int,
                 client: anobbsclient.Client, options: anobbsclient.RequestOptions
                 ) -> Tuple[anobbsclient.ThreadPage, anobbsclient.BandwidthUsage]:
        """
        获取当前页数对应的页面内容并返回。

        Parameters
        ----------
        current_page_number : int
            当前页数。
        client : anobbsclient.Client
            用于发送请求的客户端。
        options : anobbsclient.RequestOptions
            要传入客户端的外部的请求设置。
        """
        return client.get_thread_page(
            id=self.thread_id, page=current_page_number,
            options=options, for_analysis=True,
        )

    # overriding
    def check_gatekept(self, current_page_number: int,
                       current_page: anobbsclient.ThreadPage,
                       client: anobbsclient.Client, options: anobbsclient.RequestOptions,
                       g: ReversalThreadWalkTargetState):
        """
        检查是否发生卡页。

        如检测的发生卡页，会直接相应的抛出异常。

        Parameters
        ----------
        current_page_number : int
            当前页数。
        current_page : anobbsclient.ThreadPage
            当前获取到的页。
        client : anobbsclient.Client
            用于发送请求的客户端。
        options : anobbsclient.RequestOptions
            要传入客户端的外部的请求设置。
        """

        # 通过检查本页与上一页是否一致来检测是否卡页。
        # 当前页应该至少有1串比上一页的所有串号要小。
        # 极端情况下，在获取两页期间，小于等于本页的地方有19串被删会导致误判，这里不考虑
        if g.last_page_min_id is not None \
                and current_page.replies[0].id >= g.last_page_min_id:
            raise anobbsclient.GatekeptException(
                context="previous_page_min_post_id",
                current_page_number=current_page_number,
                gatekeeper_post_id=g.last_page_min_id,
            )
        g.last_page_min_id = current_page.replies[0].id

        # 如果确认此页不登录会卡页，
        # 那通过对比「守门串号」（即不登录能看到的最后一串的串号）来检测是否卡页。
        # 少数情况下，遍历期间有19串被删导致「守门页」的串号要比起初获得的「守门串号」大，
        # 不过自从遍历第二页起就可以用前面对比两页的方法检测是否发生卡页，因此不是大问题
        if client.thread_page_requires_login(current_page_number) \
                and current_page.replies[0].id <= self.gatekeeper_post_id:
            raise anobbsclient.GatekeptException(
                context="gatekeeper_post_id",
                current_page_number=current_page_number,
                gatekeeper_post_id=self.gatekeeper_post_id,
            )

    # overriding
    def should_stop(self, current_page: anobbsclient.ThreadPage, current_page_number: int,
                    client: anobbsclient.Client, options: anobbsclient.RequestOptions,
                    g: ReversalThreadWalkTargetState) -> bool:
        """
        返回是否已经达成停止条件。
        会在获取页面后被调用。

        TODO: 考虑将时间作为停止条件。

        Parameters
        ----------
        current_page : anobbsclient.ThreadPage
            当前获取到的页。
        next_page_number : int
            当前页数。
        """

        # 如果有设置停止串号，
        # 则试着找到停止串号（如果没有，则比它小且离它最近的串号）在回复中的 index
        stop_i = None
        if self.stop_before_post_id is not None:
            for (i, reply) in enumerate(current_page.replies):
                if reply.id <= self.stop_before_post_id:
                    stop_i = i
                else:
                    break

        if stop_i != None:  # 找到了上述串号
            if self.expected_stop_page_number is not None \
                    and current_page_number > self.expected_stop_page_number:
                # 明明还早，却遇到/越过了停止串号，代表卡页了

                if self.expected_stop_page_number == client.get_thread_gatekeeper_page_number():
                    # 预期停止的页面正好是「守门页」，解释了为何发生卡页。
                    # 当然，极端情况可能存在删串导致此刻「守门页」已经不包含该串号，
                    # 那这里就无法判断，以其他方法补充判断。
                    # （其他方法指用采集前新获取的「守门串号」判断，除非采集期间连删19楼不会有问题）
                    raise anobbsclient.GatekeptException(
                        context="lower_bound_post_id",
                        current_page_number=current_page_number,
                        gatekeeper_post_id=self.stop_before_post_id,
                    )
                else:  # TODO: 可能是卡页也可能是遇到了神秘状况，先抛个不一样的异常糊弄过去
                    raise anobbsclient.UnexpectedLowerBoundPostIDException(
                        current_page_number=current_page_number,
                        expected_lower_bound_page_number=self.expected_stop_page_number,
                        lower_bound_post_id=self.stop_before_post_id,
                    )

            # 截掉更早的回复。
            # TODO: 允许自定义是否截掉
            current_page.replies = current_page.replies[stop_i+1:]
            return True

        if current_page_number == 1:
            # 越过第1页
            return True

    # overriding
    def get_next_page_number(self, current_page_number: int, g: ReversalThreadWalkTargetState):
        """
        获取将要获取的下一页的页数。

        Parameters
        ----------
        current_page_number : int
            当前页的页数。
        """
        return current_page_number - 1
