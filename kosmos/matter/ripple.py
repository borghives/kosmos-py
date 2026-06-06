from enum import IntEnum
from typing import  Any

from dataclasses import dataclass, field
from bson import ObjectId
from pymongo.results import InsertOneResult, UpdateResult
import io
class RippleState(IntEnum):
    Unobservable = 0
    FromUnknown = 1
    FromKnown = 2

@dataclass
class Ripple:
    id : ObjectId | None = None
    scope: dict = field(default_factory=dict)
    state : RippleState = RippleState.Unobservable
    exprs : dict[str, Any] = field(default_factory=dict)
    doc : dict[str, Any] | None = None
    after_doc: Any | None = None
    interstitial : dict[str, Any] = field(default_factory=dict)
    blob_to_upload: io.BytesIO | None = None
    insert_feedback : InsertOneResult | None = None
    update_feedback : UpdateResult | None = None
    stasis_mode : bool = False

    def set_stasis_mode(self):
        self.stasis_mode = True

    def is_stasis_mode(self):
        return self.stasis_mode

    def set_id(self, id: ObjectId | None):
        self.id = id

    def set_scope(self, id: ObjectId | None, scope: dict):
        self.set_id(id)
        if len(scope) == 0:
            if self.id is None:
                self.id = ObjectId()
            self.scope = {"_id" : self.id}
        else:
            self.scope = scope
        
        return self.scope
    
    def get_scope(self) -> dict:
        return self.scope
    
    def get_final_id(self):
        if self.insert_feedback is not None:
            return self.insert_feedback.inserted_id
        
        if self.after_doc is not None:
            return self.after_doc.get('_id')

        if self.update_feedback is not None:
            if self.update_feedback.upserted_id is not None:
                return self.update_feedback.upserted_id

        return self.id
    
    def set_doc(self, doc : dict[str, Any]):
        self.doc = doc
    
    def get_doc(self) -> dict[str, Any]:
        if self.doc is None:
            return {}
        return self.doc

    def set(self, key: str, value: Any):
        self.interstitial[key] = value
    
    def get(self, key: str, default: Any = None):
        return self.interstitial.get(key, default)

    def do_operation(self, operation: str, key: str, value: Any):
        if self.exprs.get(operation) is None:
            self.exprs[operation] = {}
        self.exprs[operation][key] = value

    def do_set_on_insert(self, field: str, value: Any):
        self.do_operation("$setOnInsert", field, value)
        
    def do_inc(self, field: str, value: Any):
        self.do_operation("$inc", field, value)

    def do_add_to_set(self, field: str, value: Any):
        self.do_operation("$addToSet", field, value)

    def do_upload_blob(self, blob: io.BytesIO | bytes):
        if isinstance(blob, bytes):
            self.blob_to_upload = io.BytesIO(blob)
        else:
            self.blob_to_upload = blob
    
    def get_on_insert_for(self):
        return self.exprs.get("$setOnInsert", {})
    
    def get_on_incr_for(self):
        return self.exprs.get("$inc", {})

    def get_blob(self) -> io.BytesIO | None:
        if self.blob_to_upload is None:
            return None
        try:
            self.blob_to_upload.seek(0)
        except (AttributeError, io.UnsupportedOperation):
            pass
        return self.blob_to_upload
    
    def was_inserted(self) -> bool:
        return (self.insert_feedback is not None) or \
        (self.update_feedback is not None and self.update_feedback.upserted_id is not None)
    
    def was_updated(self) -> bool:
        return self.update_feedback is not None and self.update_feedback.modified_count > 0
    
    def get_update_instruction(self) -> dict:
        retval = self.exprs.copy()
        retval["$set"] = self.get_doc()
        return retval