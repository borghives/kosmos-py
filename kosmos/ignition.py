from .mongo import summon_mongo, PurposeAffinity

from dotenv import load_dotenv
from kosmos import ether
import logging
logger = logging.getLogger(__name__)


def ignite_base(*sources: str):
    for source in sources:
        load_dotenv(source)

def ignite(*sources: str):
    for source in sources:
        load_dotenv(source)
    
    project_id = ether.UniversalConstants.collapse().project_id
    if project_id == "":
        logger.fatal("Fatal: Failed to ignite universal constants: ProjectID")
        raise Exception("Fatal: Failed to ignite universal constants: ProjectID")

    must_have_observer_client()

def must_have_observer_client():
    data = summon_mongo(PurposeAffinity.Observer)
    if data is None:
        raise Exception("Failed to summon mongo observer client")
    
    client = data.sync_client()

    try:
        # The 'ping' command is cheap and does not require authentication privileges
        client.admin.command('ping')
        logger.info("MongoDB connection successful!")
    except Exception as e:
        logger.fatal(f"Could not connect and ping to MongoDB: {e}")
        raise e
    
    return client