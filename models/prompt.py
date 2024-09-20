from typing import NamedTuple


class Prompt(NamedTuple):
    id: int
    user_id: int
    prompt: str
