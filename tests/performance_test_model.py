from datetime import datetime
from typing import Optional

import kosmos as km

@km.declare_persist_db(collection_name="perf_test_data", db_name="test_db")
class PerformanceTestModel(km.Persistable):
    name: str
    value: float
    value2: float
    date: Optional[datetime] = None
    notes: str
