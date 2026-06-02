from kosmos.meta.expression.base import combine_field_specifications
from kosmos.meta.expression.base import ExpressionDriver
from typing import Type, List, Self
from kosmos.meta.expression.base import FieldSpecification
from .detector import MongoDetector
from kosmos.meta.model import Model
from kosmos.meta.state import MetaState

class Projector[T: Model]:
    def __init__(self, obj_type: Type[T]):
        self.obj_type = obj_type
        self.fields: FieldSpecification | None = None

    def Project(self, *fields: FieldSpecification) -> Self:
        self.fields = combine_field_specifications(*fields)
        return self
        
    def From(self, detector: MongoDetector) -> MongoDetector[T]:
        if detector.meta_state.is_blob:
            raise ValueError("Blob types cannot be projected")
        
        meta = detector.meta_state
        
        expression_driver = ExpressionDriver(self.obj_type.model_fields)
        assert self.fields is not None, "No fields have been projected"
        field_spec = self.fields.express(expression_driver)
        stages = detector.get_op_stages().project(field_spec)
        retval = MongoDetector[T](meta_state=meta, obj_type=self.obj_type)
        retval._aggregation_expr = stages
        return retval
        
