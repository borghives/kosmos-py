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
            # pyrefly: ignore [bad-argument-type]
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

def test_recursive_alias_resolution():
    from pydantic import BaseModel, Field
    
    class Profile(BaseModel):
        first_name: str = Field(alias="fname")
        last_name: str = Field(alias="lname")
        
    class User(BaseModel):
        profile_info: Profile = Field(alias="pinfo")
        username: str = Field(alias="uname")
        
    driver = ExpressionDriver(User.model_fields)
    
    f1 = FieldName("profile_info.first_name")
    assert f1.express(driver) == "pinfo.fname"
    
    f2 = FieldPath("profile_info.last_name")
    assert f2.express(driver) == "$pinfo.lname"
    
    # Non-existing nested fields should just resolve as their names
    f3 = FieldName("profile_info.age")
    assert f3.express(driver) == "pinfo.age"

def test_to_expr_generic():
    e1 = to_expr(3.14)
    assert isinstance(e1, LiteralInput)
    assert e1.express() == 3.14
    
    e2 = to_expr(True)
    assert isinstance(e2, LiteralInput)
    assert e2.express() is True

def test_none_comparison_queries():
    from kosmos.meta.expression.field import QueryableField
    
    q_field = QueryableField("status")
    
    # Status == None should map to is_null
    pred_eq = q_field == None
    assert pred_eq.express() == {"status": None}
    
    # Status != None should map to is_not_null
    pred_ne = q_field != None
    assert pred_ne.express() == {"status": {"$ne": None}}

def test_constructor_auto_to_expr():
    from kosmos.meta.expression.acc_op import Sum
    from kosmos.meta.expression.op import ToInt, Add, Switch
    
    # Sum should wrap "amount" in FieldPath ("$amount")
    s = Sum("amount")
    assert s.express() == {"$sum": "$amount"}
    
    # ToInt should wrap "age" in FieldPath
    t = ToInt("age")
    assert t.express() == {"$toInt": "$age"}
    
    # Add should wrap both arguments
    a = Add("value", 5)
    assert a.express() == {"$add": ["$value", 5]}
    
    # Switch cases and thens
    sw = Switch(
        branches=[{"case": "is_active", "then": "active"}],
        default="inactive"
    )
    assert sw.express() == {
        "$switch": {
            "branches": [
                {"case": "$is_active", "then": "$active"}
            ],
            "default": "$inactive"
        }
    }

def test_helper_functions_return_expressions():
    from kosmos.meta.expression.op import divide, multiply, add, sanitize_number, to_double, to_int, to_upper, to_lower, to_date_alignment
    
    assert isinstance(divide("num", "den"), Expression)
    assert divide("num", "den").express() == {"$divide": ["$num", "$den"]}
    
    assert isinstance(multiply("a", "b"), Expression)
    assert multiply("a", "b").express() == {"$multiply": ["$a", "$b"]}
    
    assert isinstance(add("a", "b"), Expression)
    assert add("a", "b").express() == {"$add": ["$a", "$b"]}
    
    assert isinstance(sanitize_number("val", 10), Expression)
    assert sanitize_number("val", 10).express() == {"$ifNull": ["$val", 10]}
    
    assert isinstance(to_double("val"), Expression)
    assert to_double("val").express() == {"$convert": {"input": "$val", "to": "double"}}
    
    assert isinstance(to_int("val"), Expression)
    assert to_int("val").express() == {"$convert": {"input": "$val", "to": "int"}}
    
    assert isinstance(to_upper("val"), Expression)
    assert to_upper("val").express() == {"$toUpper": "$val"}
    
    assert isinstance(to_lower("val"), Expression)
    assert to_lower("val").express() == {"$toLower": "$val"}
    
    assert isinstance(to_date_alignment("val", 8), Expression)
    assert to_date_alignment("val", 8).express() == {"$toDate": {"$concat": ["$val", "T08:00:00.000Z"]}}

def test_aggregation_stages_alias_resolution():
    from kosmos.meta.expression.aggregation import Aggregation
    from pydantic import Field, BaseModel
    
    class Item(BaseModel):
        quantity: int = Field(alias="qty")
        price: float = Field(alias="prc")
        
    class Order(BaseModel):
        items: list[Item] = Field(alias="its")
        customer_id: str = Field(alias="cust_id")
        
    driver = ExpressionDriver(Order.model_fields)
    
    # test lookup stage resolving localField
    agg = Aggregation().lookup(
        foreignCollection="customers",
        localField="customer_id",
        foreignField="id",
        toField="customer"
    )
    assert agg.express(driver) == [
        {
            "$lookup": {
                "from": "customers",
                "localField": "cust_id",
                "foreignField": "id",
                "as": "customer"
            }
        }
    ]
    
    # test unwind resolving path
    agg2 = Aggregation().unwind("items")
    assert agg2.express(driver) == [{"$unwind": "$its"}]
    
    agg3 = Aggregation().unwind("$items")
    assert agg3.express(driver) == [{"$unwind": "$its"}]

