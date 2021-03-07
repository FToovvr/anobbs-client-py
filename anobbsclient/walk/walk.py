
import anobbsclient


def create_walker(target, client: anobbsclient.Client, options: anobbsclient.RequestOptions = None):

    g = {}
    if options is None:
        options = {}
    current_pn = target.start_page_number
    while True:
        # 获取页面
        (current_page, usage) = target.get_page(current_pn, client, options)
        # 检查是否卡页（卡页则抛异常）
        target.check_gatekept(current_pn, current_page, client, options, g)
        # 检查是否满足终止条件
        next_pn = target.get_next_page_number(current_pn)
        should_stop = target.should_stop(current_page, next_pn, g)

        # 产出当前页
        yield (current_pn, current_page, usage)

        # 满足终止条件则终止
        if should_stop:
            break

        # 准备翻到下一页
        current_pn = next_pn
