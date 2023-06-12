import json
from typing import TypedDict

__all__ = ("CONFIG",)


class TConfig(TypedDict):
    prefix: str
    owner_ids: list[int]
    guild: int


with open("config.json", "rb") as config_f:
    CONFIG: TConfig = json.load(config_f)
