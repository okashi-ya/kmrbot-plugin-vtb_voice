import yaml
import yaml.scanner
from pathlib import Path
from nonebot.log import logger
from utils import get_config_path


def get_voice_yaml_data():
    try:
        # 每次都重新加载 即可以动态重载 性能消耗可忽略
        with open(get_config_path().joinpath("vtb_voice/voices_list.yaml"), "r", encoding="utf8") as file:
            data = yaml.safe_load(file)
    except FileNotFoundError:
        logger.error("get_sound_yaml_data fail ! File not found !")
        data = None
    except yaml.scanner.ScannerError:
        logger.error("get_sound_yaml_data fail ! Scanner Error !")
        data = None
    return data
