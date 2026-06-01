
from kosmos.matter.blob import PersistableBlob
from pymongo.asynchronous.collection import AsyncCollection
from bson import ObjectId
from enum import StrEnum
from pymongo.collection import Collection
from kosmos.meta.expression.base import ExpressionDriver
from typing import Optional
from kosmos.meta.expression.field import QueryableField
from kosmos.meta.expression.base import combine_field_specifications
from kosmos.meta.expression.base import FieldSpecification, Expression, GroupExpression
from kosmos.meta.expression.sort import SortAsc
from kosmos.meta.expression.sort import SortDesc
from kosmos.meta.expression.sort import SortOp
from kosmos.meta.expression.filter import QueryPredicates
from typing import Self
from kosmos.matter.observable import Observable
from typing import Type, List
from kosmos.mongo.collection import MongoCollection
from kosmos.meta.expression.aggregation import AggregationStages
from kosmos.matter.detectable import Detectable
from pymongoarrow.api import ( #type: ignore
    Schema,  Table,
    aggregate_arrow_all,
    aggregate_pandas_all,
    aggregate_polars_all
) 
import pandas as pd
import polars as pl


class WhenMatchedAction(StrEnum):
    REPLACE = "replace"
    MERGE = "merge"
    FAIL = "fail"
    KEEP_EXISTING = "keepExisting"
    PIPELINE = "pipeline"

class WhenNotMatchedAction(StrEnum):
    INSERT = "insert"
    DISCARD = "discard"
    FAIL = "fail"

