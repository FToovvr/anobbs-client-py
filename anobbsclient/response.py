from typing import OrderedDict, Any, List
from dataclasses import dataclass


@dataclass
class Response:
    """
    A岛客户端的响应。

    Parameters
    ----------

    body : OrderedDict[str, Any]
        JSON解析后的API响应内容。
        字典项保留原始顺序。
        可能经过后期处理。

    content_size : int
        处理前的原始响应的字节数。
    """

    body: OrderedDict[str, Any]
    content_size: int


@dataclass
class ThreadResponse(Response):

    @property
    def replies(self) -> List[OrderedDict[str, Any]]:
        return self.body["replys"]

    @replies.setter
    def replies(self, replies: List[OrderedDict[str, Any]]):
        self.body["replys"] = replies
