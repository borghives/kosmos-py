from kosmos import ether
from enum import IntEnum
import asyncio
import threading
from pymongo import AsyncMongoClient, MongoClient
from abc import ABC

import logging
logger = logging.getLogger(__name__)

class PurposeAffinity(IntEnum):
    Unknown = 0
    Admin = 1
    Creator = 2
    Observer = 3

    def to_string(self) -> str:
        if self == PurposeAffinity.Unknown:
            return "Unknown"
        elif self == PurposeAffinity.Admin:
            return "Admin"
        elif self == PurposeAffinity.Creator:
            return "Creator"
        elif self == PurposeAffinity.Observer:
            return "Observer"
        else:
            return "Undefined"
    
    @staticmethod
    def from_string(s: str) -> 'PurposeAffinity':
        s = s.strip()
        if s == "Unknown":
            return PurposeAffinity.Unknown
        elif s == "Admin":
            return PurposeAffinity.Admin
        elif s == "Creator":
            return PurposeAffinity.Creator
        elif s == "Observer":
            return PurposeAffinity.Observer
        else:
            return PurposeAffinity.Unknown


def mask_mongo_uri(uri: str) -> str:
    if len(uri) == 0:
        return "[Empty URI]"
    # 1. Isolate the scheme
    scheme_split = uri.split("://", 2)
    if len(scheme_split) != 2:
        # don't return uri just incase it contains secrets
        return "[Mongo URI has invalid format (no scheme)]"

    scheme, remainder = scheme_split[0], scheme_split[1]

    # 2. Find the end of the credentials (the LAST '@' before any '/' or '?')
    # This is important because passwords themselves can contain '@' if encoded,
    # but the delimiter between creds and hosts is the final '@'.
    end_of_creds = remainder.rfind("@")
    if end_of_creds == -1:
        return uri  # No credentials found no need to mask

    creds = remainder[:end_of_creds]
    host_and_path = remainder[end_of_creds:]  # Includes the '@'

    # 3. Split User and Password
    user_auth = creds.split(":", 2)
    if len(user_auth) < 2:
        return uri  # Only user, no password no need to mask

    user = user_auth[0]
    _ = user_auth[1]

    return f"{scheme}://{user}:****{host_and_path}"


def collapse_mongo_uri_secret(uri: str) -> str:
    logger.debug("Parsing Mongo URI %s", mask_mongo_uri(uri))

    if len(uri) == 0:
        logger.error("Mongo URI is empty or not set.")
        return ""

    # 1. Isolate the scheme
    scheme_split = uri.split("://", 2)
    if len(scheme_split) != 2:
        logger.error("Mongo URI has invalid format")
        return ""

    scheme, remainder = scheme_split[0], scheme_split[1]

    # 2. Find the end of the credentials (the LAST '@' before any '/' or '?')
    # This is important because passwords themselves can contain '@' if encoded,
    # but the delimiter between creds and hosts is the final '@'.
    end_of_creds = remainder.rfind("@")
    if end_of_creds == -1:
        logger.info("No credentials found (unauthenticated connection)")
        return uri 

    # 3. Split User and Password
    creds = remainder[:end_of_creds]
    host_and_path = remainder[end_of_creds:]  # Includes the '@'
    user_auth = creds.split(":", 1)

    if len(user_auth) < 2:
        logger.info("Only user found, no password")
        return uri 

    user = user_auth[0]
    password = user_auth[1]
    logger.debug("Parsed MongoDB URI %s %s", user, host_and_path)

    # 4. Translate and Stitch

    if ether.is_secret_source_format(password):
        logger.debug("MongoDB URI Password is from a secret source")
        password = ether.collapse_secret_source(password)
    return f"{scheme}://{user}:{password}{host_and_path}"


def collapse_uri_for(purpose: PurposeAffinity) -> str:
    constants = ether.MongoConstants.collapse()
    match purpose:
        case PurposeAffinity.Observer:
            logger.info("Using URI from MONGODB_URI")
            return collapse_mongo_uri_secret(constants.uri)
        case PurposeAffinity.Creator:
            logger.info("Using CreatorUri from MONGODB_CREATOR_URI")
            return collapse_mongo_uri_secret(constants.creator_uri)
        case PurposeAffinity.Admin:
            logger.info("Using AdminUri from MONGODB_ADMIN_URI")
            return collapse_mongo_uri_secret(constants.admin_uri)
        case _:
            logger.info("Using Default URI from MONGODB_URI")
            return collapse_mongo_uri_secret(constants.uri)

class DbClientFactory(ABC):
    _t_client_cache_data = threading.local()

    def __init__(self, uri: str):
        self.uri = uri

    def get_client_uri(self) -> str:
        return self.uri
    
    def get_client_async(self) -> AsyncMongoClient:
        client_uri = self.get_client_uri()
        
        try:
            loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            loop_id = 0
        cache_key = f"{type(self).__name__}+{hash(client_uri)}+async+{loop_id}"

        db_client = getattr(self._t_client_cache_data, cache_key, None)
        if db_client is None:
            db_client = AsyncMongoClient(client_uri, tz_aware=True)
            setattr(self._t_client_cache_data, cache_key, db_client)
        
        assert (db_client is not None)
        return db_client
    
    def get_client(self) -> MongoClient:
        client_uri = self.get_client_uri()

        cache_key = f"{type(self).__name__}+{hash(client_uri)}+synced"
        db_client = getattr(self._t_client_cache_data, cache_key, None)
        if db_client is None:
            db_client = MongoClient(client_uri, tz_aware=True)
            setattr(self._t_client_cache_data, cache_key, db_client)
        
        assert (db_client is not None)
        return db_client

        