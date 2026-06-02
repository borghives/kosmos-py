from typing import Type

from kosmos.meta.model import Model
from kosmos.mongo.detector import MongoDetector

def detect[T: Model](objtype: Type[T]):
    if not hasattr(objtype, "get_meta_state"):
        raise TypeError(f"Class {objtype.__name__} has no state meta information for detection.")
    
    meta = objtype.get_meta_state()
    return MongoDetector[T](meta, objtype)