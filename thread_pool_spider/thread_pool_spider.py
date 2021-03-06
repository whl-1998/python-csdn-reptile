from datetime import datetime
from urllib import parse
import re
import ast

import requests
from scrapy import Selector

from models import *

DOMAIN = "https://bbs.csdn.net/"  # 根路径
DYNAMIC_JS = "https://bbs.csdn.net/dynamic_js/left_menu.js?csdn"  # 包含了帖子版块json信息的js文件
HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                      ' (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'
}


def get_forum_nodes_from_json():
    """
    通过json文本获取到帖子版块结点
    :return: 包含帖子版块信息的list
    """
    left_menu_text = requests.get(DYNAMIC_JS).text  # 获取到left_menu_js的纯文本
    nodes_str_match = re.search("forumNodes: (.*])", left_menu_text)
    if nodes_str_match:
        nodes_str = nodes_str_match.group(1).replace('null', 'None')
        nodes_list = ast.literal_eval(nodes_str)  # 将nodes_str转换为列表格式
        return nodes_list
    return []  # 如果爬取失败, 那么返回空列表


def parse_nodes_list(forum_nodes: list):
    """
    将json列表中的子url提取到新的列表中
    """
    def recur(_forum_nodes: list, forum_urls: list):
        for item in _forum_nodes:
            if "children" in item:  # 如果包含子版块, 那么递归到子版块执行
                recur(item['children'], forum_urls)
            else:  # 如果不包含子版块, 那么在返回列表中添加url
                forum_urls.append(item['url'])
        return forum_urls
    return recur(forum_nodes, [])


def get_last_urls(unparsed_url_list: list):
    """
    获取最终的url列表
    """
    result_urls = []
    for unparsed_url in unparsed_url_list:
        result_urls.append(parse.urljoin(DOMAIN, unparsed_url))  # 未结贴的帖子
        result_urls.append(parse.urljoin(DOMAIN, unparsed_url + "/recommend"))  # 推荐帖子
        result_urls.append(parse.urljoin(DOMAIN, unparsed_url + "/closed"))  # 结贴的帖子
    return result_urls


def get_topic_info(forum_url: str):
    """
    爬取帖子相关的信息：比如帖子标题、作者、发布时间、最后一个回帖的nickname等信息
    """
    print("开始爬取版块url为：{} 的帖子相关信息".format(forum_url))
    sel = Selector(text=requests.get(forum_url).text)
    all_trs = sel.xpath(".//table[@class='forums_tab_table']//tbody//tr")  # 获取所有的帖子列表结点
    for tr in all_trs:  # 遍历这些tr结点, 提取每一个的帖子相关的信息
        topic = Topic()
        parsed_title = tr.xpath(".//td[3]/a/@href").extract()[-1]
        # 如果能够解析到帖子相关的信息, 那么先进入该帖子, 爬取帖子的内容, 回帖内容
        if parsed_title:
            topic_url = parse.urljoin(DOMAIN, parsed_title)
            topic.topic_id = topic_url.split('/')[-1]
            get_topics_detailed_info(topic_url, topic)  # 爬取帖子详细内容
            executor.submit(get_answer_info, topic_url)  # 爬取回帖内容
        # 若未能成功解析, 那么说明该板块不存在帖子, 直接return掉该方法
        elif "没有帖子！" in tr.xpath(".//td/text()").extract()[0].strip():
            print(forum_url.split('/')[-1] + ' 版块没有帖子')
            return
        else:
            print("非正常处理逻辑, bug+++++")
        topic.status = tr.xpath(".//td[1]/span/text()").extract()[0]
        topic.score = int(tr.xpath(".//td[2]/em/text()").extract()[0])
        topic.topic_title = tr.xpath(".//td[3]/a/text()").extract()[-1]
        author_url = tr.xpath(".//td[4]/a/@href").extract()[0]
        executor.submit(get_authors_info, author_url)  # 爬取作者信息
        topic.author_uuid = author_url.split('/')[-1]
        topic.create_time = datetime.strptime(tr.xpath(".//td[4]/em/text()").extract()[0], '%Y-%m-%d %H:%M')
        answer_info = tr.xpath(".//td[5]/span/text()").extract()[0]
        topic.answer_nums = int(answer_info.split('/')[0])
        topic.click_nums = int(answer_info.split('/')[1])
        latest_answerer_url = tr.xpath(".//td[6]/a/@href").extract()[0]
        topic.latest_answerer_uuid = latest_answerer_url.split('/')[-1]
        topic.update_time = datetime.strptime(tr.xpath(".//td[6]/em/text()").extract()[0], '%Y-%m-%d %H:%M')
        if Topic.select().where(Topic.topic_id == topic.topic_id):
            topic.save()  # 如果数据库表中有topic_id相同的记录, 那么更新数据库记录
        else:
            topic.save(force_insert=True)  # 不然就新增
    next_page = sel.xpath("//a[@class='pageliststy next_page']/@href").extract()
    if next_page and "page" in next_page[-1]:  # 如果有下一页的内容, 那么继续爬取下一页的信息
        if int(re.search(r"(\d+)", next_page[-1]).group()) <= 3:  # 只爬取最多三页的帖子
            executor.submit(get_topic_info, parse.urljoin(DOMAIN, next_page[-1]))
    else:  # 如果没有, 结束该方法
        return


