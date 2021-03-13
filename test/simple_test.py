from typing import NamedTuple

import unittest
import logging
from datetime import datetime, timedelta

from dateutil import tz

import anobbsclient
from anobbsclient.walk import create_walker, ReversalThreadWalkTarget, BoardWalkTarget

import os
import sys

logging.basicConfig(stream=sys.stderr)
logging.getLogger().setLevel(logging.DEBUG)

local_tz = tz.gettz("Asia/Shanghai")


class SimpleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user_agent = os.environ["ANOBBS_CLIENT_USER_AGENT"]
        cls.host = os.environ["ANOBBS_HOST"]
        cls.appid = os.environ["ANOBBS_CLIENT_APPID"]

        cls.luwei_cookie_expires = os.environ["ANOBBS_LUWEI_COOKIE_EXPIRES"]

        cls.user_hash = os.environ.get("ANOBBS_USERHASH", None)

    def new_client(self) -> anobbsclient.Client:
        return anobbsclient.Client(
            user_agent=SimpleTest.user_agent,
            host=SimpleTest.host,
            appid=SimpleTest.appid,
            default_request_options={
                "uses_luwei_cookie_format": SimpleTest.luwei_cookie_expires,
            },
        )

    @property
    def user_cookie(self) -> anobbsclient.UserCookie:
        assert(SimpleTest.user_hash != None)
        return anobbsclient.UserCookie(
            userhash=SimpleTest.user_hash,
        )

    def test_request_options(self):
        client = self.new_client()

        self.assertEqual(client.has_cookie(), False)
        self.assertEqual(client.get_login_policy(), "when_required")
        self.assertEqual(
            client.get_thread_gatekeeper_page_number(), 100)
        self.assertEqual(client.get_uses_luwei_cookie_format(),
                         SimpleTest.luwei_cookie_expires)
        self.assertEqual(client.get_max_attempts(), 5)

        options = {
            "user_cookie": anobbsclient.UserCookie(
                userhash="foo",
            ),
        }
        self.assertEqual(client.get_user_cookie(options).userhash, "foo")

    def test_check_login(self):
        client = self.new_client()
        user_cookie = anobbsclient.UserCookie(
            userhash="foo",
        )

        class Row(NamedTuple):
            policy: anobbsclient.options.LoginPolicy
            with_cookie: bool
            page_number: int
            expects_exception: bool
            expected_needs_login: bool

        gk_pn = client.get_thread_gatekeeper_page_number()

        for row in [
            Row("enforce", True, gk_pn, False, True),
            Row("enforce", True, gk_pn+1, False, True),
            Row("enforce", False, gk_pn, True, None),
            Row("enforce", False, gk_pn+1, True, None),
            Row("when_has_cookie", True, gk_pn, False, True),
            Row("when_has_cookie", True, gk_pn+1, False, True),
            Row("when_has_cookie", False, gk_pn, False, False),
            Row("when_has_cookie", False, gk_pn+1, True, None),
            Row("when_required", True, gk_pn, False, False),
            Row("when_required", True, gk_pn+1, False, True),
            Row("when_required", False, gk_pn, False, False),
            Row("when_required", False, gk_pn+1, True, None),
            Row("always_no", True, gk_pn, False, False),
            Row("always_no", True, gk_pn+1, True, None),
            Row("always_no", False, gk_pn, False, False),
            Row("always_no", False, gk_pn+1, True, None),
        ]:
            logging.debug(row)

            options = {
                "login_policy": row.policy,
            }
            if row.with_cookie:
                options["user_cookie"] = user_cookie

            if row.expects_exception:
                def fn(): return client.get_thread_page(
                    id=29556631,  # 无关。因为如果行为符合预期，将不会执行请求
                    page=row.page_number,
                    options=options,
                )
                self.assertRaises(anobbsclient.RequiresLoginException, fn)
            else:
                needs_login = client.thread_page_requires_login(
                    page=row.page_number,
                    options=options,
                )
                self.assertEqual(needs_login, row.expected_needs_login)

    def test_get_board_page(self):

        client = self.new_client()

        self.assertRaises(anobbsclient.NoPermissionException,
                          client.get_board_page, 4, page=101)

        (qst, _) = client.get_board_page(111, page=1)

        self.assertGreater(len(qst), 0)
        self.assertEqual(qst[-1].body.total_reply_count,
                         qst[-1].total_reply_count)
        self.assertIsNotNone(qst[-1].last_modified_time)

    def test_get_thread_page(self):
        # TODO: 测试更多字段是否正确处理

        client = self.new_client()

        (luwei_thread, _) = client.get_thread_page(
            49607, page=1, for_analysis=True)

        self.assertEqual(luwei_thread.user_id, "g3qeXeYq")
        self.assertEqual(luwei_thread.content, "这是芦苇")
        self.assertNotEqual(luwei_thread.attachment_base, None)

        dt = luwei_thread.created_at
        self.assertEqual(dt.utcoffset().total_seconds() / 60 / 60, 8)
        dt_text = (dt.strftime("%Y-%m-%d") +
                   "(" + "一二三四五六日"[dt.weekday()]+")" +
                   dt.strftime("%H:%M:%S"))
        self.assertEqual(luwei_thread.created_at_raw_text, dt_text)

    def test_get_thread_page_with_login(self):
        if SimpleTest.user_hash == None:
            self.skipTest(reason="需要登录")

        client = self.new_client()

        options = {
            "user_cookie": self.user_cookie,
        }

        (luwei_thread, _) = client.get_thread_page(
            49607, page=250, options=options, for_analysis=True,
        )

        self.assertGreater(int(luwei_thread.replies[0].id), 10000000)

    def test_get_404_thread_page(self):

        client = self.new_client()

        def get_404_thread():
            client.get_thread_page(28804321, page=1, for_analysis=True)

        self.assertRaises(
            anobbsclient.ResourceNotExistsException, get_404_thread)

    def test_thread_page_reverse_walker(self):

        client = self.new_client()

        walker = create_walker(
            target=ReversalThreadWalkTarget(
                thread_id=29184693,
                gatekeeper_post_id=99999999,
                start_page_number=3,
            ),
            client=client,
        )

        page_count, last_page_max_post_id = 0,  None
        for (n, page, _) in walker:
            self.assertTrue(n in [1, 2, 3])
            page_count += 1
            if n == 3:
                last_page_max_post_id = page.replies[-1].id
        self.assertEqual(page_count, 3)

        walker = create_walker(
            target=ReversalThreadWalkTarget(
                thread_id=29184693,
                gatekeeper_post_id=99999999,
                start_page_number=4,
                stop_before_post_id=last_page_max_post_id,
                expected_stop_page_number=3,
            ),
            client=client,
        )

        page_count = 0
        for (n, page, _) in walker:
            self.assertTrue(n in [3, 4])
            page_count += 1
            if n == 3:
                self.assertEqual(len(page.replies), 0)
        self.assertEqual(page_count, 2)

    def test_thread_page_reverse_walker_no_login(self):

        client = self.new_client()

        def case_no_login():
            for (_, _, _) in create_walker(
                target=ReversalThreadWalkTarget(
                    thread_id=29184693,
                    gatekeeper_post_id=99999999,
                    start_page_number=101,
                ),
                client=client,
            ):
                assert(False)
        self.assertRaises(anobbsclient.RequiresLoginException, case_no_login)

    def test_thread_page_reverse_walker_gatekept(self):

        client = self.new_client()

        (page100, _) = client.get_thread_page(29184693, page=100)
        gatekeeper_post_id = list(page100.replies)[-1].id

        def case_gatekept():
            for (_, _, _) in create_walker(
                target=ReversalThreadWalkTarget(
                    thread_id=29184693,
                    gatekeeper_post_id=gatekeeper_post_id,
                    start_page_number=101,
                ),
                client=client,
                options={
                    "user_cookie": anobbsclient.UserCookie(
                        userhash="",  # 无效的饼干
                    ),
                },
            ):
                assert(False)
        self.assertRaises(anobbsclient.GatekeptException, case_gatekept)

    def test_thread_page_reverse_walker_with_login(self):
        if SimpleTest.user_hash == None:
            self.skipTest(reason="需要登录")

        client = self.new_client()

        (page100, _) = client.get_thread_page(29184693, page=100)
        gatekeeper_post_id = list(page100.replies)[-1].id

        page_count = 0
        for (n, page, _) in create_walker(
            target=ReversalThreadWalkTarget(
                thread_id=29184693,
                gatekeeper_post_id=gatekeeper_post_id,
                start_page_number=101,
                stop_before_post_id=gatekeeper_post_id,
                expected_stop_page_number=100,
            ),
            client=client,
            options={
                "user_cookie": self.user_cookie,
            },
        ):
            self.assertTrue(n in [100, 101])
            page_count += 1
            if n == 100:
                self.assertEqual(len(page.replies), 0)
        self.assertEqual(page_count, 2)

    def test_board_page_walker(self):

        client = self.new_client()

        now = datetime.now(local_tz)
        two_hours_ago = now - timedelta(hours=2)

        for (_, page, _) in create_walker(
            target=BoardWalkTarget(
                board_id=111,
                start_page_number=1,
                stop_before_datetime=two_hours_ago,
            ),
            client=client,
        ):
            page: anobbsclient.BoardThread = page
            for thread in page:
                self.assertGreaterEqual(
                    thread.last_modified_time, two_hours_ago)

    def test_thread_page_reverse_walker_stop_before_datetime(self):

        client = self.new_client()

        page_count = 0
        for (n, page, _) in create_walker(
            target=ReversalThreadWalkTarget(
                thread_id=29184693,
                gatekeeper_post_id=99999999,
                start_page_number=98,
                stop_before_datetime=datetime(  # 2020-08-09(日)22:00:21
                    year=2020, month=8, day=9,
                    hour=22, minute=00, second=21,
                    tzinfo=local_tz,
                )
            ),
            client=client,
        ):
            page: anobbsclient.ThreadPage = page
            self.assertTrue(n in [96, 97, 98])
            page_count += 1
            if n == 96:
                self.assertEqual(page.replies[0].id, 29279607)
        self.assertEqual(page_count, 3)

    def test_reply_thread(self):
        self.skipTest("向服务器上传内容")

        client = self.new_client()

        client.reply_thread("test\n1234", to_thread_id=35783128, options={
            'user_cookie': self.user_cookie,
        })
