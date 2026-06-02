import os
import pytest
from typing import Annotated
from dataclasses import dataclass
from kosmos.ether.struct import MapStruct, get_map_structs, LiminalStructure

@dataclass
class MockConfig:
    project_id: Annotated[str, MapStruct("TEST_PROJECT_ID")] = "default_id"
    api_key: Annotated[str, MapStruct("TEST_API_KEY")] = "default_key"
    no_map: str = "no_map_val"

def test_get_map_structs():
    mapping = get_map_structs(MockConfig)
    assert len(mapping) == 2
    assert "project_id" in mapping
    assert "api_key" in mapping
    assert mapping["project_id"].key == "TEST_PROJECT_ID"
    assert mapping["api_key"].key == "TEST_API_KEY"
    assert "no_map" not in mapping

def test_liminal_structure_coalesce(monkeypatch):
    monkeypatch.delenv("TEST_PROJECT_ID", raising=False)
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    
    config = MockConfig()
    struct = LiminalStructure[MockConfig](config)
    
    # Coalesce without environment variables set
    collapsed = struct.collapse()
    assert collapsed.project_id == "default_id"
    assert collapsed.api_key == "default_key"
    assert collapsed.no_map == "no_map_val"
    
    # Set env vars and check re-collapse does NOT change values (since has_coalesced is True)
    monkeypatch.setenv("TEST_PROJECT_ID", "new_project_id")
    collapsed_again = struct.collapse()
    assert collapsed_again.project_id == "default_id"
    
    # Test a fresh structure with env vars set
    config2 = MockConfig()
    struct2 = LiminalStructure[MockConfig](config2)
    monkeypatch.setenv("TEST_PROJECT_ID", "another_id")
    monkeypatch.setenv("TEST_API_KEY", "another_key")
    
    collapsed2 = struct2.collapse()
    assert collapsed2.project_id == "another_id"
    assert collapsed2.api_key == "another_key"
    assert collapsed2.no_map == "no_map_val"

