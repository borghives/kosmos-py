from kosmos.ether.struct import LiminalStructure, MapStruct
from typing import Annotated
from dataclasses import dataclass

@dataclass
class MongoConstants:
    uri: Annotated[str, MapStruct("MONGODB_URI")] = ""
    admin_uri: Annotated[str, MapStruct("MONGODB_ADMIN_URI")] = ""
    creator_uri: Annotated[str, MapStruct("MONGODB_CREATOR_URI")] = ""
    database: Annotated[str, MapStruct("MONGODB_DATABASE")] = ""

    @staticmethod
    def collapse() -> 'MongoConstants':
        return constants.collapse()

constants = LiminalStructure[MongoConstants](MongoConstants())