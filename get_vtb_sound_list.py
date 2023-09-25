from nonebot import on_command
from nonebot.rule import to_me
from typing import Union
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
import configs.vtb_sound
from plugins.common_plugins_function import white_list_handle
from .painter.vtb_sound_list_painter import VtbSoundListPainter

get_vtb_sound_list = on_command(
    "vtb_help",
    rule=to_me(),
    priority=5,
)
get_vtb_sound_list.__doc__ = """vtb_help"""
get_vtb_sound_list.__help_type__ = None

get_vtb_sound_list.handle()(white_list_handle("vtb_sound"))


@get_vtb_sound_list.handle()
async def _(
        event: Union[PrivateMessageEvent, GroupMessageEvent],
):
    event_type = event.message_type
    if isinstance(event, PrivateMessageEvent):
        type_id = event.user_id
    elif isinstance(event, GroupMessageEvent):
        type_id = event.group_id
    else:
        type_id = 0
        await get_vtb_sound_list.finish()

    pic = MessageSegment.image(VtbSoundListPainter.generate_vtb_sound_list_pic(
        configs.vtb_sound.get_sound_yaml_data(), event_type, type_id))
    await get_vtb_sound_list.finish(pic)
