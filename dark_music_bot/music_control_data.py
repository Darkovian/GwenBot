from dataclasses import dataclass
from typing import Union

from discord import Message

from dark_music_bot.yt_results import YTResults


@dataclass(slots=True)
class MusicControlData:
    last_search_keyword: Union[str, None] = None
    last_search_results: Union[YTResults, None] = None
    current_control_msg_id: Union[str, int, None] = None
    current_stop_msg: Union[Message, None] = None
