from .struct import LiminalStructure, MapStruct
from typing import Annotated
from dataclasses import dataclass

@dataclass
class UniversalConstants:
    project_id: Annotated[str, MapStruct("PROJECT_ID")] = ""
    proxy_address: Annotated[str, MapStruct("ALL_PROXY")] = ""
    test_mode: Annotated[str, MapStruct("TEST_MODE")] = ""
    
    @property
    def is_test_mode(self) -> bool:
        return self.test_mode == "True"

    @staticmethod
    def collapse() -> 'UniversalConstants':
        return universal_constants.collapse()
    
universal_constants = LiminalStructure[UniversalConstants](UniversalConstants())

    

