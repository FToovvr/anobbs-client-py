from typing import NamedTuple

import unittest
import logging

import anobbsclient

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

    def test_request_options(self):
        client = self.new_client()

        self.assertEqual(client.has_cookie(), False)
        self.assertEqual(client._Client__get_login_policy(), "when_required")
        self.assertEqual(client._Client__get_gatekeeper_page_number(), 99)
        self.assertEqual(client._Client__get_uses_luwei_cookie_format(),
                         SimpleTest.luwei_cookie_expires)
        self.assertEqual(client._Client__get_max_attempts(), 3)

        options = {
            "user_cookie": anobbsclient.UserCookie(
                userhash="foo",
            ),
        }
        self.assertEqual(client._Client__get_user_cookie(options).userhash,
                         "foo")

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
            Row("enforce", True, 1, False, True),
            Row("enforce", True, 100, False, True),
            Row("enforce", False, 1, True, None),
            Row("enforce", False, 100, True, None),
            Row("when_has_cookie", True, 1, False, True),
            Row("when_has_cookie", True, 100, False, True),
            Row("when_has_cookie", False, 1, False, False),
            Row("when_has_cookie", False, 100, True, None),
            Row("when_required", True, 1, False, False),
            Row("when_required", True, 100, False, True),
            Row("when_required", False, 1, False, False),
            Row("when_required", False, 100, True, None),
            Row("always_no", True, 1, False, False),
            Row("always_no", True, 100, True, None),
            Row("always_no", False, 1, False, False),
            Row("always_no", False, 100, True, None),
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
            "user_cookie": anobbsclient.UserCookie(
                userhash=SimpleTest.user_hash,
            ),
        }

        (luwei_thread, _) = client.get_thread_page(
            49607, page=250, options=options, for_analysis=True,
        )

        self.assertGreater(int(luwei_thread.replies[0].id), 10000000)
