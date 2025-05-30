from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp

import os

import requests
from bs4 import BeautifulSoup
import jsonpath
import aiohttp

r18switch = 0
picinfo = 0
picjson = {
    "uid": "",
    "title": "",
    "author": "",
    "tags": [],
    "urls": ""
}

# ALLOWED_GROUPS = { "" }

# --------------------------------
# Pic Func
def get_pic(ustr, picmode):
    global r18switch, picinfo, picjson
    print("R18 switch is: %d" % r18switch)
    gurl = ""
    if picmode == 0:
        gurl = 'https://api.lolicon.app/setu/v2?r18=' + str(r18switch)
    elif picmode == 1:
        ustr_len = len(ustr)
        cstr = ""
        pcount = 0
        ocount = 0
        i = 0
        while i < ustr_len:
            if ustr[i] == '-':
                ocount += 1
                if ocount <= 20:
                    cstr = cstr + '|'
                else:
                    break
            elif ustr[i] == '+':
                pcount += 1
                if pcount <= 3:
                    cstr = cstr + "&tag="
                    ocount = 0
                else:
                    break
            else:
                cstr = cstr + ustr[i]
            i += 1
        gurl = 'https://api.lolicon.app/setu/v2?r18=' + str(r18switch) + '&tag=' + cstr
    elif picmode == 2:
        gurl = 'https://api.lolicon.app/setu/v2?r18=' + str(r18switch) + '&uid=' + ustr
    print(gurl)
    res1 = requests.get(gurl)
    pic1 = res1.json().get('data')
    pic2 = jsonpath.jsonpath(pic1, '$..urls..original')
    url = ""
    if pic2:
        url = pic2[0]
    else:
        return "0"
    print(url)
    picinfo = 1
    picjson["uid"] = jsonpath.jsonpath(pic1, '$..uid')
    picjson["title"] = jsonpath.jsonpath(pic1, '$..title')
    picjson["author"] = jsonpath.jsonpath(pic1, '$..author')
    picjson["tags"] = jsonpath.jsonpath(pic1, '$..tags')
    picjson["urls"] = url
    return url

# --------------------------------
# Pixiv Ranking Func
def get_prank(rmode, index):
    global headers_str
    pixiv_rank_url = 'https://www.pixiv.net/ranking.php'
    pixiv_ua = {
        'User-Agent': headers_str
    }
    pixiv_args = {
        'content': 'illust'
    }
    args = pixiv_args.copy()
    if rmode == 0:
        args['mode'] = 'daily'
    elif rmode == 1:
        args['mode'] = 'weekly'
    elif rmode == 2:
        args['mode'] = 'monthly'
    pixiv_request = requests.get(pixiv_rank_url, params=args, headers=pixiv_ua)
    pixiv_content = pixiv_request.text
    pixiv_soup = BeautifulSoup(pixiv_content, 'html.parser')
    all_res = pixiv_soup.find_all('div', class_="ranking-image-item")
    img_url = all_res[index - 1].find('img')['data-src']
    img_url_i = img_url.find('/img-master/img/') + len('/img-master/img/')
    img_url_j = img_url.find('_master')
    url = "https://i.pixiv.re/img-original/img/" + img_url[img_url_i:img_url_j] + ".jpg"
    print(url)
    return url

