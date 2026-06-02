from kosmos.meta.annotation import TimeInserted, TimeUpdated
from kosmos.matter.persistable import ParticleBase

from pydantic import Field

class Persistable(ParticleBase):
    updated_time: TimeUpdated = Field(
        description="Timestamp of the last update.", default=None
    )
    
    created_at: TimeInserted = Field(
        description="Entity Created Time (does not exist if entity has not been persisted)",
        default=None,
    )

