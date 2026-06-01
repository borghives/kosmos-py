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
import polars as pl


@km.declare_persist_db(db_name="test_db", collection_name="test_collection", version=1)
class TestModel(ParticleBase):
    __test__ = False
    name: str
    value: int
    link_id: ObjectId | None = None



@pytest.fixture(scope="module", autouse=True)
def setup_kosmos():
    km.ignite("test.env")
    recorder = km.MongoRecorder(TestModel)
    collection = recorder.get_collection()
    collection.delete_many({})

    recorder.record(TestModel(name="Alice", value=30))
    recorder.record(TestModel(name="Bob", value=40))
    recorder.record(TestModel(name="Charlie", value=50))

def test_load_one():
    user = km.MongoDetector(TestModel).filter(km.fld('name') == "Alice").load_one()
    assert user is not None
    assert isinstance(user, TestModel)
    assert user.name == "Alice"

def test_load_many():
    users = km.MongoDetector(TestModel).filter(km.fld('value') > 35).load_many()
    assert len(users) == 2

def test_load_latest():
    latest_user = cast(TestModel, km.MongoDetector(TestModel).filter(km.fld('name') == "Charlie").load_top())
    assert latest_user is not None
    assert latest_user.name == "Charlie"

def test_exists():
    assert km.MongoDetector(TestModel).filter(km.fld('name') == "Alice").exists()
    assert not km.MongoDetector(TestModel).filter(km.fld('name') == "David").exists()

def test_load_dataframe():
    df = km.MongoDetector(TestModel).load_dataframe()
    assert len(df) == 3
    assert "name" in df.columns

def test_load_polars():
    df = km.MongoDetector(TestModel).load_polars()
    assert len(df) == 3
    assert isinstance(df, pl.DataFrame)
    assert "name" in df.columns

def test_load_table():
    table = km.MongoDetector(TestModel).load_table()
    assert len(table) == 3
    assert "name" in table.column_names