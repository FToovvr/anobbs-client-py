from typing import Optional, OrderedDict, Dict, Any, Union, Literal, NamedTuple, Tuple, Callable
from dataclasses import dataclass, field

import time
import logging
import urllib
import urllib3
import json
import io

import requests
import requests_toolbelt

from .baseclient import BaseClient
from .requestutils import BandwidthUsage, try_request, get_json
from .usercookie import UserCookie
from .options import RequestOptions, LoginPolicy, LuweiCookieFormat
from .objects import Board, ThreadPage, BoardThread
from .utils import current_timestamp_ms_offset_to_utc8
from .exceptions import ShouldNotReachException, RequiresLoginException, NoPermissionException, ResourceNotExistsException, GatekeptException


@dataclass
class Client(BaseClient):
    """
        实现各类基础操作的客户端类。
    """

    def get_board_page(self, board_id: int, page: int, options: RequestOptions = {}) -> Tuple[Board, BandwidthUsage]:
        """
        获取指定板块的指定页。

        Parameters
        ----------
        board_id : int
            版块 ID。
        page : int
            页数。
        options : RequestOptions
            请求选项。
        """

        needs_login = self.board_page_requires_login(
            page=page, options=options)
        if needs_login and not self.has_cookie(options):
            raise RequiresLoginException()

        logging.debug(f"将获取版块：{board_id} 第 {page} 页，将会登录：{needs_login}")

        def request_fn():
            threads, bandwidth_usage = self._get_json(
                path=f'/Api/showf', options=options, needs_login=needs_login,
                id=board_id,
                page=page,
            )
            return list(map(lambda thread: BoardThread(thread), threads)), bandwidth_usage

        (board_page, bandwidth_usage) = try_request(
            request_fn, f"获取版块 {id} 第 {page} 页", self.get_max_attempts(options))

        return board_page, bandwidth_usage

    def get_thread_page(self, id: int, page: int, options: RequestOptions = {}, for_analysis: bool = False) -> Tuple[ThreadPage, BandwidthUsage]:
        """
        获取指定串的指定页。

        Parameters
        ----------
        id : int
            串号。
        page : int
            页数。
        options : RequestOptions
            请求选项。
        for_analysis : bool
            如果为真，将会过滤掉与分析无关的内容，以方便分析。
        """

        needs_login = self.thread_page_requires_login(
            page=page, options=options)
        if needs_login and not self.has_cookie(options):
            raise RequiresLoginException()

        logging.debug(f"将获取串：{id} 第 {page} 页，将会登录：{needs_login}")

        def request_fn():
            thread_page_json, bandwidth_usage = self._get_json(
                path=f'/Api/thread/id/{id}', options=options, needs_login=needs_login,
                page=page,
            )
            if thread_page_json == '该主题不存在':
                raise ResourceNotExistsException()

            return ThreadPage(thread_page_json), bandwidth_usage

        (thread_page, bandwidth_usage) = try_request(
            request_fn, f"获取串 {id} 第 {page} 页", self.get_max_attempts(options))

        if for_analysis:
            thread_page.replies = list(filter(
                lambda post: post.user_id != "芦苇", thread_page.replies))

        return thread_page, bandwidth_usage

    def _get_json(self, path: str, options: RequestOptions, needs_login: bool = False, **queries) -> Tuple[OrderedDict, BandwidthUsage]:
        session = self._make_session(options=options, needs_login=needs_login)
        url = self._make_request_url(path=path, **queries)
        return get_json(session, url)

    def _make_request_url(self, path: str, **queries) -> str:
        queries = OrderedDict(queries)

        # 添加通用参数
        if self.appid != None:
            queries["appid"] = self.appid
        queries["__t"] = current_timestamp_ms_offset_to_utc8()

        base_url = f'https://{self.host}{path}'
        return base_url + '?' + urllib.parse.urlencode(queries)

    def page_requires_login(self, page: int, gate_keeper: int, options: RequestOptions = {}) -> bool:
        """
        判断页面是否需要登录才能正常阅读。

        Parameters
        ----------
        page : int
            要请求的页面页数。
        gate_keeper : int
            从下页起会出现「卡页」现象的页数，
            即如果不登录，访问往后的页面都会响应该页的内容。

            2021-03-07: 目前无论是串还是板块，都是从第101页起重复第100页的内容。
        options : RequestOptions
            请求设置。

        Returns
        -------
        是否需要登录。
        """

        login_policy = self.get_login_policy(options)
        has_cookie = self.has_cookie(options)

        if login_policy == "enforce":
            return True

        if login_policy == "when_has_cookie":
            return has_cookie or page > gate_keeper
        elif login_policy in ("always_no", "when_required"):
            return page > gate_keeper

        raise ShouldNotReachException()

    def thread_page_requires_login(self, page: int, options: RequestOptions = {}) -> bool:
        return self.page_requires_login(
            page=page,
            gate_keeper=self.get_thread_gatekeeper_page_number(options),
            options=options,
        )

    def board_page_requires_login(self, page: int, options: RequestOptions = {}) -> bool:
        gk_pn = self.get_board_gatekeeper_page_number(options)
        if page > gk_pn:  # TODO: 放在这里是不是不太合适？
            raise GatekeptException(
                context='check_if_board_page_requires_login',
                current_page_number=None,
                gatekeeper_post_id=None,
            )
        return self.page_requires_login(
            page=page,
            gate_keeper=gk_pn,
            options=options,
        )

    def get_thread_gatekeeper_page_number(self, options: RequestOptions = {}) -> int:
        return self._get_option_value(options, "thread_gatekeeper_page_number", 100)

    def get_board_gatekeeper_page_number(self, options: RequestOptions = {}) -> int:
        return self._get_option_value(options, "board_gatekeeper_page_number", 100)
