from dotenv import load_dotenv
from kosmos import ether
def IgniteBase(*sources : str):
    for source in sources :
        load_dotenv(source)