import pytest
from pydantic.fields import FieldInfo
from typing import Annotated

from kosmos.meta.expression.base import (
    FieldName,
    FieldPath,
    LiteralInput,
    to_expr,
    ExpressionDriver,
    Expression
)
from kosmos.meta.annotation import NormalizeQueryInput

def test_field_name_expression():
    f = FieldName("my_field")
    assert f.repr_value == "my_field"
    
    driver = ExpressionDriver({"my_field": FieldInfo(alias="aliased_field")})
    assert f.express(driver) == "aliased_field"
    assert f.express() == "my_field"

def test_field_path_expression():
    fp = FieldPath("my_field")
    assert fp.repr_value == "$my_field"
    
    driver = ExpressionDriver({"my_field": FieldInfo(alias="aliased_field")})
    assert fp.express(driver) == "$aliased_field"
    assert fp.express() == "$my_field"

def test_literal_input_expression():
    li = LiteralInput("hello")
    assert li.repr_value == "hello"
    assert li.express() == "hello"
    
    # Test with Norm annotation
    li.for_fld("norm_field")
    driver = ExpressionDriver({
        "norm_field": FieldInfo.from_annotation(
            Annotated[str, NormalizeQueryInput(str.upper)]
        )
    })
    assert li.express(driver) == "HELLO"

def test_to_expr():
    e1 = to_expr("some_field")
    assert isinstance(e1, FieldPath)
    assert e1.repr_value == "$some_field"
    
    e2 = to_expr(123)
    assert isinstance(e2, LiteralInput)
    assert e2.repr_value == 123
    
    e3 = to_expr(e1)
    assert e3 is e1

def test_is_empty():
    class DummyExpression(Expression):
        def __init__(self, value):
            self.value = value
            
        @property
        def repr_value(self):
            return self.value

    # None
    assert DummyExpression(None).is_empty() is True
    
    # Empty sequence
    assert DummyExpression([]).is_empty() is True
    assert DummyExpression({}).is_empty() is True
    
    # Non-empty sequence
    assert DummyExpression([1]).is_empty() is False
    assert DummyExpression({"a": 1}).is_empty() is False
    
    # Nested expression
    assert DummyExpression(DummyExpression(None)).is_empty() is True
    assert DummyExpression(DummyExpression([1])).is_empty() is False
    
    # Non-sequence type (like integer) - should return False, and NOT raise TypeError
    assert DummyExpression(123).is_empty() is False
    assert DummyExpression(True).is_empty() is False
