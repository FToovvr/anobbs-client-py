from typing import Any, Dict, Optional, Set
from dataclasses import dataclass, field

from datetime import datetime

import anobbsclient

from .walktarget import WalkTargetInterface


@dataclass
class BoardWalkTargetState:
    stop_before_datetime: datetime
    latest_seen_datetime: Optional[datetime] = None

    seen_thread_ids: Set = field(default_factory=set)

    found_last_replies_before_stop_datetime: bool = False
    should_back_to_begin: bool = False


@dataclass(frozen=True)
class BoardWalkTarget(WalkTargetInterface):

    board_id: int
    """要遍历的版块的id。"""

    # overriding
    start_page_number: int

    stop_before_datetime: datetime
    """
    停止于时间。
    在看到最后回复时间早于此时间时停止。
    """

    def create_state(self) -> BoardWalkTargetState:
        return BoardWalkTargetState(stop_before_datetime=self.stop_before_datetime)

    # overriding
    def get_page(self, current_page_number: int,
                 client: anobbsclient.Client, options: anobbsclient.RequestOptions
                 ) -> [anobbsclient.Board, anobbsclient.BandwidthUsage]:
        return client.get_board_page(
            board_id=self.board_id, page=current_page_number,
            options=options,
        )

    # overriding
    def check_gatekept(self, current_page_number: int,
                       current_page: anobbsclient.Board,
                       client: anobbsclient.Client, options: anobbsclient.RequestOptions,
                       g: BoardWalkTargetState):

        if current_page_number == 1:
            # 在第一页记录这一轮见过的最晚的时间
            g.latest_seen_datetime = current_page[0].last_modified_time

        stop_before_datetime = g.stop_before_datetime
        if current_page[-1].last_modified_time < stop_before_datetime:
            # 如果该页最后一串超过停止时间
            g.found_last_replies_before_stop_datetime = True
            for (i, thread) in enumerate(current_page):
                if thread.last_modified_time < stop_before_datetime:
                    current_page[:] = current_page[:i]

        # 借用这里去重
        current_page[:] = [
            thread for thread in current_page if thread.id not in g.seen_thread_ids]
        for thread in current_page:
            g.seen_thread_ids.add(thread.id)

        # TODO: 超过100页无论是否登录都会卡页，应该给下面的方法改个名
        if client.board_page_requires_login(current_page_number):
            raise anobbsclient.GatekeptException(
                context='board_page_number',
                current_page_number=current_page_number,
                gatekeeper_post_id=None,
            )

    # overriding
    def should_stop(self, current_page: anobbsclient.Board, current_page_number: int,
                    client: anobbsclient.Client, options: anobbsclient.RequestOptions,
                    g: BoardWalkTargetState) -> bool:

        if g.found_last_replies_before_stop_datetime:
            if current_page_number == 1:
                return True
            # 如果不本身就在第1页则回到第1页，防止遗漏期间被顶上去的串
            g.should_back_to_begin = True
            g.stop_before_datetime = g.latest_seen_datetime
            g.latest_seen_datetime = None
        return False

    # overriding
    def get_next_page_number(self, current_page_number: int, g: BoardWalkTargetState):
        # 为了防止遗漏遍历途中被顶上去的串，如果遍历不在第1页便停止，则回到第1页
        if g.should_back_to_begin:
            g.should_back_to_begin = False
            return 1

        return current_page_number + 1
