from polars import string_cache
from pymongo.errors import BulkWriteError
from pydantic import Field
from bson import ObjectId
from kosmos.matter.persistable import ParticleBase, Persistable
from datetime import datetime, timezone
from pymongo.collection import Collection
import pytest
from typing import cast
import kosmos as km
import rich
import pandas as pd

@pytest.fixture(scope="module", autouse=True)
def setup_kosmos():
    km.ignite("test.env")

@km.declare_persist_db(db_name="test_db", collection_name="test_collection", version=1)
class TestModel(ParticleBase):
    __test__ = False
    name: str
    value: int
    link_id: ObjectId | None = None

@km.declare_persist_db(db_name="test_db", collection_name="test_collection", version=1)
class TestModelWithLinkId(Persistable):
    __test__ = False
    name: str
    value: int
    link_id: ObjectId | None = None
    link2_id: ObjectId = Field(description="An incrementing integer counter", default=ObjectId())

@km.declare_persist_db(collection_name="test_inc_collection", db_name="test_db")
class TestIncModel(Persistable):
    __test__ = False
    test_field: str
    counter: km.IncrCounter  = Field(description="An incrementing integer counter", default=km.ZeroCounter)
    counter2: km.IncrCounter = Field(description="An incrementing integer counter", default=km.ZeroCounter)

def test_has_update_logic():
    # 1. Test new model
    new_model = TestModel(name="new", value=1)
    assert new_model.has_update

    # 2. Test model from DB
    doc = {"_id": ObjectId(), "name": "from_db", "value": 2, "version": 1}
    loaded_model = TestModel.from_doc(doc)
    assert not loaded_model.has_update
    
    result_doc = loaded_model.dump_doc()
    result_doc['_id'] = loaded_model.id
        
    km.record(loaded_model)
    assert not loaded_model.has_update

def test_persist_object_id():
    # 1. Test new model
    new_model = TestModel(name="new", value=1, link_id=ObjectId())
    assert new_model.has_update

    # 2. Test model from DB
    doc = {"_id": ObjectId(), "name": "from_db", "value": 2, "version": 1, "link_id": ObjectId()}
    loaded_model = TestModel.from_doc(doc)
    assert not loaded_model.has_update
    
    result_doc = loaded_model.dump_doc()
    result_doc['_id'] = loaded_model.id

    
    km.record(loaded_model)
    assert not loaded_model.has_update

def test_should_persist_property():
    """Test the should_persist property logic."""
    new_model = TestModelWithLinkId(name="new", value=1)
    assert new_model.should_persist

    loaded_model = TestModel.from_doc({"_id": ObjectId(), "name": "loaded", "value": 2})
    assert not loaded_model.should_persist

    loaded_model.mark_updated()
    assert loaded_model.should_persist

def test_get_set_instruction():
    """Test the get_set_instruction method."""
    fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Directly modify the collapse function for the test
    updated_time_transformer = TestModelWithLinkId.get_field_metadata("updated_time", km.RefreshOnSet)[0]
    updated_time_transformer.refresh = lambda x: fixed_time

    model = TestModelWithLinkId(name="test", value=10)
    model.updated_time = None  # Ensure coalesce is triggered

    ripple = model.collapse()
    set_instr = ripple.get_update_instruction()
    set_doc = set_instr["$set"]

    assert set_doc["name"] == "test"
    assert set_doc["updated_time"] == fixed_time

def test_get_update_instruction():
    """Test the complete update instruction generation."""
    fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Directly modify the refresh functions for the test
    updated_time_transformer = TestModelWithLinkId.get_field_metadata("updated_time", km.RefreshOnSet)[0]
    updated_time_transformer.refresh = lambda x: fixed_time
    created_at_transformer = TestModelWithLinkId.get_field_metadata("created_at", km.CoalesceOnInsert)[0]
    created_at_transformer.collapse = lambda : fixed_time

    model = TestModelWithLinkId(name="test", value=10)
    model.id = None
    model.created_at = None
    model.updated_time = None

    ripple = model.collapse()
    update_instr = ripple.get_update_instruction()

    assert "$set" in update_instr
    set_doc = update_instr["$set"]
    assert set_doc["updated_time"] == fixed_time

    assert "$setOnInsert" in update_instr
    set_on_insert_doc = update_instr["$setOnInsert"]
    assert set_on_insert_doc["created_at"] == fixed_time

