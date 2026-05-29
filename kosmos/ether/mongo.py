from kosmos.ether.struct import LiminalStructure
from kosmos.ether.struct import MapStruct
from typing import Annotated
from dataclasses import dataclass

@dataclass
class MongoConstants:
    uri          : Annotated[str, MapStruct("MONGODB_URI")] = ""
    admin_uri    : Annotated[str, MapStruct("MONGODB_ADMIN_URI")] = ""
    creator_uri  : Annotated[str, MapStruct("MONGODB_CREATOR_URI")] = ""
    database     : Annotated[str, MapStruct("MONGODB_DATABASE")] = ""
    
    @property
    def URI(self) -> str:
        return self.uri
    
    @property
    def AdminURI(self) -> str:
        return self.admin_uri
    
    @property
    def CreatorURI(self) -> str:
        return self.creator_uri
    
    @property
    def Database(self) -> str:
        return self.database

    @staticmethod
    def Collapse() -> 'MongoConstants':
        return constants.Collapse()

constants = LiminalStructure[MongoConstants](MongoConstants())