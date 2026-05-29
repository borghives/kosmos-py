from kosmos.dataverse import MustHaveObserverClient
from dotenv import load_dotenv
from kosmos import ether
import logging
logger = logging.getLogger(__name__)


def IgniteBase(*sources : str):
    for source in sources :
        load_dotenv(source)

def Ignite(*sources : str):
    for source in sources :
        load_dotenv(source)
    
    project_id =ether.UniversalConstants.Collapse().ProjectID
    if project_id == "" :
        logger.fatal("Fatal: Failed to ignite universal constants: ProjectID")
        raise Exception("Fatal: Failed to ignite universal constants: ProjectID")

    MustHaveObserverClient()
        
