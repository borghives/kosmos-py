from kosmos.dataverse import must_have_observer_client
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

        
