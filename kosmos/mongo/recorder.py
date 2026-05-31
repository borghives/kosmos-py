from kosmos.mongo.collection import MongoCollection
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from bson import ObjectId
from kosmos.meta.util import get_base_type
from typing import Type
from kosmos.matter.observable import RippleState
from kosmos.matter.observable import Observable
from pymongo.collection import Collection
from pymongo.asynchronous.collection import AsyncCollection
import pandas as pd
import polars as pl
import pyarrow

class MongoRecorder(MongoCollection):
    def __init__(self, obj_type: Type[Observable]):
        super().__init__(obj_type.get_meta_state())

    def upsert(self, scope: dict, update: dict):
        collection = self.get_collection()
        assert isinstance(collection, Collection)
        return collection.update_one(scope, update, upsert=True)

    def record(self, obj: Observable):
        ripple = obj.collapse()
        if ripple.state == RippleState.Unobservable:
            raise ValueError("Failed to record: ripple state is unobservable.")
        
        #NOTE!!: Early exit without the object Decohere[nce] at the end will keep the object in a transitional (INBETWEEN) state
        scope = ripple.get_scope()
        update = ripple.get_update_instruction()
        ripple.update_feedback = self.upsert(scope, update)

        obj.decohere(ripple)
    
    def get_fields_with_base_type(self, base_type: type, include_aliases: bool = False) -> list[str]:
        retval :list[str] = []
        for key, field in self.meta_state.field_map.items():
            annotation = field.annotation
            if get_base_type(annotation) is base_type:
                retval.append(key)
                if include_aliases and field.alias is not None and field.alias != key:
                    retval.append(field.alias)

        return retval

    def convert_dataframe_to_records(self, dataframe: pd.DataFrame | pl.DataFrame | pyarrow.Table) -> list[dict] | None:
        records : list[dict] | None = None

        if isinstance(dataframe, pd.DataFrame) and not dataframe.empty:
            records = dataframe.to_dict("records")
        elif isinstance(dataframe, pl.DataFrame) and not dataframe.is_empty():
            records = dataframe.to_dicts()
        elif isinstance(dataframe, pyarrow.Table) and dataframe.num_rows > 0:
            records = dataframe.to_pylist()

        if records is None or len(records) == 0:
            return None

        id_fields = self.get_fields_with_base_type(ObjectId, include_aliases=True)
        if (len(id_fields) > 0):
            for record in records:
                for field in id_fields:
                    if field in record:
                        input = record[field]
                        if (input is not None):
                            record[field] = ObjectId(input)

        return records

    def insert_dataframe(
        self, dataframe: pd.DataFrame | pl.DataFrame | pyarrow.Table, chunk_size: int = 1000
    ):
        """
        Inserts a DataFrame into the database.

        Note: to have RefreshOnDataframeInsert fields refresh, the columns must exist in the DataFrame.  
        Default columns to None if to have field trigger content.

        Args:
            dataframe (pd.DataFrame): The DataFrame to insert.
        """

        collection = self.get_collection()

        records = self.convert_dataframe_to_records(dataframe)

        if records is None or len(records) == 0:
            return

        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            try:
                collection.insert_many(chunk, ordered=False)  # ordered false so that a duplicate key error won't stop the insert of many
            except BulkWriteError as bwe:
                # If there are errors other than duplicate key (11000), re-raise the original exception.
                # This preserves the full error context for the caller to handle.
                if any(error['code'] != 11000 for error in bwe.details['writeErrors']):
                    raise    

    def write_bulk_unordered(self, operations: list, chunk_size: int = 10):
        if not operations:
            return

        collection = self.get_collection()
        assert isinstance(collection, Collection)

        for i in range(0, len(operations), chunk_size):
            chunk = operations[i:i + chunk_size]
            try:
                collection.bulk_write(chunk, ordered=False)
            except BulkWriteError as bwe:
                # If there are errors other than duplicate key (11000), re-raise the original exception.
                # This preserves the full error context for the caller to handle.
                if any(error['code'] != 11000 for error in bwe.details['writeErrors']):
                    raise

    def update_dataframe(
        self, dataframe: pd.DataFrame | pl.DataFrame | pyarrow.Table,
        on: list[str],
        upsert: bool = False,
    ):
        """
        Upserts a DataFrame into the database.

        Note: to have RefreshOnDataframeInsert fields refresh, the columns must exist in the DataFrame.  
        Default columns to None if to have field trigger content.

        Args:
            dataframe (pd.DataFrame): The DataFrame to update or insert.
            on (list[str]): The fields to use for upserting.
        """

        records = self.convert_dataframe_to_records(dataframe)

        if records is None or len(records) == 0:
            return

        operations: list = []

        for record in records:
            filter = {key: record[key] for key in on}
            update = {"$set": record}
            update_op = UpdateOne(
                filter,
                update,
                upsert=upsert,
            )
            operations.append(update_op)
        
        self.write_bulk_unordered(operations)
    
    async def upsert_async(self, scope: dict, update: dict):
        collection = self.get_collection(with_async=True)
        assert isinstance(collection, AsyncCollection)
        return await collection.update_one(scope, update, upsert=True)    

    async def record_async(self, obj: Observable):
        ripple = obj.collapse()
        if ripple.state == RippleState.Unobservable:
            raise ValueError("Failed to record: ripple state is unobservable.")
        
        #NOTE!!: Early exit without the object Decohere[nce] at the end will keep the object in a transitional (INBETWEEN) state
        scope = ripple.get_scope()
        update = ripple.get_update_instruction()
        ripple.update_feedback = await self.upsert_async(scope, update)

        obj.decohere(ripple)
    
    async def insert_dataframe_async(
        self, dataframe: pd.DataFrame | pl.DataFrame | pyarrow.Table, chunk_size: int = 1000
    ):
        """
        Inserts a DataFrame into the database.

        Note: to have RefreshOnDataframeInsert fields refresh, the columns must exist in the DataFrame.  
        Default columns to None if to have field trigger content.

        Args:
            dataframe (pd.DataFrame): The DataFrame to insert.
        """

        collection = self.get_collection(with_async=True)
        assert isinstance(collection, AsyncCollection)

        records = self.convert_dataframe_to_records(dataframe)

        if records is None or len(records) == 0:
            return

        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            try:
                await collection.insert_many(chunk, ordered=False)  # ordered false so that a duplicate key error won't stop the insert of many
            except BulkWriteError as bwe:
                # If there are errors other than duplicate key (11000), re-raise the original exception.
                # This preserves the full error context for the caller to handle.
                if any(error['code'] != 11000 for error in bwe.details['writeErrors']):
                    raise
    
    async def write_bulk_unordered_async (self, operations: list, chunk_size: int = 10):
        if not operations:
            return

        collection = self.get_collection(with_async=True)
        assert isinstance(collection, AsyncCollection)

        for i in range(0, len(operations), chunk_size):
            chunk = operations[i:i + chunk_size]
            try:
                await collection.bulk_write(chunk, ordered=False)
            except BulkWriteError as bwe:
                # If there are errors other than duplicate key (11000), re-raise the original exception.
                # This preserves the full error context for the caller to handle.
                if any(error['code'] != 11000 for error in bwe.details['writeErrors']):
                    raise

    async def update_dataframe_async(
        self, dataframe: pd.DataFrame | pl.DataFrame | pyarrow.Table,
        on: list[str],
        upsert: bool = False,
    ):
        """
        Upserts a DataFrame into the database.

        Note: to have RefreshOnDataframeInsert fields refresh, the columns must exist in the DataFrame.  
        Default columns to None if to have field trigger content.

        Args:
            dataframe (pd.DataFrame): The DataFrame to update or insert.
            on (list[str]): The fields to use for upserting.
        """

        records = self.convert_dataframe_to_records(dataframe)

        if records is None or len(records) == 0:
            return

        operations: list = []

        for record in records:
            filter = {key: record[key] for key in on}
            update = {"$set": record}
            update_op = UpdateOne(
                filter,
                update,
                upsert=upsert,
            )
            operations.append(update_op)
        
        await self.write_bulk_unordered_async(operations)

def record(obj: Observable):
    MongoRecorder(obj.__class__).record(obj)

async def record_async(obj: Observable):
    await MongoRecorder(obj.__class__).record_async(obj)


