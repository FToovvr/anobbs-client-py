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

        if page > self.get_board_gatekeeper_page_number(options):
            raise NoPermissionException()

        with_login = self.get_login_policy(
            options) in ["enforce", "when_has_cookie"]
        if with_login and not self.has_cookie(options):
            raise RequiresLoginException()

        logging.debug(f"将获取版块：{board_id} 第 {page} 页，已登陆：{with_login}")

        def fn(): return self.__get_board_page(
            board_id, page=page, options=options, with_login=with_login)

        (board_page, bandwidth_usage) = try_request(
            fn, f"获取版块 {id} 第 {page} 页", self.get_max_attempts(options))

        return board_page, bandwidth_usage

    def __get_board_page(self, board_id: int, page: int, options: RequestOptions = {}, with_login: bool = False) -> Tuple[Board, BandwidthUsage]:

        session = self._make_session(options=options, with_login=with_login)

        queries = OrderedDict()
        queries["id"] = board_id
        queries["page"] = page
        if self.appid != None:
            queries["appid"] = self.appid
        queries["__t"] = current_timestamp_ms_offset_to_utc8()
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

        with_login = self.thread_page_requires_login(
            page=page, options=options)
        if with_login and not self.has_cookie(options):
            raise RequiresLoginException()

        logging.debug(f"将获取串：{id} 第 {page} 页，已登陆：{with_login}")

        def fn(): return self.__get_thread_page(
            id, page=page, options=options, with_login=with_login)

        (thread_page, bandwidth_usage) = try_request(
            fn, f"获取串 {id} 第 {page} 页", self.get_max_attempts(options))

        if for_analysis:
            thread_page.replies = list(filter(
                lambda post: post.user_id != "芦苇", thread_page.replies))

        return thread_page, bandwidth_usage

    def __get_thread_page(self, id: int, page: int, options: RequestOptions, with_login: bool = False) -> Tuple[Thread, BandwidthUsage]:

        session = self._make_session(options=options, with_login=with_login)

        queries = OrderedDict()
        queries["page"] = page
        if self.appid != None:
            queries["appid"] = self.appid
        queries["__t"] = current_timestamp_ms_offset_to_utc8()
        url = f"https://{self.host}/Api/thread/id/{id}?" + \
            urllib.parse.urlencode(queries)
        thread_page_json, bandwidth_usage = get_json(session, url)
        if thread_page_json == '该主题不存在':
            raise ResourceNotExistsException()

        return Thread(thread_page_json), bandwidth_usage

    def thread_page_requires_login(self, page: int, options: RequestOptions = {}) -> bool:
        """
        Returns
        -------
        是否需要使用饼干请求服务器。
        """

        login_policy = self.get_login_policy(options)
        has_cookie = self.has_cookie(options)
        gate_keeper_page_number = self.get_thread_gatekeeper_page_number(
            options)

        if login_policy == "enforce":
            return True

        if login_policy == "when_has_cookie":
            return has_cookie or page > gate_keeper_page_number
        elif login_policy in ("always_no", "when_required"):
            return page > gate_keeper_page_number

        raise ShouldNotReachException()

    def get_thread_gatekeeper_page_number(self, options: RequestOptions = {}) -> int:
        return self._get_option_value(options, "thread_gatekeeper_page_number", 100)

    def get_board_gatekeeper_page_number(self, options: RequestOptions = {}) -> int:
        return self._get_option_value(options, "board_gatekeeper_page_number", 100)
