from nonebot import on_command
from nonebot.rule import to_me
from typing import Union
from protocol_adapter.protocol_adapter import ProtocolAdapter
from protocol_adapter.adapter_type import AdapterMessage, AdapterGroupMessageEvent, AdapterPrivateMessageEvent
import configs.vtb_voice
from utils.permission import white_list_handle
from .painter.vtb_voice_list_painter import VtbVoiceListPainter

get_vtb_voice_list = on_command(
    "vtb_help",
    rule=to_me(),
    priority=5,
)
get_vtb_voice_list.__doc__ = """vtb_help"""
get_vtb_voice_list.__help_type__ = None

get_vtb_voice_list.handle()(white_list_handle("vtb_voice"))


@get_vtb_voice_list.handle()
async def _(
        event: Union[AdapterGroupMessageEvent, AdapterPrivateMessageEvent],
):
    msg_type = ProtocolAdapter.get_msg_type(event)
    msg_type_id = ProtocolAdapter.get_msg_type_id(event)
    pic = ProtocolAdapter.MS.image(VtbVoiceListPainter.generate_vtb_voice_list_pic(
        configs.vtb_voice.get_voice_yaml_data(), msg_type, msg_type_id))
    await get_vtb_voice_list.finish(pic)
