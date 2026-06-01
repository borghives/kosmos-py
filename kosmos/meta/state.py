from pydantic.fields import FieldInfo
from typing import Optional
from dataclasses import field
from dataclasses import dataclass, field


@dataclass
class MetaState:
    data_name   : str
    branch_name : str
    field_map   : dict[str, FieldInfo] = field(default_factory=dict)
    version     : Optional[int] = None
    is_blob     : bool = field(default=False)

    def resolve_name(self, name: str) -> str:
        """
        Resolves the given name to its canonical name.
        
        This method attempts to find the canonical name for a given field name.
        First, it checks if the name exists as a key in the `field_map`. If found,
        it returns the corresponding value (the canonical name). If not found,
        it treats the input name as the canonical name and returns it directly.
        
        Args:
            name (str): The field name to resolve.
            
        Returns:
            str: The canonical name for the given field name.
        """
        field_info = self.field_map.get(name)
        if field_info is None:
            return name
        return field_info.alias or name


def declare_persist_db(
    collection_name: str,
    db_name: str,
    version: Optional[int] = None,
    is_blob: bool = False
):
    """
    A class decorator that declares how a model should be persisted to
    MongoDB.

    Args:
        collection_name (str): The name of the MongoDB collection.
        db_name (str): The name of the MongoDB database.
        version (Optional[int]): The version of the collection.
        is_blob (bool): Whether the collection is a blob file collection.
    """

    def decorator(cls):
        cls._meta_state = MetaState(
            data_name=collection_name,
            branch_name=db_name,
            field_map=cls.model_fields,
            version=version,
            is_blob=is_blob
        )
        return cls

    return decorator