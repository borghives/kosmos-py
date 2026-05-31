from .mongo import summon_mongo, PurposeAffinity
from pymongo.errors import ConnectionFailure

import logging
logger = logging.getLogger(__name__)


def must_have_observer_client():
    data = summon_mongo(PurposeAffinity.Observer)
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
