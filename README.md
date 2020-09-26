# AnoBBS API Wrapper

AnoBBS API 的 Python 简易封装库。

## 示例

### 获取串内容

```python
from anobbsclient import Client

import os

client = Client(
    user_agent=os.environ["MY_ADNMB_CLIENT_USER_AGENT"],
    host="adnmb2.com",
)

luwei_thread = client.get_thread_page(49607, page=1)

print(luwei_thread.content)
#=> 这是芦苇
```

## 术语

* 「卡99」
    * 访问串的100页之后的页面，响应的会是100页的内容。