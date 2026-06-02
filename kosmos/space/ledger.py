from kosmos.matter.particle import Stasion
from kosmos.meta.annotation import TimeUpdated
from kosmos.meta.expression.filter import QueryPredicates
from .detector import detect
from .recorder import recorder
from pydantic import Field

class Ledger(Stasion):
    updated_time: TimeUpdated = Field(
        description="Timestamp of the last update.", default=None
    )
    
    @classmethod
    def detect(cls, filter: QueryPredicates|None = None):
        detector = detect(cls)
        if filter is not None:
            detector = detector.filter(filter)
        return detector

    @classmethod
    def recorder(cls):
        return recorder(cls)
    
    def persist(self):
        self.recorder().record(self)
    
    async def persist_async(self):
        await self.recorder().record_async(self)