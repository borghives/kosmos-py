from kosmos.ether.struct import LiminalStructure, MapStruct
from typing import Annotated
from dataclasses import dataclass

@dataclass
class UniversalConstants:
    project_id: Annotated[str, MapStruct("PROJECT_ID", permeate=True)] = ""
    proxy_address: Annotated[str, MapStruct("ALL_PROXY", permeate=True)] = ""
    
    @staticmethod
    def collapse() -> 'UniversalConstants':
        return universal_constants.collapse()
    
universal_constants = LiminalStructure[UniversalConstants](UniversalConstants())

    

