import os
import random
import re
import time
from typing import Union, Tuple, Any
from pathlib import Path
from nonebot.adapters.onebot.v11.message import Message
from nonebot import on_regex
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, RegexGroup
from nonebot.log import logger
from plugins.common_plugins_function import white_list_handle
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot_plugin_guild_patch import GuildMessageEvent
import configs.vtb_sound

query_vtb_sound = on_regex(
    pattern=r"^(vtb|ｖｔｂ)( +.*)?$",
    priority=5,
)
query_vtb_sound.__doc__ = """vtb_sound"""
query_vtb_sound.__help_type__ = None

query_vtb_sound.handle()(white_list_handle("vtb_sound"))


async def handle_get_param(
    matcher: Matcher,
    command_arg: Message = CommandArg(),
):
    param = command_arg.extract_plain_text()
    matcher.set_arg("param", Message(param))
query_vtb_sound.handle()(handle_get_param)


def split_user_and_sound_name(sounds_data, param) -> Tuple[bool, str, str]:
    if sounds_data is None:
        return False, "", ""
    data = param.strip().split(' ')
    param1 = ""
    param2 = ""
    if len(data) > 0:
        param1 = data[0]
    if len(data) > 1:
        param2 = data[1]
    if len(data) > 2:
        return False, "", ""

    if len(param1) == 0:
        # 无user和name约束
        return True, "", ""
    # 判断param2是否存在 如果存在 就是 user+name格式
    # 否则要判断param1是user还是name
    if len(param2) != 0:
        return True, param1, param2
    else:
        # 判断方法：如果再user中能找到param1就是user 否则视为sound_name
        result = list(filter(lambda x: param1 in x["vtb_name"], sounds_data["data"]))
        if len(result) != 0:
            return True, param1, ""
        else:
            return True, "", param1


last_query_time_data = {}


@query_vtb_sound.handle()
async def _(
        matcher: Matcher,
        event: Union[PrivateMessageEvent, GroupMessageEvent],
        params: Tuple[Any, ...] = RegexGroup(),
):
    if isinstance(event, PrivateMessageEvent):
        type_id = event.user_id
    elif isinstance(event, GroupMessageEvent):
        type_id = event.group_id
    else:
        type_id = 0
        await query_vtb_sound.finish()
    # 如果不是纯文本消息则略过
    if len(event.message) != 1:
        await query_vtb_sound.finish()

    # vtb_sound阻止后续事件执行
    matcher.stop_propagation()
    sounds_data = configs.vtb_sound.get_sound_yaml_data()
    if sounds_data is None:
        logger.error("query_vtb_sound sounds_data is None.")
        await query_vtb_sound.finish("无法获取vtb_sound列表")
    result = split_user_and_sound_name(sounds_data, params[1] or "")
    if not result[0]:
        await query_vtb_sound.finish()
    user = result[1]
    sound_name = result[2]

    if isinstance(event, PrivateMessageEvent):
        event_id = event.user_id
    elif isinstance(event, GroupMessageEvent):
        event_id = event.group_id
    elif isinstance(event, GuildMessageEvent):
        event_id = event.guild_id
    else:
        event_id = 0
    # 超级用户跳过所有限流
    if event.user_id not in sounds_data["super_user"]:
        # 限流 一个人有时间限制 一个群也有时间限制
        if last_query_time_data.get(event.message_type) is None:
            last_query_time_data[event.message_type] = {}
        if last_query_time_data.get("private") is None:
            last_query_time_data["private"] = {}
        if event.message_type != "private":
            left_time = sounds_data["query_interval"] - \
                        (int(time.time()) - last_query_time_data["private"].get(event.user_id, 0))
            if left_time > 0:
                # 针对个人的
                await query_vtb_sound.finish(Message(f"[CQ:reply,id={event.message_id}]") +
                                             Message(f"个人请求过于频繁：请{round(left_time, 2)}秒后再试"))

        left_time = sounds_data["query_interval"] - \
            (int(time.time()) - last_query_time_data[event.message_type].get(event_id, 0))
        if left_time > 0:
            # 针对群的
            await query_vtb_sound.finish(Message(f"[CQ:reply,id={event.message_id}]") +
                                         Message(f"群组/频道请求过于频繁：请{round(left_time, 2)}秒后再试"))

    sounds_list = []
    for each_data in sounds_data["data"]:
        for each_sound in each_data["sounds"]:
            # 检查每一个规则
            if len(user) != 0 and user not in each_data["vtb_name"]:
                # user不在列表里
                continue
            if len(sound_name) != 0 and re.match(f"^{each_sound['sound_name']}$", sound_name) is None:
                # name正则匹配失败
                continue
            if each_sound.get("white_list") is not None:
                if len(list(filter(
                        lambda x: (x.get("type", "") == event.message_type and x.get("type_id", 0) == type_id),
                        each_sound["white_list"]))) == 0:
                    # 有白名单但是不符合白名单规则
                    continue
            sounds_list.append(each_sound)
    if len(sounds_list) == 0:
        await query_vtb_sound.finish(Message(f"[CQ:reply,id={event.message_id}]") + Message("未找到user和name对应的音频！"))

    if event.user_id not in sounds_data["super_user"]:
        # 非超级用户 写入对应的CD时间
        last_query_time_data[event.message_type][event_id] = time.time()
        last_query_time_data["private"][event.user_id] = time.time()

    # 随机取一首
    dst_sound_dirs = sounds_list[random.randint(0, len(sounds_list) - 1)]["dirs"]
    dst_sound_dir = dst_sound_dirs[random.randint(0, len(dst_sound_dirs) - 1)]
    file_path = Path(configs.get_config_path()).joinpath(f"vtb_sound/{dst_sound_dir}")
    msg = Message(f"[CQ:record,file=file:///{file_path}]")
    await query_vtb_sound.finish(msg)
