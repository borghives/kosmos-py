

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Union, get_origin, get_args, Annotated, List, Set
import types
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from kosmos.meta.util import coalesce
from kosmos.meta.annotation import NormalizeQueryInput

def get_model_fields_from_annotation(annotation: Any) -> Optional[dict]:
    if annotation is None:
        return None
    # Handle Annotated
    if get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    
    # Handle Union/Optional
    origin = get_origin(annotation)
    if origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType):
        for arg in get_args(annotation):
            if arg is not type(None):
                fields = get_model_fields_from_annotation(arg)
                if fields:
                    return fields
    
    # Handle List/Sequence/Set/Dict/etc.
    if origin in (list, set, dict, List, Set, Dict):
        args = get_args(annotation)
        if args:
            target = args[-1]
            fields = get_model_fields_from_annotation(target)
            if fields:
                return fields
                
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation.model_fields
    return None

class ExpressionDriver:
    """
    Handles the conversion of abstract `Expression` objects into concrete MongoDB queries.

    This class is responsible for:
    - Marshalling `Expression` objects into their MongoDB representation.
    - Resolving field names to their database aliases.
    - Applying any query-time value transformations associated with a model field.
    """

    def __init__(self, model_fields: dict[str, FieldInfo]):
        self.model_fields = model_fields

    def get_alias(self, field_name: str) -> str:
        parts = field_name.split(".")
        resolved_parts = []
        current_fields = self.model_fields
        
        for part in parts:
            if not current_fields:
                resolved_parts.append(part)
                continue
            
            field_info = current_fields.get(part)
            if field_info is None:
                resolved_parts.append(part)
                current_fields = None
            else:
                alias = field_info.alias or part
                resolved_parts.append(alias)
                current_fields = get_model_fields_from_annotation(field_info.annotation)
                
        return ".".join(resolved_parts)
    
    def get_transformers(self, field_name: str) -> list:
        parts = field_name.split(".")
        current_fields = self.model_fields
        field_info = None
        
        for part in parts:
            if not current_fields:
                field_info = None
                break
            field_info = current_fields.get(part)
            if field_info is None:
                break
            current_fields = get_model_fields_from_annotation(field_info.annotation)
            
        if field_info is None:
            return []
        metadata = field_info.metadata
        return [item for item in metadata if isinstance(item, NormalizeQueryInput)]

    def marshal(self, value: Any) -> Any:
        if isinstance(value, Expression):
            return value.express(self)
        if isinstance(value, dict):
            return {self.marshal(k): self.marshal(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.marshal(v) for v in value if v is not None]
        if isinstance(value, tuple):
            return tuple(self.marshal(v) for v in value if v is not None)
        if isinstance(value, set):
            return {self.marshal(v) for v in value if v is not None}
        return value

class Expression(ABC):
    """
    An abstract representation of an object that can be converted into a MongoDB expression.

    This serves as the base class for various query components, such as filters,
    sort operators, and field predicates.
    """

    @property
    @abstractmethod
    def repr_value(self) -> Any:
        """
        Returns the raw representation of the expression before final marshalling.
        
        This property should return the internal state of the expression as a
        Python primitive (dict, list, value) that the `ExpressionDriver` will
        recursively traverse and resolve (e.g. resolving `FieldName` to aliases).
        """
        pass
    
    def express(self, driver: Optional[ExpressionDriver] = None) -> Any:
        if driver is None:
            driver = ExpressionDriver({})
        
        return driver.marshal(self.repr_value) if driver else self.repr_value
    
    def is_empty(self) -> bool:
        value = self.repr_value
        if value is None:
            return True
        
        if isinstance(value, dict):
            return len(value) == 0
        
        if isinstance(value, list):
            return len(value) == 0
    
        if isinstance(value, Expression):
            return value.is_empty()
        
        if not hasattr(value, "__len__"):
            return False
        
        return len(value) == 0


class FieldName(Expression):
    """
    An expression representing a field name that can be resolved to a database alias.
    """
    def __init__ (self, field_name: str):
        self.field_name = field_name

    @property
    def repr_value(self):
        return self.field_name

    def express(self, driver: Optional[ExpressionDriver] = None) -> Any:
        return driver.get_alias(self.repr_value) if driver else self.repr_value
    
class FieldPath(Expression):
    """
    An expression representing a field path used in aggregation expressions.

    Field paths are prefixed with a `$` sign in MongoDB aggregation pipelines.
    """
    def __init__ (self, field_name: str ):
        self.field_name = field_name

    @property
    def repr_value(self):
        return f"${self.field_name}"

    def express(self, driver: Optional[ExpressionDriver] = None) -> Any:
        field_alias = driver.get_alias(self.field_name) if driver else self.field_name
        return f"${field_alias}"
        
class LiteralInput(Expression):
    """
    An expression representing a literal value used in a query predicate.

    This wrapper allows query-time transformations to be applied to the value
    based on the model field's annotations.
    """
    def __init__ (self, literal_input):
        self.literal_input = literal_input
        self.linked_field_name = ""

    def for_fld(self, field_name: str) -> "LiteralInput":
        self.linked_field_name = field_name
        return self

    @property
    def repr_value(self):
        return self.literal_input

    def express(self, driver: Optional[ExpressionDriver] = None) -> Any:
        if driver is None or not self.linked_field_name:
            return self.repr_value
        
        transformers = driver.get_transformers(self.linked_field_name)
        return coalesce(self.repr_value, transformers)

def to_expr(expr_input: Any) -> Expression:
    if isinstance(expr_input, Expression):
        return expr_input
    if isinstance(expr_input, str):
        return FieldPath(expr_input)
    return LiteralInput(expr_input)

class OpExpression(Expression):
    @classmethod
    def of(cls, *inputs: Expression | str | int, **kwargs) -> "OpExpression":
        """
        Creates an instance of this class from a list of expressions or strings.
        """
        input_exprs = [to_expr(input) for input in inputs]
        return cls(*input_exprs, **kwargs)

         

class AccOpExpression(Expression):
    @classmethod
    def of(cls, *inputs: Expression | str | int, **kwargs) -> "AccOpExpression":
        """
        Creates an instance of this class from a list of expressions or strings.
        """
        input_exprs = [to_expr(input) for input in inputs]
        return cls(*input_exprs, **kwargs)

class MapExpression(Expression) :
    def __init__(self, accumulate: Optional[Dict] = None) -> None:
        self._value = accumulate if accumulate is not None else {}

    @property
    def repr_value(self):
        return self._value
    
    def __or__(self, other):
        """
        Combines this filter with another
        """
        if other is None:
            return self

        cls = self.__class__

        if not isinstance(other, cls):
            other = cls(other)

        if self.is_empty():
            return other
        
        if other.is_empty():
            return self

        self_clauses = self.repr_value
        other_clauses = other.repr_value

        assert isinstance(self_clauses, dict)
        assert isinstance(other_clauses, dict)
        combined = self_clauses | other_clauses
                
        return cls(combined)

# #output for field
# class GroupAccumulators(MapExpression):
#     """
#     An expression that represents a MongoDB query predicate (the part of a `find`
#     operation that selects documents).

#     Accumulator can be combined using with `|` operators.

#     ref: https://www.mongodb.com/docs/manual/reference/operator/aggregation/group/#std-label-accumulators-group
#     """
#     def __init__(self, accumulate: Optional[Dict] = None) -> None:
#         super().__init__(accumulate)

class FieldSpecification (MapExpression):
    """
    for group by:
    ref: https://www.mongodb.com/docs/manual/reference/operator/aggregation/group/#std-label-accumulators-group

    for project
    ref: https://www.mongodb.com/docs/manual/reference/operator/aggregation/project/
    """
    def __init__(self, specification: Optional[Dict] = None) :
        super().__init__(specification)


class GroupExpression(Expression):
    def __init__(self, key: Any):
        self.key = to_expr(key) if key is not None else None
        self.accumulators : Optional[FieldSpecification] = None

    @property
    def repr_value(self) -> dict:
        group_expr  : dict = {"_id" : self.key}
        if self.accumulators:
            value = self.accumulators.repr_value
            assert isinstance(value, dict)
            group_expr.update(value)

        return group_expr
    
    def with_acc(self, accumulators: FieldSpecification) -> "GroupExpression":
        self.accumulators = accumulators
        return self
    
def combine_field_specifications(*specifications: FieldSpecification | dict) -> Optional[FieldSpecification]:
    combined_dict = {}
    for specification in specifications:
        if specification is None:
            continue
        if isinstance(specification, FieldSpecification):
            val = specification.repr_value
        elif isinstance(specification, dict):
            val = specification
        else:
            raise TypeError(f"Unsupported specification type: {type(specification)}")
        
        assert isinstance(val, dict)
        combined_dict.update(val)
                    
    return FieldSpecification(combined_dict) if combined_dict else None