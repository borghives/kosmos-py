from kosmos.meta.expression.filter import QueryPredicates
from kosmos.mongo.collection import MongoCollection
from kosmos.matter.blob import BlobBase
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