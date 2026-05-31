
from pydantic import BeforeValidator
from pydantic import BaseModel
from typing import Annotated

from pydantic import Field, PrivateAttr

from .annotation import CoalesceOnIncr


class IntCounter(BaseModel):
    """
    An integer that can be incremented atomically.

    This class is useful for creating fields that can be incremented in the
    database

    Attributes:
        _incr_value (int): The amount to increment the value by.
    """

    _incr_value: int = PrivateAttr(default=0)
    value: int = Field(default=0)

    def __init__(self, value=0, **kwargs):
        super().__init__(**kwargs)
        self.value = value

    def __int__(self) -> int:
        return self._incr_value + self.value

    def __eq__(self, other) -> bool:
        return int(self) == int(other)
        

    def get_changes(self) -> int:
        """
        Gets the amount to increment the value by.

        Returns:
            int: The amount to increment the value by.
        """
        return self._incr_value

    def __iadd__(self, incr_value: int) -> "IntCounter":
        """
        Increments the value by the given amount.

        Args:
            incr_value (int): The amount to increment the value by.

        Returns:
            IntCounter: The new value.
        """
        self._incr_value = self._incr_value + incr_value
        return self

    def collapse(self) -> "IntCounter":
        """
        Returned a new IntCounter with the increment.
        """
        return IntCounter(int(self))

def validate_int_counter(value):
    if value is None:
        return IntCounter(0)
    if isinstance(value, IntCounter):
        return value
    return IntCounter(value)

ZeroCounter = IntCounter()
#: An annotated integer type for atomic increments in a `Persistable` model.
#:
#: This type uses `IntCounter` internally to track increments and works with
#: the persistence layer to use MongoDB's `$inc` operator.
#:
#: Usage:
#:   class MyModel(Persistable):
#:       counter: IncrCounter
#:
IncrCounter = Annotated[IntCounter, 
    CoalesceOnIncr(collapse=lambda x: x.collapse()),
    BeforeValidator(lambda x: IntCounter(value=x) if isinstance(x, int) else x),
    Field(default=IntCounter())]