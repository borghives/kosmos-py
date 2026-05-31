from typing import get_type_hints, get_origin, get_args, Annotated, Dict
from dataclasses import dataclass
import os

class MapStruct:
    def __init__(self, key: str, permeate: bool = False):
        self.key = key
        self.permeate = permeate

def get_map_structs(cls) -> Dict[str, MapStruct]:
    type_hints = get_type_hints(cls, include_extras=True)
    map_structs = {}
    for field_name in type_hints:
        hint = type_hints[field_name]
        if get_origin(hint) is Annotated:
            args = get_args(hint)
            map_struct = next((arg for arg in args[1:] if isinstance(arg, MapStruct)), None)
            if map_struct:
                map_structs[field_name] = map_struct
    return map_structs

@dataclass
class LiminalStructure[T]:
    constants: T
    has_coalesced: bool = False
    
    def coalesce(self):
        for key, map_struct in get_map_structs(type(self.constants)).items():
            if os.getenv(map_struct.key) is not None:
                setattr(self.constants, key, os.getenv(map_struct.key))
    
    def collapse(self) -> T:
        if not self.has_coalesced:
            self.coalesce()
            self.has_coalesced = True
        return self.constants


        