def test_inc_op():
    # 1. Create and persist a new model with an increment
    model = TestIncModel(test_field="inc_test")

    print(f"Type of read_count: {type(model.counter)}")

    model.counter += 2
    model.counter2 += 3

    assert model.counter == 2
    assert model.counter2 == 3

    print(f"Type of read_count: {type(model.counter)}")

    km.record(model)

    assert model.counter == 2
    assert model.counter2 == 3

    recorder = km.MongoRecorder(TestIncModel)
    recorder.record(model)
    
    # 2. Check the database for the initial state
    collection = recorder.get_collection()
    assert collection is not None
    assert isinstance(collection, Collection)

    db_data = collection.find_one({'_id': model.id})
    assert db_data is not None
    assert db_data["test_field"] == "inc_test"
        # On first insert, then inc is 2. So it should be 2.
    assert db_data["counter"] == 2
    assert db_data["counter2"] == 3
    assert db_data["_id"] == model.id

    # 3. Load from DB, increment again, and persist
    assert model.id is not None
    
    field = km.fld("counter")
    assert field is not None

    detector = km.detect(TestIncModel)
    loaded_model = cast(TestIncModel, detector.load_id(model.id))
    assert loaded_model is not None
    assert loaded_model.counter == 2

    loaded_model.counter += 3
    recorder.record(loaded_model)

    # 4. Check the database for the updated state
    db_data_updated = collection.find_one({'_id': loaded_model.id})
    assert db_data_updated is not None
    # 2 + 3 = 5
    assert db_data_updated["counter"] == 5

    # # Clean up
    # collection.delete_one(model.self_filter())
def test_persist_instance():
    """Test persisting a single model instance."""

    model = TestModel(name="to_persist", value=100)
    model.name = "persisted"

    km.record(model)

    assert model.has_update == False
    assert model.name == "persisted"

def test_insert_dataframe():
    """Test inserting a pandas DataFrame."""

    df = pd.DataFrame({"name": ["df_user1"], "value": [10], "updated_time": [None]})
    km.MongoRecorder(TestModel).insert_dataframe(df)

def test_insert_dataframe_with_objectid():
    """Test inserting a pandas DataFrame."""
    link_id = ObjectId()
    link2_id = ObjectId()
    df = pd.DataFrame({"_id": [ObjectId()], "name": ["df_user1_with_link"], "value": [10], "updated_time": [None], "link_id": [link_id], "link2_id": [link2_id]})
    km.MongoRecorder(TestModelWithLinkId).insert_dataframe(df)

    loaded_model = km.detect(TestModelWithLinkId).filter(km.fld("link_id") == link_id).load_one()

    assert loaded_model is not None
    assert isinstance(loaded_model, TestModelWithLinkId)
    assert isinstance(loaded_model.link_id, ObjectId)
    assert isinstance(loaded_model.link2_id, ObjectId)
    assert isinstance(loaded_model.id, ObjectId)
    
    assert loaded_model.name == "df_user1_with_link"
    assert loaded_model.value == 10
    assert loaded_model.link_id == link_id
    assert loaded_model.link2_id == link2_id


def test_update_dataframe():
    """Test upserting a DataFrame."""

    recorder = km.MongoRecorder(TestModel)
    collection = recorder.get_collection()
    collection.delete_many({})

    # 1. Insert initial data
    model = TestModel(name="existing", value=1)
    recorder.record(model)

    model = TestModel(name="other", value=2)
    recorder.record(model)

    # 2. Prepare DataFrame for upsert
    # "existing" will be updated (value 1 -> 10)
    # "new" will be inserted
    df = pd.DataFrame([
        {"name": "existing", "value": 10},
        {"name": "new", "value": 20}
    ])

    # 3. Perform Upsert
    recorder.update_dataframe(df, on=["name"], upsert=True)

    detector = km.detect(TestModel)

    # 4. Verify
    # Check "existing" updated
    existing = detector.filter(km.fld("name") == "existing").load_one()
    assert existing is not None
    assert existing.value == 10

    # Check "new" inserted
    new_item = detector.filter(km.fld("name") == "new").load_one()
    assert new_item is not None
    assert new_item.value == 20

    # Check "other" remains untouched
    other = detector.filter(km.fld("name") == "other").load_one()
    assert other is not None
    assert other.value == 2

    # Total count should be 3
    assert collection.count_documents({}) == 3

    # Clean up
    collection.delete_many({})

def test_insert_dataframe_ignores_duplicate_error():
    """Test that insert_dataframe handles and ignores duplicate key errors."""
    

    df = pd.DataFrame({"name": ["test"], "value": [1]})
    
    try:
        km.MongoRecorder(TestModel).insert_dataframe(df)
    except BulkWriteError as bwe:
        assert bwe is None
    
def test_load_dataframe():
    """Test loading data into a pandas DataFrame."""
    recorder = km.MongoRecorder(TestModel)
    collection = recorder.get_collection()
    collection.delete_many({})

    df = pd.DataFrame([
        {"name": "df_user1", "value": 11, "link_id": ObjectId()},
        {"name": "df_user2", "value": 20, "link_id": ObjectId()},
    ])
    recorder.insert_dataframe(df)

    detector = km.detect(TestModel)
    loaded_df = detector.load_dataframe()

    assert len(loaded_df) == 2
    assert "name" in loaded_df.columns
    assert "value" in loaded_df.columns
    assert "link_id" in loaded_df.columns
    assert "_id" in loaded_df.columns
    
    rich.print(loaded_df)

    # Clean up
    collection.delete_many({})