class MongoDetector[T: Detectable](MongoCollection):
    def __init__(self, obj_type: Type[T]):
        super().__init__(obj_type.get_meta_state())
        self._aggregation_expr: AggregationStages = AggregationStages()
        self._persist_cls = obj_type

    def _new_agg(self, agg: AggregationStages | None = None) -> Self:
        if agg is None:
            agg = self._aggregation_expr

        retval = MongoDetector[T](self._persist_cls)
        retval._aggregation_expr = agg
        return retval

    def filter(self, filter: QueryPredicates) -> Self:
        """
        Adds a filter to the query.

        Args:
            filter (QueryPredicates): The filter to add.

        Returns:
            MongoDetector: The `MongoDetector` object for chaining.
        """
        return self._new_agg(self._aggregation_expr.match(filter))
    
    def sort(self, sort: SortOp | str | None = None, descending: bool = False) -> Self:
        """
        Adds a sort to the query.

        Args:
            sort (SortOp | str): The sort to add.
            descending (bool): Whether to sort in descending order.  Only significant is sort is a string. Defaults to `False`.

        Returns:
            MongoDetector: The `MongoDetector` object for chaining.
        """

        if (sort is None):
            return self

        if isinstance(sort, SortOp):
            sort_op = sort
        else:
            sort_op = SortDesc(sort) if descending else SortAsc(sort)

        return self._new_agg(self._aggregation_expr.sort(sort_op))

    def skip(self, skip: int) -> Self:
        """
        Adds a skip to the query.

        Args:
            skip (int): The number of documents to skip.

        Returns:
            MongoDetector: The `MongoDetector` object for chaining.
        """
        return self._new_agg(self._aggregation_expr.skip(skip))

    def limit(self, limit: int) -> Self:
        """
        Adds a limit to the query.

        Args:
            limit (int): The limit to add.

        Returns:
            MongoDetector: The `MongoDetector` object for chaining.
        """
        return self._new_agg(self._aggregation_expr.limit(limit))

    def sample(self, sample: int) -> Self:
        """
        Adds a sample stage to the aggregation pipeline.

        Args:
            sample (int): The number of documents to sample.

        Returns:
            MongoDetector: The `MongoDetector` object for chaining.
        """
        return self._new_agg(self._aggregation_expr.sample(sample))

    def add_fields(self, *specifications: FieldSpecification | dict) -> Self:
        """
        Adds an addFields stage to the aggregation pipeline.

        Args:
            specifications (FieldSpecification | dict): The fields to add.

        Returns:
            MongoDetector: The `MongoDetector` object for chaining.
        """

        combined = combine_field_specifications(*specifications)
        
        if combined is not None:
            return self._new_agg(self._aggregation_expr.add_fields(combined))

        return self

    def project(self, *specifications: FieldSpecification | dict) -> Self:
        combined = combine_field_specifications(*specifications)
        
        if combined is not None:
            return self._new_agg(self._aggregation_expr.project(combined))

        return self

    def lookup(self, foreign_collection: str, local_field: str, foreign_field: str, to_field: str = "result") -> Self:
        return self._new_agg(self._aggregation_expr.lookup(
            foreignCollection=foreign_collection, 
            localField=local_field, 
            foreignField=foreign_field, 
            toField=to_field
        ))

    def group_by(self, *keys: str | FieldSpecification | None) -> "GroupDetector[T]":
        combined: FieldSpecification = FieldSpecification()
        for key in keys:
            if isinstance(key, str):
                combined |= QueryableField(key).with_(key)
            else:
                combined |= key
        
        return GroupDetector[T](self, combined)
    
    def agg(self, aggregation: AggregationStages) -> Self:
        """
        Adds an aggregation pipeline to the query.

        Args:
            aggregation (Aggregation): The aggregation pipeline to add.

        Returns:
            LoadDirective: The `LoadDirective` object for chaining.
        """
        return self._new_agg(self._aggregation_expr | aggregation)

    def count(self) -> int:
        """
        Executes a count query on the model's collection.

        Returns:
            int: The number of documents matching the filter.
        """
        count_exc = self._new_agg(self._aggregation_expr.count("count"))
        with count_exc.exec_agg() as cursors:
            for result in cursors:
                return result.get("count", 0)

        return 0  # type: ignore

    def load_id(self, id : ObjectId | str):
        if isinstance(id, str):
            if not ObjectId.is_valid(id):
                return None
            id = ObjectId(id)
        return self.filter(QueryableField("id") == id).load_one()

    def exec_agg(self, post_agg: Optional[AggregationStages] = None):
        """
        Performs an aggregation query on the model's collection.

        Args:
            post_agg (Aggregation, optional): The aggregation pipeline to
                append to the end just for this execution

        Returns:
            CommandCursor: A `pymongo` cursor to the results of the aggregation.
        """
        collection = self.get_collection()
        assert isinstance(collection, Collection)
        return collection.aggregate(self._get_pipeline_expr(post_agg))

    def load_agg(self, post_agg: Optional[AggregationStages] = None) -> list[T]:
        """
        Executes an aggregation and returns the results as a list of models.

        Args:
            post_agg (Aggregation, optional): The aggregation pipeline to
                append to the end just for this execution

        Returns:
            list[PersistableType]: A list of model instances.
        """
        p_cls = self._persist_cls
        with self.exec_agg(post_agg) as cursors:
            return [p_cls.from_doc(doc) for doc in cursors]
    
    def load_one(self) -> Optional[T]:
        """
        Loads a single document from the database.

        Returns:
            Optional[T]: An instance of the model, or `None` if no document is found.
        """
        docs = self.load_agg(AggregationStages().limit(1))
        return docs[0] if len(docs) > 0 else None

    def load_many(self) -> list[T]:
        """
        Loads multiple documents from the database.

        Returns:
            list[T]: A list of loaded model instances.
        """
        return self.load_agg()

    def load_top(self, sort: SortOp = SortDesc("updated_time")) -> Optional[T]:
        """
        Loads the most recently updated document from the database.

        Args:
            sort (SortOp, optional): Sort order. Defaults to `updated_time` descending.

        Returns:
            Optional[T]: An instance of the loaded document, or `None` if not found.
        """
        docs = self.load_agg(AggregationStages().sort(sort).limit(1))
        return docs[0] if len(docs) > 0 else None

    def merge_into(self, collection_name: str, on: List[str], when_matched: WhenMatchedAction = WhenMatchedAction.REPLACE, when_not_matched: WhenNotMatchedAction = WhenNotMatchedAction.INSERT):
        merge_exe =  self._new_agg(self._aggregation_expr.merge({
            "into": collection_name,
            "on": on,
            "whenMatched": when_matched.value,
            "whenNotMatched": when_not_matched.value 
        }))
        merge_exe.exec_agg()

    def exists(self) -> bool:
        """
        Checks if at least one document matching the filter exists.

        Returns:
            bool: `True` if a matching document exists, `False` otherwise.
        """
        docs = self.load_agg(AggregationStages().limit(1))
        return len(docs) > 0
    
    def load_table(self, schema: Optional[Schema] = None) -> Table:
        """
        Loads data from a query into a PyArrow Table.

        Args:
            schema (Schema, optional): The PyArrow schema to use.

        Returns:
            Table: A PyArrow Table containing the loaded data.
        """

        collection = self.get_collection()
        return aggregate_arrow_all(collection, pipeline=self._get_pipeline_expr(), schema=Schema(schema) if schema else None)
    
    def load_dataframe(self, schema: Optional[Schema] = None) -> pd.DataFrame:
        """
        Loads data from a query into a pandas DataFrame.

        Args:
            schema (Schema, optional): The PyArrow schema to use.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the loaded data.
        """
        collection = self.get_collection()
        return aggregate_pandas_all(collection, pipeline=self._get_pipeline_expr(), schema=Schema(schema) if schema else None)

    def load_polars(self, schema: Optional[dict] = None) -> pl.DataFrame | pl.Series:
        """
        Loads data from a query into a polars DataFrame.

        Args:
            schema (Schema, optional): The PyArrow schema to use.

        Returns:
            pl.DataFrame | pl.Series: A polars DataFrame or Series containing the loaded data.
        """
        collection = self.get_collection()
        return aggregate_polars_all(collection, pipeline=self._get_pipeline_expr(), schema=Schema(schema) if schema else None)

    async def exec_agg_async(self, post_agg: Optional[AggregationStages] = None):
        collection = self.get_collection_async()
        return await collection.aggregate(self._get_pipeline_expr(post_agg))

    async def load_agg_async(self, post_agg: Optional[AggregationStages] = None):
        p_cls = self._persist_cls
        cursor = await self.exec_agg_async(post_agg)
        async with cursor:
            async for doc in cursor:
                yield p_cls.from_doc(doc)

    async def load_one_async(self) -> Optional[T]:
        async for doc in self.load_agg_async(AggregationStages().limit(1)):
            return doc
    
    async def load_many_async(self) -> list[T]:
        return [doc async for doc in self.load_agg_async()]

    async def load_top_async(self, sort: SortOp = SortDesc("updated_time")):
        async for doc in self.load_agg_async(AggregationStages().sort(sort).limit(1)):
            return doc
    
    async def merge_into_async(self, collection_name: str, on: List[str], when_matched: WhenMatchedAction = WhenMatchedAction.REPLACE, when_not_matched: WhenNotMatchedAction = WhenNotMatchedAction.INSERT):
        merge_exe = self._new_agg(self._aggregation_expr.merge({
            "into": collection_name,
            "on": on,
            "whenMatched": when_matched.value, #<replace|keepExisting|merge|fail|pipeline>, 
            "whenNotMatched": when_not_matched.value #<insert|discard|fail> 
        }))
        await merge_exe.exec_agg_async()

    async def exists_async(self) -> bool:
        doc = await self.load_one_async()
        return doc is not None

    def _load_dataframe_legacy(
        self,
    ) -> pd.DataFrame:
        """
        Loads data from an aggregation query into a pandas DataFrame.

        Args:
            aggregation (Aggregation, optional): The aggregation pipeline.
            filter (Filter, optional): A filter to apply to the aggregation.
            sampling (Optional[Size], optional): The number of documents to
                sample.
            sort (SortOp, optional): A sort directive for the aggregation.
            **kwargs: Additional keyword arguments to form a filter.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the loaded data.
        """
        with self.exec_agg() as cursors:
            df = pd.DataFrame(cursors)
            return df

    def _get_expression_driver(self) -> ExpressionDriver:
        return ExpressionDriver(self.get_model_fields())

    def _get_pipeline_expr(self, post_agg: Optional[AggregationStages] = None) -> list[dict]:
        pipelines = (self._aggregation_expr | post_agg)
        flattened_pipelines =pipelines.express(self._get_expression_driver())
        assert isinstance(flattened_pipelines, list)
        return flattened_pipelines

