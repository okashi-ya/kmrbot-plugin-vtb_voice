import random
import re
import time
from typing import Union, Tuple, Any
from utils import get_config_path
from protocol_adapter.protocol_adapter import ProtocolAdapter
from protocol_adapter.adapter_type import AdapterGroupMessageEvent, AdapterPrivateMessageEvent, AdapterMessage
from nonebot import on_regex
from nonebot.matcher import Matcher
from nonebot.params import RegexGroup
from nonebot.log import logger
from utils.permission import white_list_handle
from .vtb_voice_config import get_voice_yaml_data

query_vtb_voice = on_regex(
    pattern=r"^(vtb|ｖｔｂ)( +.*)?$",
    priority=5,
)
query_vtb_voice.__doc__ = """vtb_voice"""
query_vtb_voice.__help_type__ = None

query_vtb_voice.handle()(white_list_handle("vtb_voice"))


def split_user_and_voice_name(voices_data, param) -> Tuple[bool, str, str]:
    if voices_data is None:
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
        # 判断方法：如果再user中能找到param1就是user 否则视为voice_name
        result = list(filter(lambda x: param1 in x["vtb_name"], voices_data["data"]))
        if len(result) != 0:
            return True, param1, ""
        else:
            return True, "", param1


last_query_time_data = {}


@query_vtb_voice.handle()
async def _(
        matcher: Matcher,
        event: Union[AdapterPrivateMessageEvent, AdapterGroupMessageEvent],
        params: Tuple[Any, ...] = RegexGroup(),
):
    msg_type = ProtocolAdapter.get_msg_type(event)
    msg_type_id = ProtocolAdapter.get_msg_type_id(event)
    user_id = ProtocolAdapter.get_user_id(event)
    # 如果不是纯文本消息则略过
    if ProtocolAdapter.get_msg_len(event) != 1:
        await query_vtb_voice.finish()

    # vtb_voice阻止后续事件执行
    matcher.stop_propagation()
    voices_data = get_voice_yaml_data()
    if voices_data is None:
        logger.error("query_vtb_voice voices_data is None.")
        await query_vtb_voice.finish("无法获取vtb_voice列表")
    result = split_user_and_voice_name(voices_data, params[1] or "")
    if not result[0]:
        await query_vtb_voice.finish()
    user = result[1]
    voice_name = result[2]

    # 超级用户跳过所有限流
    if event.get_user_id() not in voices_data["super_user"]:
        # 限流 一个人有时间限制 一个群也有时间限制
        if last_query_time_data.get(msg_type) is None:
            last_query_time_data[msg_type] = {}
        if last_query_time_data.get("private") is None:
            last_query_time_data["private"] = {}

        left_time = voices_data["query_interval"] - \
            (int(time.time()) - last_query_time_data["private"].get(user_id, 0))
        if left_time > 0:
            # 针对个人的
            await query_vtb_voice.finish(ProtocolAdapter.MS.reply(event) +
                                         ProtocolAdapter.MS.text(f"个人请求过于频繁：请{round(left_time, 2)}秒后再试"))
        if msg_type == "group":
            left_time = voices_data["query_interval"] - \
                (int(time.time()) - last_query_time_data[msg_type].get(msg_type_id, 0))
            if left_time > 0:
                # 针对群的
                await query_vtb_voice.finish(ProtocolAdapter.MS.reply(event) +
                                             ProtocolAdapter.MS.text(f"群组/频道请求过于频繁：请{round(left_time, 2)}秒后再试"))

    voices_list = []
    for each_data in voices_data["data"]:
        for each_voice in each_data["voices"]:
            # 检查每一个规则
            if len(user) != 0 and user not in each_data["vtb_name"]:
                # user不在列表里
                continue
            if len(voice_name) != 0 and re.match(f"^{each_voice['voice_name']}$", voice_name) is None:
                # name正则匹配失败
                continue
            if each_voice.get("white_list") is not None:
                if len(list(filter(
                        lambda x: (x.get("type", "") == msg_type and x.get("type_id", 0) == msg_type_id),
                        each_voice["white_list"]))) == 0:
                    # 有白名单但是不符合白名单规则
                    continue
            voices_list.append(each_voice)
    if len(voices_list) == 0:
        await query_vtb_voice.finish(ProtocolAdapter.MS.reply(event) +
                                     ProtocolAdapter.MS.text("未找到user和name对应的音频！"))

    if user_id not in voices_data["super_user"]:
        # 非超级用户 写入对应的CD时间
        last_query_time_data[msg_type][msg_type_id] = time.time()
        last_query_time_data["private"][user_id] = time.time()

    # 随机取一首
    dst_voice_dirs = voices_list[random.randint(0, len(voices_list) - 1)]["dirs"]
    dst_voice_dir = dst_voice_dirs[random.randint(0, len(dst_voice_dirs) - 1)]

    file_path_origin = get_config_path().joinpath(f"vtb_voice/{dst_voice_dir}")
    msg = ProtocolAdapter.MS.voice(file_path_origin)
    await query_vtb_voice.finish(msg)
