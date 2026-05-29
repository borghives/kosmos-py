from kosmos import mongo
from kosmos.mongo.client import PurposeAffinity
import threading
from pymongo.errors import ConnectionFailure

import logging
logger = logging.getLogger(__name__)

_lock = threading.Lock()
_mongo_observers: dict[PurposeAffinity, mongo.Dataverse] = {} 
_summon_once: dict[PurposeAffinity, bool] = {}   


def summon_mongo(purpose: PurposeAffinity) -> mongo.Dataverse:
    if _summon_once.get(purpose, False):
        return _mongo_observers[purpose]

    with _lock:
        if not _summon_once.get(purpose, False):
            _mongo_observers[purpose] = mongo.Dataverse.create_for(purpose)
            _summon_once[purpose] = True
        return _mongo_observers[purpose]

    

def must_have_observer_client():
    data = summon_mongo(mongo.PurposeAffinity.Observer)
    if data is None:
        raise Exception("Failed to summon mongo observer client")
    
    client = data.sync_client()

    try:
        # The 'ping' command is cheap and does not require authentication privileges
        client.admin.command('ping')
        logger.info("MongoDB connection successful!")
    except ConnectionFailure as e:
        logger.fatal(f"Could not connect to MongoDB: {e}")
        raise e