def test_logical_flattening_and_empty_combinations():
    from kosmos.meta.expression.field import QueryableField
    from kosmos.meta.expression.filter import QueryPredicates
    
    q_name = QueryableField("name")
    q_age = QueryableField("age")
    q_active = QueryableField("active")
    
    q1 = q_name == "Alice"
    q2 = q_age > 18
    q3 = q_active == True
    
    # Flattening: (q1 & q2) & q3 should compile to And([q1, q2, q3])
    and_all = (q1 & q2) & q3
    assert and_all.express() == {
        "$and": [
            {"name": "Alice"},
            {"age": {"$gt": 18}},
            {"active": True}
        ]
    }
    
    # Empty handling: empty filters should be bypassed in & and |
    empty = QueryPredicates()
    assert (empty & q1).express() == {"name": "Alice"}
    assert (q1 & empty).express() == {"name": "Alice"}
    assert (empty | q1).express() == {"name": "Alice"}
    assert (q1 | empty).express() == {"name": "Alice"}
    
    # Or flattening
    or_all = (q1 | q2) | q3
    assert or_all.express() == {
        "$or": [
            {"name": "Alice"},
            {"age": {"$gt": 18}},
            {"active": True}
        ]
    }

def test_timezone_date_operators():
    from kosmos.meta.expression.op import Year, Hour
    
    # Timezone as a string literal America/New_York
    y1 = Year("created_at", timezone="America/New_York")
    assert y1.express() == {
        "$year": {
            "date": "$created_at",
            "timezone": "America/New_York"
        }
    }
    
    # Timezone as a FieldPath
    h1 = Hour("updated_time", timezone=FieldName("tz_field"))
    assert h1.express() == {
        "$hour": {
            "date": "$updated_time",
            "timezone": "tz_field"
        }
    }

def test_nested_list_alias_resolution():
    from pydantic import BaseModel, Field
    
    class Item(BaseModel):
        quantity: int = Field(alias="qty")
        price: float = Field(alias="prc")
        
    class Order(BaseModel):
        items: list[Item] = Field(alias="its")
        customer_id: str = Field(alias="cust_id")
        
    driver = ExpressionDriver(Order.model_fields)
    
    f1 = FieldPath("items.price")
    assert f1.express(driver) == "$its.prc"
    
    f2 = FieldName("items.quantity")
    assert f2.express(driver) == "its.qty"

def test_new_mql_operators():
    from kosmos.meta.expression.query import Nin, Nor, Expr, ElemMatch, Regex
    from kosmos.meta.expression.op import StrCaseCmp, SubstrBytes, Week
    from kosmos.meta.expression.aggregation import Aggregation
    
    # 1. Nin 
    n1 = Nin([1, 2, 3])
    assert n1.express() == {"$nin": [1, 2, 3]}
    
    # 2. Nor
    nor1 = Nor([{"a": 1}, {"b": 2}])
    assert nor1.express() == {"$nor": [{"a": 1}, {"b": 2}]}
    
    # 3. Expr
    expr1 = Expr({"$gt": ["$field1", "$field2"]})
    assert expr1.express() == {"$expr": {"$gt": ["$field1", "$field2"]}}
    
    # 4. ElemMatch
    em = ElemMatch({"product": "book", "qty": {"$gt": 5}})
    assert em.express() == {"$elemMatch": {"product": "book", "qty": {"$gt": 5}}}
    
    # 5. Regex
    r1 = Regex("^A", options="i")
    assert r1.express() == {"$regex": "^A", "$options": "i"}
    r2 = Regex("^B")
    assert r2.express() == {"$regex": "^B"}
    
    # 6. StrCaseCmp
    s1 = StrCaseCmp("str1", "str2")
    assert s1.express() == {"$strcasecmp": ["$str1", "$str2"]}
    
    # 7. SubstrBytes
    sb = SubstrBytes("my_str", 1, 3)
    assert sb.express() == {"$substrBytes": ["$my_str", 1, 3]}
    
    # 8. Week
    w = Week("my_date", timezone="UTC")
    assert w.express() == {
        "$week": {
            "date": "$my_date",
            "timezone": "UTC"
        }
    }
    
    # 9. Aggregation
    agg = Aggregation().match({"status": "A"}).limit(5)
    assert agg.express() == [{"$match": {"status": "A"}}, {"$limit": 5}]
