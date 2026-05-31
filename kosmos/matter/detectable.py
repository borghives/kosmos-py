from kosmos.meta.state import MetaState
from typing import Protocol, Self

class Detectable(Protocol):
    @classmethod
    def get_meta_state(cls) -> MetaState:
        ...
    @classmethod
    def from_doc(cls, doc: dict) -> Self:
        ...
        