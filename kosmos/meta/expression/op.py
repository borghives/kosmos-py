from typing import Optional, List, Any, Union, Dict
from datetime import datetime
from kosmos.meta.expression.base import Expression, OpExpression, to_expr, LiteralInput
from kosmos.time.timeframing import TimeFrame
from kosmos.time.util import to_utc_aware


class ToInt(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toInt": self.input}

class ToDouble(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toDouble": self.input}

class ToLong(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toLong": self.input}

class ToDecimal(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toDecimal": self.input}

class Abs(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$abs": self.input}

class Subtract(OpExpression):
    def __init__(self, input1: Any, input2: Any) -> None:
        self.input1 = to_expr(input1)
        self.input2 = to_expr(input2)

    @property
    def repr_value(self):
        return {"$subtract": [self.input1, self.input2]}

class Add(OpExpression):
    def __init__(self, input1: Any, input2: Any) -> None:
        self.input1 = to_expr(input1)
        self.input2 = to_expr(input2)

    @property
    def repr_value(self):
        return {"$add": [self.input1, self.input2]}

class DateToString(OpExpression):
    def __init__(self, input: Any, format: str, timezone: Optional[Any] = None) -> None:
        self.input = to_expr(input)
        self.format = format
        self.timezone: Expression | None = None
        
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)
        
    @property
    def repr_value(self):
        date_to_string = {"format": self.format, "date": self.input}

        if self.timezone:
            date_to_string["timezone"] = self.timezone

        return {"$dateToString": date_to_string}


def _date_op_repr(op: str, date: Expression, timezone: Optional[Expression] = None):
    if timezone:
        return {op: {"date": date, "timezone": timezone}}
    return {op: date}

class Multiply(OpExpression):
    def __init__(self, *inputs: Any) -> None:
        self.inputs = [to_expr(x) for x in inputs]

    @property
    def repr_value(self):
        return {"$multiply": list(self.inputs)}

class Divide(OpExpression):
    def __init__(self, input1: Any, input2: Any) -> None:
        self.input1 = to_expr(input1)
        self.input2 = to_expr(input2)

    @property
    def repr_value(self):
        return {"$divide": [self.input1, self.input2]}

class Mod(OpExpression):
    def __init__(self, input1: Any, input2: Any) -> None:
        self.input1 = to_expr(input1)
        self.input2 = to_expr(input2)

    @property
    def repr_value(self):
        return {"$mod": [self.input1, self.input2]}

class Pow(OpExpression):
    def __init__(self, number: Any, exponent: Any) -> None:
        self.number = to_expr(number)
        self.exponent = to_expr(exponent)

    @property
    def repr_value(self):
        return {"$pow": [self.number, self.exponent]}

class Sqrt(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$sqrt": self.input}

class Exp(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$exp": self.input}

class Ln(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$ln": self.input}

class Log(OpExpression):
    def __init__(self, number: Any, base: Any) -> None:
        self.number = to_expr(number)
        self.base = to_expr(base)

    @property
    def repr_value(self):
        return {"$log": [self.number, self.base]}

class Log10(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$log10": self.input}

class Ceil(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$ceil": self.input}

class Floor(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$floor": self.input}

class Trunc(OpExpression):
    def __init__(self, input: Any, place: Optional[Any] = None) -> None:
        self.input = to_expr(input)
        self.place = to_expr(place) if place is not None else None

    @property
    def repr_value(self):
        if self.place is not None:
             return {"$trunc": [self.input, self.place]}
        return {"$trunc": self.input}

class Round(OpExpression):
    def __init__(self, input: Any, place: Optional[Any] = None) -> None:
        self.input = to_expr(input)
        self.place = to_expr(place) if place is not None else None

    @property
    def repr_value(self):
        if self.place is not None:
             return {"$round": [self.input, self.place]}
        return {"$round": self.input}

class Concat(OpExpression):
    def __init__(self, *inputs: Any) -> None:
        self.inputs = [to_expr(x) for x in inputs]

    @property
    def repr_value(self):
        return {"$concat": list(self.inputs)}

class Substr(OpExpression):
    def __init__(self, string: Any, start: Any, length: Any) -> None:
        self.string = to_expr(string)
        self.start = to_expr(start)
        self.length = to_expr(length)

    @property
    def repr_value(self):
        return {"$substr": [self.string, self.start, self.length]}

class SubstrCP(OpExpression):
    def __init__(self, string: Any, code_point_index: Any, code_point_count: Any) -> None:
        self.string = to_expr(string)
        self.code_point_index = to_expr(code_point_index)
        self.code_point_count = to_expr(code_point_count)

    @property
    def repr_value(self):
        return {"$substrCP": [self.string, self.code_point_index, self.code_point_count]}

class SubstrBytes(OpExpression):
    def __init__(self, string: Any, byte_index: Any, byte_count: Any) -> None:
        self.string = to_expr(string)
        self.byte_index = to_expr(byte_index)
        self.byte_count = to_expr(byte_count)

    @property
    def repr_value(self):
        return {"$substrBytes": [self.string, self.byte_index, self.byte_count]}

class ToLower(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toLower": self.input}

class ToUpper(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toUpper": self.input}

class StrLenBytes(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$strLenBytes": self.input}

class StrLenCP(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$strLenCP": self.input}

class StrCaseCmp(OpExpression):
    def __init__(self, string1: Any, string2: Any) -> None:
        self.string1 = to_expr(string1)
        self.string2 = to_expr(string2)

    @property
    def repr_value(self):
        return {"$strcasecmp": [self.string1, self.string2]}

class ArrayElemAt(OpExpression):
    def __init__(self, array: Any, index: Any) -> None:
        self.array = to_expr(array)
        self.index = to_expr(index)

    @property
    def repr_value(self):
        return {"$arrayElemAt": [self.array, self.index]}

class ConcatArrays(OpExpression):
    def __init__(self, *arrays: Any) -> None:
        self.arrays = [to_expr(x) for x in arrays]

    @property
    def repr_value(self):
        return {"$concatArrays": list(self.arrays)}

class Size(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$size": self.input}

class IsArray(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$isArray": self.input}

class In(OpExpression):
    def __init__(self, element: Any, array: Any) -> None:
        self.element = to_expr(element)
        self.array = to_expr(array)

    @property
    def repr_value(self):
        return {"$in": [self.element, self.array]}

class Year(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$year", self.date, self.timezone)

class Month(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$month", self.date, self.timezone)

class DayOfMonth(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$dayOfMonth", self.date, self.timezone)

class DayOfWeek(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$dayOfWeek", self.date, self.timezone)

class DayOfYear(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$dayOfYear", self.date, self.timezone)

class Hour(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$hour", self.date, self.timezone)

class Minute(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$minute", self.date, self.timezone)

class Second(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$second", self.date, self.timezone)

class Millisecond(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$millisecond", self.date, self.timezone)

class Week(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$week", self.date, self.timezone)

class IsoDayOfWeek(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$isoDayOfWeek", self.date, self.timezone)

class IsoWeek(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$isoWeek", self.date, self.timezone)

class IsoWeekYear(OpExpression):
    def __init__(self, date: Any, timezone: Optional[Any] = None) -> None:
        self.date = to_expr(date)
        self.timezone: Expression | None = None
        if timezone is not None:
            if isinstance(timezone, str) and not timezone.startswith("$"):
                self.timezone = LiteralInput(timezone)
            else:
                self.timezone = to_expr(timezone)

    @property
    def repr_value(self):
        return _date_op_repr("$isoWeekYear", self.date, self.timezone)

class Cond(OpExpression):
    def __init__(self, if_expr: Any, then_expr: Any, else_expr: Any) -> None:
        self.if_expr = to_expr(if_expr)
        self.then_expr = to_expr(then_expr)
        self.else_expr = to_expr(else_expr)

    @property
    def repr_value(self):
        return {"$cond": {"if": self.if_expr, "then": self.then_expr, "else": self.else_expr}}

class IfNull(OpExpression):
    def __init__(self, input: Any, replacement: Any) -> None:
        self.input = to_expr(input)
        self.replacement = to_expr(replacement)

    @property
    def repr_value(self):
        return {"$ifNull": [self.input, self.replacement]}

class Switch(OpExpression):
    def __init__(self, branches: List[dict], default: Optional[Any] = None) -> None:
        self.branches = [{"case": to_expr(b["case"]), "then": to_expr(b["then"])} for b in branches]
        self.default = to_expr(default) if default is not None else None

    @property
    def repr_value(self):
        val: Dict[str, Any] = {"branches": self.branches}
        if self.default is not None:
            val["default"] = self.default
        return {"$switch": val}

class Type(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$type": self.input}

class Convert(OpExpression):
    def __init__(self, input: Any, to: Any, on_error: Optional[Any] = None, on_null: Optional[Any] = None) -> None:
        self.input = to_expr(input)
        self.to: Expression = LiteralInput(to) if isinstance(to, str) and not to.startswith("$") else to_expr(to)
        self.on_error: Expression | None = None 
        self.on_null: Expression | None = None 
        
        if on_error is not None:
            self.on_error = to_expr(on_error)
        
        if on_null is not None:
            self.on_null = to_expr(on_null)

    @property
    def repr_value(self):
        val = {"input": self.input, "to": self.to}
        if self.on_error is not None:
            val["onError"] = self.on_error
        if self.on_null is not None:
            val["onNull"] = self.on_null
        return {"$convert": val}

class ToString(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toString": self.input}

class ToBool(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toBool": self.input}

class ToDate(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toDate": self.input}

class ToObjectId(OpExpression):
    def __init__(self, input: Any) -> None:
        self.input = to_expr(input)

    @property
    def repr_value(self):
        return {"$toObjectId": self.input}


def divide(numerator: Any, denominator: Any) -> Divide:
    return Divide(numerator, denominator)


def multiply(*inputs: Any) -> Multiply:
    return Multiply(*inputs)


def add(a: Any, b: Any) -> Add:
    return Add(a, b)


def sanitize_number(expr: Any, default: int = 0) -> IfNull:
    return IfNull(expr, default)


def to_double(expr: Any) -> Convert:
    return Convert(expr, "double")


def to_int(expr: Any) -> Convert:
    return Convert(expr, "int")


def to_upper(expr: Any) -> ToUpper:
    return ToUpper(expr)


def to_lower(expr: Any) -> ToLower:
    return ToLower(expr)


def to_date_alignment(expr: Any, hour: int) -> ToDate:
    if hour < 0 or hour > 23:
        raise ValueError("Hour must be between 0 and 23")

    return ToDate(Concat(expr, LiteralInput(f"T{hour:02}:00:00.000Z")))


def m_timeframe(windowframe: TimeFrame) -> dict:
    return m_period(windowframe.floor, windowframe.ceiling)


def m_period(floor: datetime, ceiling: datetime) -> dict:
    return {
        "$gte": LiteralInput(to_utc_aware(floor)),
        "$lt": LiteralInput(to_utc_aware(ceiling))
    }
