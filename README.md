# Kosmos-Py

**Kosmos-Py** is a high-performance, asynchronous MongoDB ORM/ODM-like framework and data persistence layer for Python. It is designed to establish a consistent, type-safe environment for backend services, combining Pydantic models with MongoDB operations, pandas/polars/pyarrow data science integration, secret resolution, timezone-aware timeframing, and hierarchical execution profiling.

---

## Table of Contents
1. [Core Philosophy & Architecture](#1-core-philosophy--architecture)
2. [Ignition & Configuration](#2-ignition--configuration)
3. [Liminal Configuration & Secrets](#3-liminal-configuration--secrets)
4. [Defining Models & Lifecycles](#4-defining-models--lifecycles)
5. [Atomic Counters](#5-atomic-counters)
6. [Field Transformers & Custom Metadata](#6-field-transformers--custom-metadata)
7. [Querying and Filtering (`MongoDetector`)](#7-querying-and-filtering-mongodetector)
8. [Data Saving & Recording (`MongoRecorder`)](#8-data-saving--recording-mongorecorder)
9. [GridFS Blobs (`PersistableBlob`)](#9-gridfs-blobs-persistableblob)
10. [Time & Profiling Utilities](#10-time--profiling-utilities)

---

## 1. Core Philosophy & Architecture

* **State of Matter (`ModelState`)**:
  * `Unset`: The model exists only in memory and has not been prepared for database synchronization.
  * `Transition`: The model is collapsing its changes into a database instruction representation.
  * `Material`: The model is fully synchronized/entangled with the database and is considered stable.
* **Collapse (`collapse()`)**: Compiles the current attributes of a model instance (including auto-timestamps, atomic increments, etc.) into a database update instruction representation (`Ripple`).
* **Decohere (`decohere()`)**: Finalizes the model's state in-memory after database update confirmation (e.g. converting a delta increment to a static value, setting IDs).

---

## 2. Ignition & Configuration

Before interacting with databases or configuration properties, you must ignite the environment using [ignite](./kosmos/ignition.py#L12).

```python
import kosmos as km

# Load environment variables and initialize standard observers
km.ignite("app.env")
```

The configuration is mapped to connection affinities using [PurposeAffinity](./kosmos/mongo/client.py#L11):
* `PurposeAffinity.Observer`: Read-only / read-heavy connections (uses `MONGODB_URI`).
* `PurposeAffinity.Creator`: Write / creation operations (uses `MONGODB_CREATOR_URI`).
* `PurposeAffinity.Admin`: Schema modification / administrative operations (uses `MONGODB_ADMIN_URI`).

---

## 3. Liminal Configuration & Secrets

Kosmos-Py provides a configuration mapper called [LiminalStructure](./kosmos/ether/struct.py#L23) that matches environment variables to Python dataclass fields using the [MapStruct](./kosmos/ether/struct.py#L5) annotation.

### Liminal Configuration Dataclass
```python
from dataclasses import dataclass
from typing import Annotated
import kosmos as km

@dataclass
class CustomAppConstants:
    app_port: Annotated[str, km.ether.MapStruct("PORT")] = "8080"
    db_name: Annotated[str, km.ether.MapStruct("DB_NAME")] = "default_db"

# Wrap inside LiminalStructure to enable lazy environment resolution
liminal_constants = km.ether.struct.LiminalStructure(CustomAppConstants())

# Retrieve resolved constants
constants = liminal_constants.collapse()
print(constants.db_name)
```

### Secrets Resolution
If strings in your environment configuration follow the `__secret:SECRET_NAME:VERSION__` pattern, Kosmos-Py will automatically intercept them and query Google Cloud Secret Manager via [GCPSecretManager](./kosmos/ether/secret.py#L52).

```env
# Example Env File: app.env
PROJECT_ID=my-gcp-project-123
MONGODB_URI=mongodb://user:__secret:mongodb-prod-password:latest__@localhost:27017/prod
```
When [ignite](./kosmos/ignition.py#L12) parses the URI, the secret is resolved invisibly to the caller, and credentials are masked during standard logging.

---

## 4. Defining Models & Lifecycles

All models inherit from [Model](./kosmos/meta/model.py#L11) (a Pydantic wrapper mapping `id` to `_id`) and [ParticleBase](./kosmos/matter/persistable.py#L15) (handling DB metadata), or [Persistable](./kosmos/matter/persistable.py#L144) (which adds automatic creation and update timestamps).

To declare database mappings, use the [@declare_persist_db](./kosmos/meta/state.py#L36) decorator.

```python
from bson import ObjectId
from pydantic import Field
import kosmos as km

@km.declare_persist_db(db_name="store_db", collection_name="products", version=1)
class Product(km.Persistable):
    name: str = Field(alias="title")
    price: float
    category_id: ObjectId | None = None
```

### Lifecycle & Update Tracking
When a model is instantiated directly, it is marked as modified (`has_update = True`). When loaded from the database, it is clean (`has_update = False`). To force-mark a model as needing preservation on save, use [mark_updated()](./kosmos/meta/model.py#L74).

```python
# Query database
detector = km.MongoDetector[Product](Product)
product = detector.filter(km.fld("title") == "Laptop").load_one()

# Modify properties and notify the persistence layer
product.price = 1200.00
product.mark_updated()

# Save modifications back to MongoDB
km.record(product)
```

---

## 5. Atomic Counters

For concurrent systems, Kosmos-Py provides [IncrCounter](./kosmos/meta/atomic.py#L81) (aliased to [IntCounter](./kosmos/meta/atomic.py#L11) / [ZeroCounter](./kosmos/meta/atomic.py#L71)), which compiles to MongoDB `$inc` operations.

```python
import kosmos as km
from pydantic import Field

@km.declare_persist_db(db_name="store_db", collection_name="stock_inventory")
class Inventory(km.Persistable):
    item_id: str
    stock: km.IncrCounter = Field(default=km.ZeroCounter)

# Initialize Inventory
inv = Inventory(item_id="sku-102")
km.record(inv)

# Load and increment atomically
detector = km.detect(Inventory)
loaded_inv = detector.filter(km.fld("item_id") == "sku-102").load_one()

loaded_inv.stock += 5  # Queues an atomic increment of +5
km.record(loaded_inv)  # Sends {"$inc": {"stock": 5}} to MongoDB
```

---

## 6. Field Transformers & Custom Metadata

Kosmos-Py uses type annotations to hook lifecycle transformations into Pydantic models.

| Annotation / Type | Target Operations | Action |
| :--- | :--- | :--- |
| `StrUpper` | Initialization / Set | Converts string to uppercase |
| `StrLower` | Initialization / Set | Converts string to lowercase |
| `TimeInserted` | Document Creation | Automatically sets current UTC timestamp once on creation |
| `TimeUpdated` | Document Update | Sets current UTC timestamp on every save |

### Example Hook Usage:
```python
import kosmos as km
from typing import Annotated

@km.declare_persist_db(db_name="analytics_db", collection_name="logs")
class LogEntry(km.ParticleBase):
    log_level: km.meta.annotation.StrUpper  # Always converts e.g. "info" to "INFO"
    message: str
    created_at: km.meta.annotation.TimeInserted  # Auto set on insert
    updated_at: km.meta.annotation.TimeUpdated   # Auto updated on save
```

---

## 7. Querying and Filtering (`MongoDetector`)

The [MongoDetector](./kosmos/mongo/detector.py#L44) class (instantiated with `km.detect(Model)`) exposes a chainable query builder supporting projection, filtering, pagination, lookups, aggregation, and conversion to standard scientific formats.

### Fluent Aggregation & Querying
```python
import kosmos as km

detector = km.detect(Product)

# Chain filters and lookup pipelines
results = (
    detector
    .filter((km.fld("price") > 100) & (km.fld("category") == "electronics"))
    .sort("price", descending=True)
    .skip(10)
    .limit(5)
    .load_many()
)
```

### Type Resolution & Aliasing
Using [fld()](./kosmos/__init__.py#L16) automatically resolves your Pydantic alias fields to their DB representation.
```python
# In Product, "name" is aliased to "title"
# km.fld("name") compiles to query field: "title"
product = detector.filter(km.fld("name") == "UltraBook").load_one()
```

### Loading to Pandas, Polars, and PyArrow
Kosmos-Py natively outputs your query results as data science containers using `pymongoarrow`:
```python
# Load query results directly to Pandas
df_pandas = detector.filter(km.fld("price") > 50).load_dataframe()

# Load query results directly to Polars
df_polars = detector.filter(km.fld("price") > 50).load_polars()

# Load query results directly to PyArrow Table
arrow_table = detector.filter(km.fld("price") > 50).load_table()
```

### Async Operations
All loading and aggregation pipeline methods support async execution:
```python
# Async load query
await detector.filter(km.fld("price") > 500).load_one_async()
await detector.filter(km.fld("price") > 500).load_many_async()
```

---

## 8. Data Saving & Recording (`MongoRecorder`)

Saving and updating operations are handled by [MongoRecorder](./kosmos/mongo/recorder.py#L17) or the wrapper functions `km.record(obj)` and `km.record_async(obj)`.

### Single Document Saving
```python
# Sync saving
km.record(product)

# Async saving
await km.record_async(product)
```

### Dataframe Bulk Operations
You can bulk insert or upsert DataFrames containing hundreds of rows using bulk write queries.

```python
import pandas as pd
import kosmos as km

recorder = km.MongoRecorder(Product)
df = pd.DataFrame([
    {"title": "Tablet A", "price": 299.99},
    {"title": "Tablet B", "price": 499.99}
])

# Insert bulk rows into database
recorder.insert_dataframe(df)

# Upsert dataframes based on specific keys
recorder.update_dataframe(df, on=["title"], upsert=True)
```

---

## 9. GridFS Blobs (`PersistableBlob`)

For storing large files, inherit from [PersistableBlob](./kosmos/matter/blob.py#L6) and specify `is_blob=True` in your DB declaration. Kosmos-Py manages upload, metadata association, and deletes old chunks from GridFS automatically when files are replaced.

```python
from typing import Optional
import io
import kosmos as km

@km.declare_persist_db(db_name="files_db", collection_name="attachments", is_blob=True)
class DocumentAttachment(km.PersistableBlob):
    data: bytes = b""
    metadata: Optional[dict] = None

    def dump_buffer(self) -> io.BytesIO:
        return io.BytesIO(self.data)

# 1. Upload a new file
new_attachment = DocumentAttachment(
    filename="invoice.pdf",
    data=b"Raw PDF bytes content",
    metadata={"customer_id": "1002"}
)
km.record(new_attachment)  # Uploads to GridFS

# 2. Retrieve file content
detector = km.detect(DocumentAttachment)
loaded = detector.filter(km.fld("filename") == "invoice.pdf").load_one()

# Open download stream to read contents
stream = km.open_blob(loaded)
file_bytes = stream.read()
print(file_bytes)
```

Both sync (`open_blob`, `record`) and async (`open_blob_async`, `record_async`) methods are supported.

---

## 10. Time & Profiling Utilities

### Timeframes and Chronological Alignment
Kosmos-Py has a robust [TimeFrame](./kosmos/time/timeframing.py#L31) utility mapping to specific time bounds (hourly, daily, weekly, monthly, quarterly, yearly).

```python
from datetime import datetime, timezone
import kosmos.time as kt

moment = datetime(2026, 6, 1, 15, 0, 0, tzinfo=timezone.utc)

# Align date to Daily bounds
day_frame = kt.DailyFrame.create(moment=moment, tzone=timezone.utc)
print(day_frame.floor)    # 2026-06-01 00:00:00+00:00
print(day_frame.ceiling)  # 2026-06-02 00:00:00+00:00

# Jump to previous time frames
yesterday = day_frame.get_previous_frame()
last_week = day_frame.get_previous_x_frame(7)
```

### Performance & Nested Profiling
Profile code blocks hierarchically using [PerfTimer](file:///Users/eddao/projects/kosmos-py/kosmos/time/perftime.py#L7) or the [@timed](file:///Users/eddao/projects/kosmos-py/kosmos/time/perftime.py#L108) decorator.

```python
import kosmos.time as kt
import time

@kt.timed(name="Fetch API Data")
def fetch_api(ptimer=None):
    time.sleep(0.1)

@kt.timed(name="Process DB Records")
def process_db(ptimer=None):
    # Pass ptimer to record nested timer calls
    time.sleep(0.05)
    fetch_api(ptimer=ptimer)

# Run operations inside a parent timer scope
with kt.PerfTimer("Main Flow", verbose=True) as root_timer:
    process_db(ptimer=root_timer)
    
# Prints output similar to:
# Main Flow -> 1 times in 150.00 ms
# └── Process DB Records -> 1 times in 150.00 ms (100.0%)
# |  └── Fetch API Data -> 1 times in 100.00 ms (66.7%)
```
