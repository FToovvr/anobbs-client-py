# AnoBBS Client

AnoBBS（A岛所用匿名版架构）API 的 Python 封装库。

[![GitHub license](https://img.shields.io/github/license/FToovvr/anobbs-client-py.svg)](https://github.com/FToovvr/anobbs-client-py/blob/master/LICENSE)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/anobbs-client.svg)](https://pypi.python.org/pypi/anobbs-client/)
[![PyPI version shields.io](https://img.shields.io/pypi/v/anobbs-client.svg)](https://pypi.python.org/pypi/anobbs-client/)
[![GitHub issues](https://img.shields.io/github/issues/FToovvr/anobbs-client-py.svg)](https://GitHub.com/FToovvr/anobbs-client-py/issues/)


功能随个人需要增加。

注意⚠️：由于本库出发点的项目没有多线程需求，所以本库当前只以单线程使用为目的设计。虽然每个请求都奢侈地专门创建了一个新的 Session，但共用的 CookieJar 并非线程安全。

## 实现功能

* 查看
    * [x] 版块
    * [x] 页面
    * [ ] 版块列表/版规介绍/…
    * 遍历
        * [x] 反向遍历串页面
        * [x] 遍历版块页面
* [ ] 发布
    * [ ] 串
    * [x] 回应
* [ ] 添加订阅/删除订阅
* [x] 装载饼干
* [ ] …

## 术语

* 「卡页」「卡99」
    * 访问串的100页之后的页面，响应的会是100页的内容。

## 示例

毕竟只是自用，感觉也不会有其他人感兴趣，就不在这方面多费时间了。

下面都是些最基础的例子，剩下的就让源代码自己去解释吧 (ゝ∀･)

### 创建客户端

``` python
client = anobbsclient.Client(
    # 客户端的 User-Agent
    user_agent='…',
    # 目标服务器的主机名，如 'adnmb3.com'
    host='…',
    # 客户端的 appid，可为 `None`
    appid='…',
    # 与单次请求相关的一些选项，发送请求时可以选择覆盖这些选项
    default_request_options={
        # 在浏览器中以名为 userhash 的 cookie 的形式呈现，登录的凭证。
        # 领饼干领的就是这个。
        # 在需要提供此值（如访问超过100页的页面）而此值空缺时
        # 会直接抛异常
        'user_cookie': '…',
        # 要怎么处理登录：
        # 'enforce':            无论如何都会在请求中包含 user_cookie。
        #                       无论操作是否需要登录，都要提供 user_cookie
        # 'when_has_cookie':    只要提供了 user_cookie，就会在请求中包含它
        # 'when_required':      当需要进行需要登录的操作时，
        #                       才会在请求中包含 user_cookie
        # 'always_no':          无论如何都不在请求中包含 user_cookie。
        #                       遇到需要登录的操作会直接抛异常
        'login_policy': 'when_required',
    },
)
```

### 获取串内容

```python
luwei_thread = client.get_thread_page(49607, page=1)

print(luwei_thread.content) #=> '这是芦苇'
```

### 获取版块内容

```python
g_board = client.get_board_page(4, page=1)

print(g_board[0].user_id) #=> 'ATM'
```

### 发布回应

```python
try:
    client.reply_thread(
        "正文内容", to_thread_id=999999999999,
        title="标题（可选）", name="名称（可选）",
        email="邮箱（可选）",
    )
except anobbsclient.ReplyException as e:
    # 服务器不接受所发回应
    print(e.raw_error, e.raw_detail)
    raise e
```

### 反向遍历串页面

Q：为何这么做？A：防止遍历途中有串被抽导致遗漏。

例子略，只是表示有这个功能 (ゝ∀･)