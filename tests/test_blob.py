import pytest
import io
import asyncio
from datetime import datetime
from bson import ObjectId
from typing import Optional

import kosmos as km
from kosmos import PersistableBlob

@pytest.fixture(scope="module", autouse=True)
def setup_kosmos():
    km.ignite("test.env")

@km.declare_persist_db(db_name="test_db", collection_name="test_blobs", is_blob=True)
class MyBlob(PersistableBlob):
    __test__ = False
    metadata: Optional[dict] = None
    data: bytes = b""

    def dump_buffer(self) -> io.BytesIO:
        return io.BytesIO(self.data)

@pytest.fixture(autouse=True)
def clean_database():
    coll = km.mongo.collection.MongoCollection(MyBlob.get_meta_state())
    coll.get_collection().delete_many({})
    db = coll.get_collection().database
    db[coll._get_data_name() + ".chunks"].delete_many({})


def test_blob_sync_flow():
    # 1. Test successful upload
    file_content = b"Hello GridFS sync world!"
    new_blob = MyBlob(filename="sync_test.txt", data=file_content, metadata={"author": "Antigravity"})
    assert not new_blob.has_id()
    
    km.record(new_blob)
    assert new_blob.has_id()
    assert isinstance(new_blob.id, ObjectId)

    # 2. Test querying and metadata parsing
    detector = km.MongoDetector[MyBlob](MyBlob)
    loaded_blob = detector.filter(km.fld("filename") == "sync_test.txt").load_one()
    assert loaded_blob is not None
    assert loaded_blob.id == new_blob.id
    assert loaded_blob.filename == "sync_test.txt"
    assert loaded_blob.metadata == {"author": "Antigravity"}
    assert loaded_blob.length == len(file_content)
    assert loaded_blob.chunk_size is not None
    assert isinstance(loaded_blob.upload_date, datetime)

    # 3. Test open_blob and reading contents
    grid_out = km.open_blob(loaded_blob)
    downloaded_bytes = grid_out.read()
    assert downloaded_bytes == file_content

    # 4. Test updating metadata (which also re-uploads the buffer under user's collapse)
    loaded_blob.metadata = {"author": "Antigravity", "updated": True}
    loaded_blob.data = file_content
    km.record(loaded_blob)

    # Verify ID changed
    assert loaded_blob.id != new_blob.id
    new_id = loaded_blob.id
    assert new_id is not None

    # Verify metadata updated in DB
    updated_blob = detector.load_id(new_id)
    assert updated_blob is not None
    assert updated_blob.metadata == {"author": "Antigravity", "updated": True}
    
    grid_out2 = km.open_blob(updated_blob)
    assert grid_out2.read() == file_content  # Content remains intact

    # 5. Test replacing content (both data and metadata)
    old_id = updated_blob.id
    updated_blob.data = b"New updated content!"
    updated_blob.metadata = {"updated_content": True}
    km.record(updated_blob)

    final_id = updated_blob.id
    assert final_id is not None
    assert final_id != old_id
    

    # Verify old file is deleted from GridFS
    coll = km.mongo.collection.MongoCollection(MyBlob.get_meta_state())
    gfs = coll.get_gridfs()
    with pytest.raises(Exception):
        gfs.open_download_stream(old_id).read()

    # Verify new file has new contents and metadata
    new_loaded = detector.load_id(final_id)
    assert new_loaded is not None
    grid_out_final = km.open_blob(new_loaded)
    assert grid_out_final.read() == b"New updated content!"
    assert new_loaded.metadata == {"updated_content": True}


def test_blob_async_flow():
    async def run_async_test():
        # 1. Test successful upload
        file_content = b"Hello GridFS async world!"
        new_blob = MyBlob(filename="async_test.txt", data=file_content, metadata={"author": "Antigravity", "mode": "async"})
        assert not new_blob.has_id()

        await km.record_async(new_blob)
        assert new_blob.has_id()
        assert isinstance(new_blob.id, ObjectId)

        # 2. Test querying and metadata parsing
        detector = km.MongoDetector[MyBlob](MyBlob)
        loaded_blob = await detector.filter(km.fld("filename") == "async_test.txt").load_one_async()
        assert loaded_blob is not None
        assert loaded_blob.id == new_blob.id
        assert loaded_blob.filename == "async_test.txt"
        assert loaded_blob.metadata == {"author": "Antigravity", "mode": "async"}
        assert loaded_blob.length == len(file_content)
        assert loaded_blob.chunk_size is not None
        assert isinstance(loaded_blob.upload_date, datetime)

        # 3. Test open_blob_async and reading contents
        grid_out = await km.open_blob_async(loaded_blob)
        downloaded_bytes = await grid_out.read()
        assert downloaded_bytes == file_content

        # 4. Test updating metadata
        loaded_blob.metadata = {"author": "Antigravity", "mode": "async", "updated": True}
        loaded_blob.data = file_content
        await km.record_async(loaded_blob)

        # Verify ID changed
        assert loaded_blob.id != new_blob.id
        new_id = loaded_blob.id

        # Verify metadata updated in DB
        updated_blob = await detector.filter(km.fld("id") == new_id).load_one_async()
        assert updated_blob is not None
        assert updated_blob.metadata == {"author": "Antigravity", "mode": "async", "updated": True}
        
        grid_out2 = await km.open_blob_async(updated_blob)
        assert (await grid_out2.read()) == file_content

        # 5. Test replacing content
        old_id = updated_blob.id
        updated_blob.data = b"New updated async content!"
        updated_blob.metadata = {"updated_content": True, "mode": "async"}
        await km.record_async(updated_blob)

        final_id = updated_blob.id
        assert final_id != old_id

        # Verify old file is deleted from GridFS
        coll = km.mongo.collection.MongoCollection(MyBlob.get_meta_state())
        gfs = coll.get_gridfs_async()
        with pytest.raises(Exception):
            grid_out_old = await gfs.open_download_stream(old_id)
            await grid_out_old.read()

        # Verify new file has new contents and metadata
        new_loaded = await detector.filter(km.fld("id") == final_id).load_one_async()
        assert new_loaded is not None
        grid_out_final = await km.open_blob_async(new_loaded)
        assert (await grid_out_final.read()) == b"New updated async content!"
        assert new_loaded.metadata == {"updated_content": True, "mode": "async"}

    asyncio.run(run_async_test())
