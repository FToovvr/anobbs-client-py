from typing import Tuple, Dict, Any
from dataclasses import dataclass
import abc

import anobbsclient


@dataclass(frozen=True)
class WalkTargetInterface:

    start_page_number: int
    """遍历开始的页数。"""

    @abc.abstractmethod
    def create_state(self) -> Any:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_page(self, current_page_number: int,
                 client: anobbsclient.Client, options: anobbsclient.RequestOptions
                 ) -> Tuple[Any, anobbsclient.BandwidthUsage]:
        raise NotImplementedError()

    @abc.abstractmethod
    def check_gatekept(self, current_page_number: int,
                       current_page: Any,
                       client: anobbsclient.Client, options: anobbsclient.RequestOptions,
                       g: Dict[str, Any]):
        raise NotImplementedError()

    @abc.abstractmethod
    def should_stop(self, current_page: Any, current_page_number: int,
                    client: anobbsclient.Client, options: anobbsclient.RequestOptions,
                    g: Dict[str, Any]) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_next_page_number(self, current_page_number: int, g: Dict[str, Any]):
        raise NotImplementedError()
