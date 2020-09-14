from typing import OrderedDict, Any, List, Tuple, Optional
from dataclasses import dataclass

import json
import re
from datetime import datetime

import pytz


datetime_re = re.compile(r"^(.*?)\(.\)(.*?)$")
tz = pytz.timezone("Asia/Shanghai")


@dataclass
class Post:
    # TODO: 回应比串多了一个目前用途未知的 ``status`` 字段，
    # 所以回应应该对应单独一个子类？

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
        return tz.localize(dt)

    @property
    def user_id(self) -> str:
        return self._raw["userid"]

    @property
    def name(self) -> str:
        return _none_if(self._raw["name"], "无名氏")

    @property
    def email(self) -> str:
        return _none_if(self._raw["email"], "")

    @property
    def title(self) -> str:
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
class Thread(ThreadBody):
    # TODO: 改名为 ``ThreadPage```

    _replies: Optional[List[Post]]

    def __init__(self, data: OrderedDict[str, Any]):
        super(Thread, self).__init__(data)

        if "replys" in self._raw:
            self._replies = map(lambda post: Post(post),
                                self._raw["replys"])
            # 不 pop 来保持顺序
            self._raw["replys"] = None
        else:
            self._replies = None

    def raw_copy(self) -> OrderedDict[str, Any]:
        copy = super(Thread, self).raw_copy(_keeps_replies_slot=True)
        copy["replys"] = self.replies
        return copy

    @property
    def body(self) -> ThreadBody:
        return ThreadBody(self._raw, _total_reply_count=self._total_reply_count)

    @property
    def replies(self) -> Optional[List[Post]]:
        return self._replies

    @replies.setter
    def replies(self, replies: List[Post]):
        self._replies = replies

    def to_json(self) -> str:
        data = self.raw_copy()
        if self._replies != None:
            data["replys"] = map(lambda post: post.body, self._replies)
        else:
            data.pop("replys", None)

        return json.dumps(data, indent=2, ensure_ascii=False)


@dataclass
class TimelineThread(Thread):

    @property
    def board_id(self) -> int:
        return int(self._raw["fid"])


Board = List[Thread]
