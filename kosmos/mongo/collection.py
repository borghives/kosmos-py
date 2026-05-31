from pydantic.fields import FieldInfo
from pymongo.collection import Collection
from pymongo.asynchronous.collection import AsyncCollection
from kosmos.ether.universal import UniversalConstants
from kosmos.meta.state import MetaState

from .dataverse import summon_mongo
from .client import PurposeAffinity

class MongoCollection:
    def __init__(self, meta_state: MetaState):
        self.meta_state = meta_state
        self._sync_collection : Collection | None = None
        self._async_collection : AsyncCollection | None = None

    def get_model_fields(self) -> dict[str, FieldInfo]:
        return self.meta_state.field_map

    def get_collection(self, with_async: bool = False) -> Collection | AsyncCollection:
        if not with_async and self._sync_collection is not None:
            return self._sync_collection
        if with_async and self._async_collection is not None:
            return self._async_collection
        
        database_name = self.meta_state.branch_name
        collection_name = self.meta_state.data_name

        if self.meta_state.version is not None:
            collection_name += "_v" + str(self.meta_state.version)

        if UniversalConstants.collapse().is_test_mode:
            collection_name += "_test"
        
        client = summon_mongo(PurposeAffinity.Observer).sync_client()
        database = client[database_name]
        
        self._sync_collection = database[collection_name]
        if with_async:
            client = summon_mongo(PurposeAffinity.Observer).async_client()
            self._async_collection = client[database_name][collection_name]
            return self._async_collection
        else:
            client = summon_mongo(PurposeAffinity.Observer).sync_client()
            self._sync_collection = client[database_name][collection_name]
            return self._sync_collection