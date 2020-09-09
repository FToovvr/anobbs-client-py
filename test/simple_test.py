from typing import NamedTuple

import unittest
import logging

import anobbsclient
from anobbsclient.walk import walkthread

import os
import sys

logging.basicConfig(stream=sys.stderr)
logging.getLogger().setLevel(logging.DEBUG)


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
        self.assertEqual(client.get_max_attempts(), 3)

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

        for row in [
            Row("enforce", True, 100, False, True),
            Row("enforce", True, 101, False, True),
            Row("enforce", False, 100, True, None),
            Row("enforce", False, 101, True, None),
            Row("when_has_cookie", True, 100, False, True),
            Row("when_has_cookie", True, 101, False, True),
            Row("when_has_cookie", False, 100, False, False),
            Row("when_has_cookie", False, 101, True, None),
            Row("when_required", True, 100, False, False),
            Row("when_required", True, 101, False, True),
            Row("when_required", False, 100, False, False),
            Row("when_required", False, 101, True, None),
            Row("always_no", True, 100, False, False),
            Row("always_no", True, 101, True, None),
            Row("always_no", False, 100, False, False),
            Row("always_no", False, 101, True, None),
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

    def test_get_thread_page(self):
        # TODO: 测试更多字段是否正确处理

        client = self.new_client()

        (luwei_thread, _) = client.get_thread_page(
            49607, page=1, for_analysis=True)

        self.assertEqual(luwei_thread.user_id, "g3qeXeYq")
        self.assertEqual(luwei_thread.content, "这是芦苇")
        self.assertNotEqual(luwei_thread.attachment_base, None)

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

    def test_thread_page_reverse_walker(self):

        client = self.new_client()

        walker = walkthread.ThreadPageReverseWalker(
            client=client,
            thread_id=29184693,
            upper_bound_page=3,
            end_condition=walkthread.LowerBoundPageEndCondition(
                page=1, page_seen_max_post_id=None,
            ),
            gatekeeper_post_id=99999999,
        )

        page_count, last_page_max_post_id = 0,  None
        for (n, page, _) in walker:
            self.assertTrue(n in [1, 2, 3])
            page_count += 1
            if n == 3:
                last_page_max_post_id = page.replies[-1].id
        self.assertEqual(page_count, 3)

        walker = walkthread.ThreadPageReverseWalker(
            client=client,
            thread_id=29184693,
            upper_bound_page=4,
            end_condition=walkthread.LowerBoundPageEndCondition(
                page=3, page_seen_max_post_id=last_page_max_post_id,
            ),
            gatekeeper_post_id=99999999,
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
            for (_, _, _) in walkthread.ThreadPageReverseWalker(
                client=client,
                thread_id=29184693,
                upper_bound_page=101,
                end_condition=walkthread.LowerBoundPageEndCondition(
                    page=1, page_seen_max_post_id=None,
                ),
                gatekeeper_post_id=99999999,
            ):
                assert(False)
        self.assertRaises(anobbsclient.RequiresLoginException, case_no_login)

    def test_thread_page_reverse_walker_gatekept(self):

        client = self.new_client()

        (page100, _) = client.get_thread_page(29184693, page=100)
        gatekeeper_post_id = list(page100.replies)[-1].id

        def case_gatekept():
            for (_, _, _) in walkthread.ThreadPageReverseWalker(
                client=client,
                thread_id=29184693,
                upper_bound_page=101,
                end_condition=walkthread.LowerBoundPageEndCondition(
                    page=1, page_seen_max_post_id=None,
                ),
                gatekeeper_post_id=gatekeeper_post_id,
                request_options={
                    "user_cookie": anobbsclient.UserCookie(
                        userhash="",  # 无效的饼干
                    ),
                },
            ):
                assert(False)
        self.assertRaises(anobbsclient.GatekeptException, case_gatekept)

    def test_thread_page_reverse_walker_with_login(self):

        client = self.new_client()

        (page100, _) = client.get_thread_page(29184693, page=100)
        gatekeeper_post_id = list(page100.replies)[-1].id

        page_count = 0
        for (n, page, _) in walkthread.ThreadPageReverseWalker(
            client=client,
            thread_id=29184693,
            upper_bound_page=101,
            end_condition=walkthread.LowerBoundPageEndCondition(
                page=100, page_seen_max_post_id=gatekeeper_post_id,
            ),
            gatekeeper_post_id=gatekeeper_post_id,
            request_options={
                "user_cookie": self.user_cookie,
            },
        ):
            self.assertTrue(n in [100, 101])
            page_count += 1
            if n == 100:
                self.assertEqual(len(page.replies), 0)
        self.assertEqual(page_count, 2)
