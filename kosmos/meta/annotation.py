
from kosmos.time import get_current_time
from kosmos.time import to_utc_aware
from pydantic import AfterValidator
from typing import Annotated
from pydantic import  BeforeValidator, PlainSerializer, WithJsonSchema, Field
from bson.objectid import ObjectId
from datetime import datetime

PyObjectId = Annotated[
    ObjectId,
    # Check if input is string, convert to ObjectId. Otherwise allow existing ObjectId.
    BeforeValidator(lambda x: ObjectId(x) if isinstance(x, str) else x),
    
    # Serialize ObjectId to string (Replaces json_encoders)
    PlainSerializer(lambda x: str(x), return_type=str, when_used="json"),
    
    # Tells Pydantic: "In the JSON Schema, treat this type as a string"
    WithJsonSchema({"type": "string"}),
]

class Collapsible:
    """
    Abstract base for annotations that generate a value on demand.

    This pattern is used for fields that get a final form of their value when they are
    explicitly "collapsed".  The __call__ function should be idempotent as in f(f(x)) == f(x).
    """

    def __call__(self, v):
        raise NotImplementedError()


class CoalesceOnInsert(Collapsible):
    """
    A Collapsible that finalize a value on document creation for database insertion (not update).
    """

    def __init__(self, collapse):
        self.collapse = collapse

    def __call__(self, v):
        if v is None:
            return self.collapse()
        return v


class CoalesceOnIncr(Collapsible):
    """
    A Collapsible that provides an increment value on update.

    If the field's value is `None`, it calls the `collapse` function to generate
    a new value. This is intended for use with `$inc` operations.
    """

    def __init__(self, collapse):
        self.collapse = collapse

    def __call__(self, v):
        if v is None:
            try:
                return self.collapse()
            except TypeError:
                return None
        try:
            return self.collapse(v)
        except TypeError:
            return self.collapse()

class Refreshable:
    """
    Abstract base for annotations that refresh a value on demand.

    This pattern is used for fields that get a final form of their value when they are
    explicitly "refreshed".  The __call__ function should be idempotent as in f(f(x)) == f(x).
    """
    def __init__(self, refresh):
        self.refresh = refresh

    def __call__(self, v):
        return self.refresh(v)

class RefreshOnSet(Refreshable):
    """
    A Refreshable that provides a value on any database update (not insertion).
    This is intended when a value needs to be refreshed on every save.
    """


class NormalizeValue(Refreshable):
    """
    A Refreshable that provides a normalize value for query input.

    This is intended for use with query input where a value needs to be
    normalized based the field attribute.
    """

class NormalizeQueryInput(Refreshable):
    """
    A Refreshable that provides a normalize value for query input.

    This is intended for use with query input where a value needs to be
    normalized based the field attribute.
    """

class BeforeSetAttr(Refreshable):
    """
    An annotation to transform a value before it is set on a model field.
    This only applies when the model has been fully initialized.

    This is used within the model's `__setattr__` to apply a function to the
    value before it is assigned to the attribute.
    """

# class InitializeValue(Refreshable):
#     """
#     An annotation to transform a value before it is initialized.

#     This is used within the model's `__init__` to apply a function to the value
#     """

#: An annotated string type that automatically converts the value to uppercase.
StrUpper = Annotated[
    str,
    NormalizeValue(str.upper),
    NormalizeQueryInput(str.upper),
]

#: An annotated string type that automatically converts the value to lowercase.
StrLower = Annotated[
    str,
    NormalizeValue(str.lower),
    NormalizeQueryInput(str.lower),
]

#: A datetime field that defaults to the current UTC time on document creation.
TimeInserted = Annotated[
    datetime | None,
    AfterValidator(lambda x: to_utc_aware(x) if x is not None else None),
    CoalesceOnInsert(get_current_time),
    Field(default=None),
]

#: A datetime field that defaults to the current UTC time on document update.
TimeUpdated = Annotated[
    datetime | None,
    AfterValidator(lambda x: to_utc_aware(x) if x is not None else None),
    RefreshOnSet(lambda x: get_current_time()),
    Field(default=None),
]

TimeNorm = Annotated[
    datetime,
    NormalizeValue(to_utc_aware),
    NormalizeQueryInput(to_utc_aware),
]