@register("pic", "Evoke", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("info")
    async def info(self, event: AstrMessageEvent):
        if event.get_group_id() and event.get_group_id() not in ALLOWED_GROUPS:
            yield event.plain_result("该群聊不可使用该功能")
            return

        global picinfo, picjson
        if picinfo == 0:
            yield event.plain_result("当前没有返回图片")
        elif picinfo == 1:
            pic_msg = "uid：" + str(picjson["uid"][0]) + "\n"
            pic_msg += "标题：" + str(picjson["title"][0]) + "\n"
            pic_msg += "作者：" + str(picjson["author"][0]) + "\n"
            tags = ""
            for index in range(0, len(picjson["tags"][0]) - 1):
                tags += str(picjson["tags"][0][index]) + "， "
            tags += str(picjson["tags"][0][len(picjson["tags"][0]) - 1])
            pic_msg += "tags：" + tags + "\n"
            pic_msg += "url：" + str(picjson["urls"])
            yield event.plain_result(pic_msg)
        else:
            yield event.plain_result("url：" + str(picjson["urls"]))

    @filter.command("pic")
    async def pic(self, event: AstrMessageEvent):
        # if event.get_group_id() and event.get_group_id() not in ALLOWED_GROUPS:
        #     yield event.plain_result("该群聊不可使用该功能")
        #     return

        chat_id = event.get_sender_id()
        url = get_pic("", 0)
        if url == "0":
            chain = [
                Comp.At(qq=chat_id), # At 消息发送者
                Comp.Plain("请验证请求内容是否正确"),
            ]
            yield event.chain_result(chain)
        else:
            filename = os.path.basename(url)  # e.g. "68057997_p0.jpg"
            tmp_path = os.path.join('/tmp', filename)
            tmp_path = os.path.join(os.getcwd(), tmp_path)
            abs_path = os.path.abspath(tmp_path).replace('\\', '/')

            if not os.path.exists(tmp_path):
                async with aiohttp.ClientSession() as sess:
                    resp = await sess.get(url)
                    if resp.status == 404:
                        chain = [
                            Comp.At(qq=chat_id), # At 消息发送者
                            Comp.Plain("无法返回图片内容(404)"),
                        ]
                        yield event.chain_result(chain)
                        return
                    elif resp.status != 200:
                        chain = [
                            Comp.At(qq=chat_id), # At 消息发送者
                            Comp.Plain(f"⚠️ 无法下载图片({resp.status})"),
                        ]
                        yield event.chain_result(chain)
                        return
                    # resp.raise_for_status()
                    data = await resp.read()
                with open(tmp_path, 'wb') as f:
                    f.write(data)

            chain = [
                Comp.Image.fromFileSystem(abs_path), # 从 URL 发送图片
            ]
            yield event.chain_result(chain)

    @filter.command("tag")
    async def tag(self, event: AstrMessageEvent):
        # if event.get_group_id() and event.get_group_id() not in ALLOWED_GROUPS:
        #     yield event.plain_result("该群聊不可使用该功能")
        #     return

        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)

        chat_id = event.get_sender_id()
        if len(message_str) >= 5:
            label = message_str[:4]
            if label == "tag ":
                param = message_str[4:]
                if len(param) > 0:
                    chat_id = event.get_sender_id()
                    url = get_pic(param, 1)
                    if url == "0":
                        chain = [
                            Comp.At(qq=chat_id), # At 消息发送者
                            Comp.Plain("请验证tag内容是否正确"),
                        ]
                        yield event.chain_result(chain)
                    else:
                        filename = os.path.basename(url)  # e.g. "68057997_p0.jpg"
                        tmp_path = os.path.join('/tmp', filename)
                        tmp_path = os.path.join(os.getcwd(), tmp_path)
                        abs_path = os.path.abspath(tmp_path).replace('\\', '/')

                        if not os.path.exists(tmp_path):
                            async with aiohttp.ClientSession() as sess:
                                resp = await sess.get(url)
                                if resp.status == 404:
                                    chain = [
                                        Comp.At(qq=chat_id), # At 消息发送者
                                        Comp.Plain("无法返回图片内容(404)"),
                                    ]
                                    yield event.chain_result(chain)
                                    return
                                elif resp.status != 200:
                                    chain = [
                                        Comp.At(qq=chat_id), # At 消息发送者
                                        Comp.Plain(f"⚠️ 无法下载图片({resp.status})"),
                                    ]
                                    yield event.chain_result(chain)
                                    return
                                # resp.raise_for_status()
                                data = await resp.read()
                            with open(tmp_path, 'wb') as f:
                                f.write(data)

                        chain = [
                            Comp.Image.fromFileSystem(abs_path), # 从 URL 发送图片
                        ]
                        yield event.chain_result(chain)
                else:
                    chain = [
                        Comp.At(qq=chat_id), # At 消息发送者
                        Comp.Plain("请输入tag"),
                    ]
                    yield event.chain_result(chain)
            else:
                chain = [
                    Comp.At(qq=chat_id), # At 消息发送者
                    Comp.Plain("请输入正确的tag"),
                ]
                yield event.chain_result(chain)
        else:
            chain = [
                Comp.At(qq=chat_id), # At 消息发送者
                Comp.Plain("请输入正确的tag"),
            ]
            yield event.chain_result(chain)

    @filter.command("uid")
    async def uid(self, event: AstrMessageEvent):
        # if event.get_group_id() and event.get_group_id() not in ALLOWED_GROUPS:
        #     yield event.plain_result("该群聊不可使用该功能")
        #     return

        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)

        chat_id = event.get_sender_id()
        if len(message_str) >= 5:
            label = message_str[:4]
            if label == "uid ":
                param = message_str[4:]
                if len(param) > 0:
                    chat_id = event.get_sender_id()
                    url = get_pic(param, 2)
                    if url == "0":
                        chain = [
                            Comp.At(qq=chat_id), # At 消息发送者
                            Comp.Plain("请验证uid内容是否正确"),
                        ]
                        yield event.chain_result(chain)
                    else:
                        filename = os.path.basename(url)  # e.g. "68057997_p0.jpg"
                        tmp_path = os.path.join('/tmp', filename)
                        tmp_path = os.path.join(os.getcwd(), tmp_path)
                        abs_path = os.path.abspath(tmp_path).replace('\\', '/')

                        if not os.path.exists(tmp_path):
                            async with aiohttp.ClientSession() as sess:
                                resp = await sess.get(url)
                                if resp.status == 404:
                                    chain = [
                                        Comp.At(qq=chat_id), # At 消息发送者
                                        Comp.Plain("无法返回图片内容(404)"),
                                    ]
                                    yield event.chain_result(chain)
                                    return
                                elif resp.status != 200:
                                    chain = [
                                        Comp.At(qq=chat_id), # At 消息发送者
                                        Comp.Plain(f"⚠️ 无法下载图片({resp.status})"),
                                    ]
                                    yield event.chain_result(chain)
                                    return
                                # resp.raise_for_status()
                                data = await resp.read()
                            with open(tmp_path, 'wb') as f:
                                f.write(data)

                        chain = [
                            Comp.Image.fromFileSystem(abs_path), # 从 URL 发送图片
                        ]
                        yield event.chain_result(chain)
                else:
                    chain = [
                        Comp.At(qq=chat_id), # At 消息发送者
                        Comp.Plain("请输入uid"),
                    ]
                    yield event.chain_result(chain)
            else:
                chain = [
                    Comp.At(qq=chat_id), # At 消息发送者
                    Comp.Plain("请输入正确的uid"),
                ]
                yield event.chain_result(chain)
        else:
            chain = [
                Comp.At(qq=chat_id), # At 消息发送者
                Comp.Plain("请输入正确的uid"),
            ]
            yield event.chain_result(chain)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
