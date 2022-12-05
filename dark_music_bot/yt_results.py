from __future__ import annotations
from dataclasses import dataclass, field
from typing import Union, Dict


@dataclass(slots=True)
class YTResultItem:
    channel: Union[str, None] = None
    title: Union[str, None] = None
    video_id: Union[str, None] = None
    length: Union[str, None] = field(default=None, init=False)
    img: Union[str, None] = None
    img_data: Union[bytes, None] = field(default=None, init=False)


@dataclass(slots=True)
class YTResults:
    results: Dict[int, YTResultItem] = field(default_factory=dict, init=False)
    prev_page_token: Union[str, None] = field(default=None, init=False)
    next_page_token: Union[str, None] = field(default=None, init=False)
