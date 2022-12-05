from dataclasses import dataclass, field
from uuid import uuid4, UUID
from enum import Enum
from typing import Any, Dict, Union


class GwenCommands(Enum):
    Stop = 999
    Search = 0
    CreateSearchResultContent = 1
    GetStreamURL = 2
    GetVideoIDFromURL = 3
    GetVideoData = 4
    Ship = 5
    Probe = 6


@dataclass(slots=True)
class GwenCommand:
    id: UUID = field(default_factory=uuid4, init=False)
    cmd: Union[GwenCommands, None] = None
    data: Union[Dict[str, Any], None] = None
    _result: Union[Any, None] = field(default=None, init=False)

    @property
    def result(self) -> Union[Any, None]:
        return self._result

    @result.setter
    def result(self, v: Union[Any, None]) -> None:
        self.data = None
        self._result = v
