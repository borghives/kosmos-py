from kosmos.meta.expression.filter import QueryPredicates
from kosmos.meta.expression.field import QueryableField
from kosmos.mongo.collection import MongoCollection
from kosmos.matter.blob import BlobBase
from bson import ObjectId
from .detector import detect
from .recorder import recorder

class PersistableBlob(BlobBase):
    @classmethod
    def detect(cls, filter: QueryPredicates|None = None):
        detector = detect(cls)
        if filter is not None:
            detector = detector.filter(filter)
        return detector

    @classmethod
    def from_filename(cls, filename: str):
        return cls.detect(QueryableField("filename") == filename).load_one()

    @classmethod
    def from_id(cls, id: ObjectId | str):
        if isinstance(id, str):
            if not ObjectId.is_valid(id):
                return None
            id = ObjectId(id)
        return cls.detect(QueryableField("_id") == id).load_one()

    @classmethod
    def recorder(cls):
        return recorder(cls)
    
    def persist(self):
        self.recorder().record(self)
    
    async def persist_async(self):
        await self.recorder().record_async(self)

    def open(self):
        return open_blob(self)
    
    async def open_async(self):
        return await open_blob_async(self)

def open_blob(file :BlobBase):
    fs = MongoCollection(type(file).get_meta_state()).get_gridfs()
    if file.has_id():
        return fs.open_download_stream(file.collapse_id())
    else:
        return fs.open_download_stream_by_name(file.filename, revision=-1)

async def open_blob_async(file :BlobBase):
    fs = MongoCollection(type(file).get_meta_state()).get_gridfs_async()
    if file.has_id():
        return await fs.open_download_stream(file.collapse_id())
    else:
        return await fs.open_download_stream_by_name(file.filename, revision=-1)