from typing import OrderedDict, Any, List, Tuple, Optional
from dataclasses import dataclass

import json


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
        return self._raw["id"]

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
    def user_id(self) -> int:
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

    __total_reply_count: int

    def __init__(self, data: OrderedDict[str, Any]):
        super(ThreadBody, self).__init__(data)

        self.__total_reply_count = int(self._raw["replyCount"])
        # 不 pop 来保持顺序
        self._raw["replyCount"] = None

    def raw_copy(self, keeps_reply_count: bool = True, _keeps_replies_slot=False) -> OrderedDict[str, Any]:
        copy = super(ThreadBody, self).raw_copy()
        if keeps_reply_count:
            copy["replyCount"] = str(self.__total_reply_count)
        else:
            copy.pop("replyCount")
        if not _keeps_replies_slot:
            copy.pop("replys", None)
        return copy

    @property
    def total_reply_count(self) -> int:
        return self.__total_reply_count


@dataclass
class Thread(ThreadBody):

    __replies: Optional[List[Post]]

    def __init__(self, data: OrderedDict[str, Any]):
        super(Thread, self).__init__(data)

        if "replys" in self._raw:
            self.__replies = map(lambda post: Post(post),
                                 self._raw["replys"])
            # 不 pop 来保持顺序
            self._raw["replys"] = None
        else:
            self.__replies = None

    def raw_copy(self) -> OrderedDict[str, Any]:
        copy = super(Thread, self).raw_copy(_keeps_replies_slot=True)
        copy["replys"] = self.replies
        return copy

    @property
    def body(self) -> ThreadBody:
        return ThreadBody(self._raw)

    @property
    def replies(self) -> Optional[List[Post]]:
        return self.__replies

    @replies.setter
    def replies(self, replies: List[Post]):
        self.__replies = replies

    def to_json(self) -> str:
        data = self.raw_copy()
        if self.__replies != None:
            data["replys"] = map(lambda post: post.body, self.__replies)
        else:
            data.pop("replys", None)

        return json.dumps(data, indent=2, ensure_ascii=False)


@dataclass
class TimelineThread(Thread):

    @property
    def board_id(self) -> int:
        return int(self._raw["fid"])


Board = List[Thread]
