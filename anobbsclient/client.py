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
from .objects import Board, Thread, BoardThread
from .utils import current_timestamp_ms_offset_to_utc8
from .exceptions import ShouldNotReachException, RequiresLoginException, NoPermissionException, ResourceNotExistsException


@dataclass
class Client(BaseClient):

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

        logging.debug(f"将获取版块：{board_id} 第 {page} 页，将会登陆：{needs_login}")

        def fn(): return self.__get_board_page(
            board_id, page=page, options=options, needs_login=needs_login)

        (board_page, bandwidth_usage) = try_request(
            fn, f"获取版块 {id} 第 {page} 页", self.get_max_attempts(options))

        return board_page, bandwidth_usage

    def __get_board_page(self, board_id: int, page: int, options: RequestOptions = {}, needs_login: bool = False) -> Tuple[Board, BandwidthUsage]:

        session = self._make_session(options=options, needs_login=needs_login)

        queries = OrderedDict()
        queries["id"] = board_id
        queries["page"] = page
        self._add_common_parameters(queries)
        url = f"https://{self.host}/Api/showf?" + \
            urllib.parse.urlencode(queries)
        threads, bandwidth_usage = get_json(session, url)
        return list(map(lambda thread: BoardThread(thread), threads)), bandwidth_usage

    def get_thread_page(self, id: int, page: int, options: RequestOptions = {}, for_analysis: bool = False) -> Tuple[Thread, BandwidthUsage]:
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

        logging.debug(f"将获取串：{id} 第 {page} 页，将会登陆：{needs_login}")

        def fn(): return self.__get_thread_page(
            id, page=page, options=options, needs_login=needs_login)

        (thread_page, bandwidth_usage) = try_request(
            fn, f"获取串 {id} 第 {page} 页", self.get_max_attempts(options))

        if for_analysis:
            thread_page.replies = list(filter(
                lambda post: post.user_id != "芦苇", thread_page.replies))

        return thread_page, bandwidth_usage

    def __get_thread_page(self, id: int, page: int, options: RequestOptions, needs_login: bool = False) -> Tuple[Thread, BandwidthUsage]:

        session = self._make_session(options=options, needs_login=needs_login)

        queries = OrderedDict()
        queries["page"] = page
        self._add_common_parameters(queries)
        url = f"https://{self.host}/Api/thread/id/{id}?" + \
            urllib.parse.urlencode(queries)
        thread_page_json, bandwidth_usage = get_json(session, url)
        if thread_page_json == '该主题不存在':
            raise ResourceNotExistsException()

        return Thread(thread_page_json), bandwidth_usage

    def _add_common_parameters(self, queries: OrderedDict):
        if self.appid != None:
            queries["appid"] = self.appid
        queries["__t"] = current_timestamp_ms_offset_to_utc8()

    def page_requires_login(self, page: int, gate_keeper: int, options: RequestOptions = {}) -> bool:
        """
        判断页面是否需要登陆才能正常阅读。

        Parameters
        ----------
        page : int
            要请求的页面页数。
        gate_keeper : int
            开始会出现「卡99」现象的页数，即第一个与之前页重复的页面。
        options : RequestOptions
            请求设置。

        Returns
        -------
        是否需要登陆。
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
        return self.page_requires_login(
            page=page,
            gate_keeper=self.get_board_gatekeeper_page_number(options),
            options=options,
        )

    def get_thread_gatekeeper_page_number(self, options: RequestOptions = {}) -> int:
        return self._get_option_value(options, "thread_gatekeeper_page_number", 100)

    def get_board_gatekeeper_page_number(self, options: RequestOptions = {}) -> int:
        return self._get_option_value(options, "board_gatekeeper_page_number", 100)
