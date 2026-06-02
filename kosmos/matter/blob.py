from typing import Optional
from datetime import datetime
from pydantic import Field, ConfigDict, BaseModel
from abc import abstractmethod

from .particle import ParticleBase
from .ripple import RippleState, Ripple

import io

class BlobBase(ParticleBase):
    filename: str       = Field(default="")
    metadata: dict|None = Field(default=None)
    # GridFS metadata fields (populated from database, ignored during creation/upload)
    length: Optional[int] = Field(default=None, alias="length")
    chunk_size: Optional[int] = Field(default=None, alias="chunkSize")
    upload_date: Optional[datetime] = Field(default=None, alias="uploadDate")

    # model configuration
    model_config = ConfigDict(extra="ignore")

    @abstractmethod
    def dump_buffer(self) -> io.BytesIO:
        raise NotImplementedError

    def get_filename(self) -> str:
        return self.filename

    def dump_metadata(self) -> Optional[dict]:
        if self.metadata:
            if isinstance(self.metadata, BaseModel):
                return self.metadata.model_dump(by_alias=True, exclude_none=True)
            return self.metadata

        return None

    def self_scope(self) -> dict:
        return {"filename": self.filename}

    def collapse(self) -> Ripple:
        ripple = self.create_ripple()

        if ripple.state == RippleState.Unobservable:
            return ripple

        ripple.set_id(self.id)
        ripple.set_scope(self.self_scope())
            
        metadata = self.dump_metadata()
        if metadata:
            ripple.set("metadata", metadata)

        ripple.do_upload_blob(self.dump_buffer())
            
        return ripple