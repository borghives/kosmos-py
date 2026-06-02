import pytest
from pydantic import Field
from bson import ObjectId
import kosmos as km
from kosmos.matter.particle import Stasion

@pytest.fixture(scope="module", autouse=True)
def setup_kosmos():
    km.ignite("test.env")

@km.declare_persist_db(collection_name="test_stasis_collection", db_name="test_db")
class TestStasisModel(Stasion):
    __test__ = False
    name: str
    counter: km.IncrCounter = Field(default=km.ZeroCounter)

def test_stasis_model_insert():
    model = TestStasisModel(name="stasis_item")
    model.counter += 5
    
    assert model.counter == 5
    
    km.record(model)
    
    # Verify database contents
    recorder = km.recorder(TestStasisModel)
    collection = recorder.get_collection()
    db_data = collection.find_one({'_id': model.id})
    
    assert db_data is not None
    assert db_data["name"] == "stasis_item"
    # It should be saved as an integer 5 in the database, not a sub-document!
    assert db_data["counter"] == 5
    
    collection.delete_many({})

@km.declare_persist_db(collection_name="test_ledger_collection", db_name="test_db")
class MyLedger(km.Ledger):
    __test__ = False
    action: str
    amount: int

@pytest.fixture(autouse=True)
def clean_ledger_database():
    coll = km.recorder(MyLedger).get_collection()
    coll.delete_many({})

def test_ledger_sync_flow():
    ledger = MyLedger(action="deposit", amount=100)
    assert ledger.updated_time is None
    
    ledger.persist()
    assert ledger.updated_time is not None
    
    loaded = MyLedger.detect(km.fld("action") == "deposit").load_one()
    assert loaded is not None
    assert loaded.action == "deposit"
    assert loaded.amount == 100
    assert abs((loaded.updated_time - ledger.updated_time).total_seconds()) < 0.1

def test_ledger_async_flow():
    import asyncio
    async def run_async():
        ledger = MyLedger(action="withdraw", amount=50)
        assert ledger.updated_time is None
        
        await ledger.persist_async()
        assert ledger.updated_time is not None
        
        loaded = await MyLedger.detect(km.fld("action") == "withdraw").load_one_async()
        assert loaded is not None
        assert loaded.action == "withdraw"
        assert loaded.amount == 50
        assert abs((loaded.updated_time - ledger.updated_time).total_seconds()) < 0.1
        
    asyncio.run(run_async())

