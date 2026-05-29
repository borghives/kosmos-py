from kosmos.mongo.client import collapse_uri_for, PurposeAffinity
from pymongo import MongoClient
from pymongo import AsyncMongoClient
from kosmos.mongo.client import DbClientFactory
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