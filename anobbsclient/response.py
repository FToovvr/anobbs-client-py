from typing import OrderedDict, Any, List, Tuple
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

    content_size : Tuple[int, int]
        上传字节数与下载字节数。
    """

    body: OrderedDict[str, Any]
    bandwidth_usage: Tuple[int, int]


@dataclass
class ThreadResponse(Response):

    @property
    def replies(self) -> List[OrderedDict[str, Any]]:
        return self.body["replys"]

    @replies.setter
    def replies(self, replies: List[OrderedDict[str, Any]]):
        self.body["replys"] = replies
