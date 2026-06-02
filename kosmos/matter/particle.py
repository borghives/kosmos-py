from enum import IntEnum

from kosmos.meta.util import coalesce
from kosmos.meta.state import MetaState
from kosmos.meta.model import Model
from kosmos.meta.annotation import CoalesceOnInsert, CoalesceOnIncr, RefreshOnSet
from .ripple import RippleState, Ripple

class ModelState(IntEnum):
    Unset = 0
    Transition = 1
    Material = 2

class ParticleBase(Model):
    """
    Pydantic models providing MongoDB persistence capabilities.

    This class extends `Model` to offer a suite of methods for
    database interactions, including creating, reading, and querying documents.
    It requires a decorator like `@declare_persist_db` to be applied to the
    subclass to define the database and collection metadata.

    It also supports automatic timestamp management for creation and updates
    and provides helpers for constructing atomic update operations.

    Attributes:
        updated_time (TimeUpdated): A timestamp that is automatically updated
            when the model is persisted to database.
        created_at (TimeInserted): A timestamp that is set once when the model
            is first inserted into the database.
    """

    _state: ModelState = ModelState.Unset

    @classmethod
    def get_meta_state(cls) -> MetaState:
        retval = getattr(cls, "_meta_state", None)
        assert retval is not None, "MetaState has not been declared for this model. Did you forget to use @declare_persist_db?"
        return retval

    # --- Instance State and Helpers ---
    @property
    def should_persist(self) -> bool:
        """
        Checks if the model should be persisted. Mainly used by lazy persist

        Returns:
            bool: `True` if the model should be persisted, `False` otherwise.
        """
        return self.has_update or not self.has_id()

    # Collapsible interface
    def self_scope(self) -> dict:
        """
        Returns a filter to find the current document. This filter MUST be unique to the document.
        Defaults to using the `_id` field. Can be overridden to use other fields.

        Returns:
            dict: A filter expression for finding the document.
        """
        return {}  # default no scope which should direct to use _id to scope.

    # A particle must be collapsed by an observer and decohere the interaction's ripple in order to exist in a known state.
    # Failure to complete the Collapse AND Decohere flow will put the state of the object in an UNKNOWN / INBETWEEN state.

    def create_ripple(self) -> Ripple:
        """Collapses the model's state"""
        self_state = self._state
        if self_state == ModelState.Unset:
            # Unset -> Transition
            self._state = ModelState.Transition
            ripple_state = RippleState.FromUnknown
            if self.has_id():
                ripple_state = RippleState.FromKnown
            return Ripple(state=ripple_state)
        elif self_state == ModelState.Material:
            # Material -> Transition
            self._state = ModelState.Transition
            return Ripple(state=RippleState.FromKnown)
        
        return Ripple(state=RippleState.Unobservable)  # A model is unobservable in transition state
        
    def collapse(self) -> Ripple:
        ripple = self.create_ripple()

        if ripple.state == RippleState.Unobservable:
            return ripple

        ripple.set_id(self.id)
        ripple.set_scope(self.self_scope())
            
        doc = self.dump_doc()
        for field, transformers in self.get_fields_with_metadata(RefreshOnSet).items():
            doc[field] = self.coalesce_field(field, transformers)

        for field, transformers in self.get_fields_with_metadata(
            CoalesceOnInsert
        ).items():
            current_value = getattr(self, field)
            new_value = coalesce(current_value, transformers)
            ripple.do_set_on_insert(field, new_value)
            if field in doc:
                del doc[field]
        
        for field, transformers in self.get_fields_with_metadata(
            CoalesceOnIncr
        ).items():
            current_value = getattr(self, field)
            ripple.do_inc(field, current_value.get_changes())
            if field in doc:
                del doc[field]

        ripple.set_doc(doc)
        return ripple

    def decohere(self, ripple: Ripple) -> None:
        # Do nothing on an unobservable ripple. We should not be here decohering an unobservable ripple.
        if ripple.state == RippleState.Unobservable:
            raise ValueError("Failed Decoherence: ripple state is unobservable.")

        self_state = self._state

        if self_state == ModelState.Transition:
            self._state = ModelState.Material
            self._has_update = False
            
            if ripple.was_inserted():
                kv_fields = ripple.get_on_insert_for()
                for f in kv_fields.keys():
                    setattr(self, f, kv_fields[f])
            
            for field, transformers in self.get_fields_with_metadata(
                CoalesceOnIncr
            ).items():
                current_value = getattr(self, field)
                setattr(self, field, current_value.collapse())
        
        final_id = ripple.get_final_id()
        if final_id is not None:
            self.id = final_id
        

