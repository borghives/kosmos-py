from kosmos.matter.persistable import Persistable
import pytest
from unittest.mock import MagicMock, patch
from kosmos.meta.model import Model
from kosmos.meta.state import declare_persist_db
from kosmos.mongo.recorder import MongoRecorder
from kosmos.mongo.dataverse import Dataverse
from kosmos.mongo.client import DbClientFactory, PurposeAffinity

@declare_persist_db(collection_name="test_recordings", db_name="test_db")
class DummyModel(Persistable):
    name: str

@patch("kosmos.mongo.client.MongoClient")
@patch("kosmos.mongo.summon_mongo")
def test_recorder_creation(mock_summon_mongo, mock_mongo_client):
    # Mock MongoClient to avoid real database connection attempts
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    
    # Mock summon_mongo to return our test-configured Dataverse
    mock_dataverse = Dataverse(
        client_factory=DbClientFactory("mongodb://localhost:27017"),
        purpose=PurposeAffinity.Creator
    )
    mock_summon_mongo.return_value = mock_dataverse
    
    # We can now invoke create() on the parameterized Recorder
    recorder = MongoRecorder(DummyModel)
    
    assert recorder.meta_state is not None
    assert recorder.meta_state.data_name == "test_recordings"
    assert recorder.meta_state.branch_name == "test_db"
    
