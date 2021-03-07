from typing import OrderedDict, Any, List, Tuple, Optional
from dataclasses import dataclass

import json
import re
from datetime import datetime

from dateutil import tz


datetime_re = re.compile(r"^(.*?)\(.\)(.*?)$")
local_tz = tz.gettz("Asia/Shanghai")


@dataclass
class Post:
    """
    帖子基类。

    TODO: 回应比串多了一个目前用途未知的 ``status`` 字段，
          所以回应应该对应单独一个子类？
    """

    _raw: OrderedDict[str, Any]

    def __init__(self, data: OrderedDict[str, Any]):
        self._raw = data

    def raw_copy(self) -> OrderedDict[str, Any]:
        return OrderedDict(self._raw)

    @property
    def id(self) -> int:
        return int(self._raw["id"])

    @property
    def attachment_base(self) -> Optional[str]:
        return _none_if(self._raw["img"], "")

    @property
    def attachment_extension(self) -> Optional[str]:
        return _none_if(self._raw["ext"], "")

    @property
    def created_at_raw_text(self) -> str:
        return self._raw["now"]

    @property
    def created_at(self) -> datetime:
        g = datetime_re.match(self.created_at_raw_text)
        dt = datetime.strptime(f"{g[1]} {g[2]}", "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=local_tz)

    @property
    def user_id(self) -> str:
        return self._raw["userid"]

    @property
    def name(self) -> Optional[str]:
        return _none_if(self._raw["name"], "无名氏")

    @property
    def email(self) -> Optional[str]:
        return _none_if(self._raw["email"], "")

    @property
    def title(self) -> Optional[str]:
        return _none_if(self._raw["title"], "无标题")

    @property
    def content(self) -> str:
        return self._raw["content"]

    @property
    def marked_sage(self) -> bool:
        return self._raw["sage"] != "0"

    @property
    def marked_admin(self) -> bool:
        return self._raw["admin"] != "0"

    def to_json(self) -> str:
        return json.dumps(self._raw, indent=2, ensure_ascii=False)


def _none_if(content, none_mark) -> Optional[Any]:
    if content == none_mark:
        return None
    return content


@dataclass
class ThreadBody(Post):
    """
    串基类。

    串在这里专指「一串帖子」中的头部，即「一楼」。
    """

    _total_reply_count: int

    def __init__(self, data: OrderedDict[str, Any], _total_reply_count: Optional[int] = None):
        super(ThreadBody, self).__init__(data)

        if _total_reply_count != None:
            self._total_reply_count = _total_reply_count
        else:
            self._total_reply_count = int(self._raw["replyCount"])
        # 不 pop 来保持顺序
        self._raw["replyCount"] = None

    def raw_copy(self, keeps_reply_count: bool = True, _keeps_replies_slot=False) -> OrderedDict[str, Any]:
        copy = super(ThreadBody, self).raw_copy()
        if keeps_reply_count:
            copy["replyCount"] = str(self._total_reply_count)
        else:
            copy.pop("replyCount")
        if not _keeps_replies_slot:
            copy.pop("replys", None)
        return copy

    @property
    def total_reply_count(self) -> int:
        return self._total_reply_count


@dataclass
class ThreadPage(ThreadBody):
    """
    是 ``get_thread_page`` 返回的串页面，包含其自身 body 及该页的各回复帖。
    """

    _replies: List[Post]

    def __init__(self, data: OrderedDict[str, Any]):
        super(ThreadPage, self).__init__(data)

        self._replies = list(map(lambda post: Post(post), self._raw["replys"]))
        # 不 pop 来保持顺序
        self._raw["replys"] = None

    def raw_copy(self) -> OrderedDict[str, Any]:
        copy = super(ThreadPage, self).raw_copy(_keeps_replies_slot=True)
        copy["replys"] = self.replies
        return copy

    @property
    def body(self) -> ThreadBody:
        return ThreadBody(self._raw, _total_reply_count=self._total_reply_count)

    @property
    def replies(self) -> List[Post]:
        return self._replies

    @replies.setter
    def replies(self, replies: List[Post]):
        self._replies = replies

    def to_json(self) -> str:
        data = self.raw_copy()
        if self._replies != None:
            data["replys"] = list(
                map(lambda post: post.raw_copy(), self._replies))
        else:
            data.pop("replys", None)

        return json.dumps(data, indent=2, ensure_ascii=False)


@dataclass
class BoardThread(ThreadPage):
    """
    组成 ``get_board_page`` 返回的各串的 body。
    """

    def __init__(self, data: OrderedDict[str, Any]):
        super(BoardThread, self).__init__(data)

    @property
    def last_modified_time(self) -> datetime:
        if len(self.replies) == 0:
            return self.created_at
        return self.replies[-1].created_at


@dataclass
class TimelineThread(BoardThread):
    """
    暂未使用，预计用于组成时间线。
    """

    def __init__(self, data: OrderedDict[str, Any]):
        super(TimelineThread, self).__init__(data)

    @property
    def board_id(self) -> int:
        return int(self._raw["fid"])


Board = List[BoardThread]