def get_topics_detailed_info(topic_url: str, topic: Topic):
    """
    获取帖子列表的详细信息(比如帖子内容, 回帖内容, 点赞数, 结帖率等
    """
    sel = Selector(text=requests.get(topic_url).text)
    all_divs = sel.xpath("//div[starts-with(@id, 'post-')]")
    topic_item = all_divs[0]  # 帖子的内容, 发帖者相关的内容在第一个div中
    topic_content = ""
    for item in topic_item.xpath(".//div[@class='post_body post_body_min_h']/text()").extract():
        topic_content += item.strip()
    topic.topic_content = topic_content
    topic.praised_nums = int(topic_item.xpath(".//label[@class='red_praise digg']//em/text()").extract()[0])
    topic.end_percentage = re.search(r"(\d+)%",
                                     topic_item.xpath(".//div[@class='close_topic']/text()").extract()[0]).group()


def get_answer_info(topic_url: str):
    """
    爬取回帖的内容
    从第一页开始, 第一个content是属于topic的, 这就意味着, 如果是第一页, 我们要从第二个content开始获取
    """
    print("开始爬取帖子url为：{} 的回帖信息".format(topic_url))
    sel = Selector(text=requests.get(topic_url).text)
    all_divs = sel.xpath("//div[starts-with(@id, 'post-')]")
    if "page" not in topic_url:  # 如果是第一页, 判断是否有回帖内容
        if len(all_divs) <= 1:
            print(topic_url + '这个帖子还没有回帖')
            return
        else:
            all_divs = all_divs[1:]
    else:
        if len(all_divs) <= 0:
            print(topic_url + '在这一页中没有回帖内容')
            return
    for i in range(len(all_divs)):
        answer = Answer()
        answer.answer_id = int(all_divs[i].xpath("//div[@class='bbs_detail_wrap']//div/@data-post-id").extract()[i])
        answer.topic_id = int(re.search(r'(\d+)', topic_url).group())
        author_url = all_divs[i].xpath(".//div[@class='nick_name']//a[1]/@href").extract()[0]
        answer.author_uuid = author_url.split('/')[-1]
        answer.create_time = datetime.strptime(all_divs[i].xpath(".//label[@class='date_time']/text()").extract()[0], "%Y-%m-%d %H:%M:%S")
        answer_content = ""
        for item in all_divs[i].xpath(".//div[@class='post_body post_body_min_h']/text()").extract():
            answer_content += item.strip()
        answer.answer_content = answer_content
        answer.praised_nums = all_divs[i].xpath(".//label[@class='red_praise digg']//em/text()").extract()[0]
        executor.submit(get_authors_info, author_url)
        if Answer.select().where(Answer.answer_id == answer.answer_id):
            answer.save()
        else:
            answer.save(force_insert=True)
    next_page = sel.xpath("//a[@class='pageliststy next_page']/@href").extract()
    if next_page and "page" in next_page[-1]:
        if int(re.search(r"page=(\d+)", next_page[-1]).group(1)) <= 3:
            executor.submit(get_answer_info, parse.urljoin(DOMAIN, next_page[-1]))
    else:
        return


def get_authors_info(author_url):
    """
    获取发帖, 回帖作者的个人信息
    """
    uuid = author_url.split('/')[-1]
    author = Author()
    author.author_uuid = uuid
    print("开始爬取用户url为：{} 的用户信息".format("https://me.csdn.net/" + uuid))
    sel = Selector(text=requests.get("https://me.csdn.net/" + uuid, headers=HEADERS).text)
    name = ""
    for item in sel.xpath("//div[@class='lt_title']/text()").extract():
        name += item.strip()
    author.name = name
    author.original_blog_nums = int(sel.xpath("//div[@class='me_chanel_det_item access']//span/text()").extract()[0].strip())
    author.desc = sel.xpath("//div[@class='description clearfix']//p/text()").extract()[0].strip()
    author.rank = sel.xpath("//div[@class='me_chanel_det_item access']//span/text()").extract()[1].strip()
    author.follower_nums = sel.xpath("//div[@class='fans']//a//span/text()").extract()[0].strip()
    author.following_nums = sel.xpath("//div[@class='att']//a//span/text()").extract()[0].strip()

    sel = Selector(text=requests.get("https://me.csdn.net/bbs/" + uuid, headers=HEADERS).text)
    author.post_topic_nums = sel.xpath("//div[@class='me_chanel_det_item access']//span/text()").extract()[0].strip()
    author.answer_topic_nums = sel.xpath("//div[@class='me_chanel_det_item access']//span/text()").extract()[1].strip()
    author.end_topic_percentage = sel.xpath("//div[@class='me_chanel_det_item access']//span/text()").extract()[2].strip()

    sel = Selector(text=requests.get("https://me.csdn.net/bbs/ask/" + uuid, headers=HEADERS).text)
    author.post_question_nums = sel.xpath("//div[@class='me_chanel_det_item access']//span/text()").extract()[0].strip()
    author.answer_question_nums = sel.xpath("//div[@class='me_chanel_det_item access']//span/text()").extract()[1].strip()

    if Author.select().where(Author.author_uuid == author.author_uuid):
        author.save()
    else:
        author.save(force_insert=True)


if __name__ == '__main__':
    from concurrent.futures.thread import ThreadPoolExecutor
    executor = ThreadPoolExecutor(max_workers=8)
    last_urls = get_last_urls(parse_nodes_list(get_forum_nodes_from_json()))
    for url in last_urls:
        executor.submit(get_topic_info, url)
