from pydantic.fields import FieldInfo
from pymongo.collection import Collection
from pymongo.asynchronous.collection import AsyncCollection
from kosmos.ether.universal import UniversalConstants
from kosmos.meta.state import MetaState

from .dataverse import summon_mongo
from .client import PurposeAffinity

import gridfs

class MongoCollection:
    def __init__(self, meta_state: MetaState):
        self.meta_state = meta_state
        self._collection : Collection | None = None
        self._collection_async : AsyncCollection | None = None
        self._gridfs : gridfs.GridFSBucket | None = None
        self._gridfs_async : gridfs.AsyncGridFSBucket | None = None

    def _get_db_name(self) -> str:
        return self.meta_state.branch_name

    def _get_data_name(self) -> str:
        name = self.meta_state.data_name
        if self.meta_state.version is not None:
            name += f"_v{self.meta_state.version}"
        if UniversalConstants.collapse().is_test_mode:
            name += "_test"
        return name

    def _get_collection_name(self) -> str:
        collection_name = self._get_data_name()
        if self.meta_state.is_blob:
            collection_name += ".files"
        return collection_name

    def get_model_fields(self) -> dict[str, FieldInfo]:
        return self.meta_state.field_map

    def get_gridfs(self) -> gridfs.GridFSBucket:
        if not self.meta_state.is_blob:
            raise TypeError("Collection is not a blob collection")
        
        if self._gridfs is not None:
            return self._gridfs

        database_name = self._get_db_name()
        bucket_name = self._get_data_name()
        
        mongo_data = summon_mongo(PurposeAffinity.Observer)
        self._gridfs = gridfs.GridFSBucket(mongo_data.sync_client()[database_name], bucket_name)
        return self._gridfs

    def get_gridfs_async(self) -> gridfs.AsyncGridFSBucket:
        if self._gridfs_async is not None:
            return self._gridfs_async

        database_name = self._get_db_name()
        bucket_name = self._get_data_name()
        
        mongo_data = summon_mongo(PurposeAffinity.Observer)
        self._gridfs_async = gridfs.AsyncGridFSBucket(mongo_data.async_client()[database_name], bucket_name)
        return self._gridfs_async
    
    def get_collection_async(self) -> AsyncCollection:
        if self._collection_async is not None:
            return self._collection_async
        
        database_name = self._get_db_name()
        collection_name = self._get_collection_name()
        
        mongo_data = summon_mongo(PurposeAffinity.Observer)
        self._collection_async = mongo_data.async_client()[database_name][collection_name]
        return self._collection_async
        
    def get_collection(self) -> Collection:
        if self._collection is not None:
            return self._collection
        
        database_name = self._get_db_name()
        collection_name = self._get_collection_name()
        
        mongo_data = summon_mongo(PurposeAffinity.Observer)
        self._collection = mongo_data.sync_client()[database_name][collection_name]
        return self._collection