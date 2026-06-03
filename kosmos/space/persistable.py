from pydantic import Field
from kosmos.meta.expression.filter import QueryPredicates
from kosmos.meta.annotation import TimeInserted, TimeUpdated
from kosmos.matter.particle import ParticleBase
from .detector import detect
from .recorder import recorder


class Persistable(ParticleBase):
    updated_time: TimeUpdated = Field(
        description="Timestamp of the last update.", default=None
    )
    
    created_at: TimeInserted = Field(
        description="Entity Created Time (does not exist if entity has not been persisted)",
        default=None,
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