from kosmos.ether.struct import LiminalStructure
from kosmos.ether.struct import MapStruct
from typing import  Annotated
from dataclasses import dataclass



@dataclass
class UniversalConstants:
    project_id: Annotated[str, MapStruct("PROJECT_ID", permeate=True)] = ""
    proxy_address: Annotated[str, MapStruct("ALL_PROXY", permeate=True)] = ""
    
    @property
    def ProjectID(self) -> str:
        return self.project_id
        
    @property
    def ProxyAddress(self) -> str:
        return self.proxy_address
    
    @staticmethod
    def Collapse() -> 'UniversalConstants':
        return universal_constants.Collapse()
    
universal_constants = LiminalStructure[UniversalConstants](constants=UniversalConstants())
    

