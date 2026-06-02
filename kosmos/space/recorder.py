from kosmos.matter.observable import Observable
from kosmos.mongo.recorder import MongoRecorder


def recorder(obj_type: type) -> MongoRecorder:
    return MongoRecorder(obj_type)

def record(obj: Observable):
    MongoRecorder(obj.__class__).record(obj)

async def record_async(obj: Observable):
    await MongoRecorder(obj.__class__).record_async(obj)