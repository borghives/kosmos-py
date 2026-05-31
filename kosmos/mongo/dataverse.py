import threading
from .client import PurposeAffinity, DbClientFactory, collapse_uri_for

from pymongo import MongoClient
from pymongo import AsyncMongoClient

from dataclasses import dataclass

@dataclass
class Dataverse:
    client_factory: DbClientFactory
    purpose: PurposeAffinity

    def async_client(self) -> AsyncMongoClient:
        return self.client_factory.get_client_async()
    
    def sync_client(self) -> MongoClient:
        return self.client_factory.get_client()

    @staticmethod
    def create_for(purpose: PurposeAffinity) -> 'Dataverse':
        uri = collapse_uri_for(purpose)
        return Dataverse(
            client_factory=DbClientFactory(uri),
            purpose=purpose
        )

_lock = threading.Lock()
_mongo_observers: dict[PurposeAffinity, Dataverse] = {} 
_summon_once: dict[PurposeAffinity, bool] = {}   

def summon_mongo(purpose: PurposeAffinity) -> Dataverse:
    if _summon_once.get(purpose, False):
        return _mongo_observers[purpose]

    with _lock:
        if not _summon_once.get(purpose, False):
            _mongo_observers[purpose] = Dataverse.create_for(purpose)
            _summon_once[purpose] = True
        return _mongo_observers[purpose]