class GroupDetector[T: Detectable]:
    def __init__(self, base_directive: MongoDetector[T], key: Expression | None):
        self._base_directive = base_directive
        self.group_expression = GroupExpression(key)
        
    def acc(self : "GroupDetector[T]", *accumulators: FieldSpecification) -> MongoDetector[T]:
        if (accumulators is None or len(accumulators) == 0):
            return self._base_directive
        
        combined: Optional[FieldSpecification] = None
        for accumulator in accumulators:
            if combined is None:
                combined = accumulator
            else:
                combined |= accumulator
        
        if combined is not None:
            group_agg = AggregationStages().group(self.group_expression.with_acc(combined))
            return self._base_directive.agg(group_agg)
        
        return self._base_directive

def dectect[T: Detectable](obj: Type[T]):
    return MongoDetector[T](obj)

def open_blob(file :PersistableBlob):
    fs = MongoCollection(type(file).get_meta_state()).get_gridfs()
    if file.has_id():
        return fs.open_download_stream(file.collapse_id())
    else:
        return fs.open_download_stream_by_name(file.filename, revision=-1)

async def open_blob_async(file :PersistableBlob):
    fs = MongoCollection(type(file).get_meta_state()).get_gridfs_async()
    if file.has_id():
        return await fs.open_download_stream(file.collapse_id())
    else:
        return await fs.open_download_stream_by_name(file.filename, revision=-1)