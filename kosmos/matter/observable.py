


from kosmos.meta.state import MetaState
from .ripple import Ripple
from typing import Protocol

class Observable(Protocol):
    @classmethod
    def get_meta_state(cls) -> MetaState:
        ...
    def collapse(self) -> Ripple:
        ...
    def decohere(self, ripple : Ripple):
        ...
