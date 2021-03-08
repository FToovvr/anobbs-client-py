import anobbsclient

from .walktarget import WalkTargetInterface


def create_walker(target: WalkTargetInterface, client: anobbsclient.Client, options: anobbsclient.RequestOptions = None):

    g = target.create_state()
    if options is None:
        options = {}
    current_pn = target.start_page_number
    while True:
        # 获取页面
        (current_page, usage) = target.get_page(current_pn, client, options)
        # 检查是否卡页（卡页则抛异常）
        target.check_gatekept(current_pn, current_page, client, options, g)
        # TODO: 分离出 preprocess 进行如剪裁回复之类的操作？
        # 检查是否满足终止条件
        should_stop = target.should_stop(
            current_page, current_pn, client, options, g)

        # 产出当前页
        yield (current_pn, current_page, usage)

        # 满足终止条件则终止
        if should_stop:
            break

        # 翻到下一页
        current_pn = target.get_next_page_number(current_pn, g)
