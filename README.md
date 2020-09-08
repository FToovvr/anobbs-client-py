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

luwei_thread = client.get_thread(49607, page=1)

print(luwei_thread.body["content"])
#=> 这是芦苇
```

