import pytest
import asyncio
from unittest.mock import MagicMock, patch
from kosmos.mongo.client import DbClientFactory

@patch("kosmos.mongo.client.MongoClient")
def test_db_client_factory_sync(mock_mongo_client):
    mock_client = mock_mongo_client.return_value
    
    factory = DbClientFactory("mongodb://localhost")
    assert factory.get_client_uri() == "mongodb://localhost"
    
    c1 = factory.get_client()
    assert c1 is mock_client
    mock_mongo_client.assert_called_once_with("mongodb://localhost", tz_aware=True)
    
    # Caching on the same thread should return the exact same client
    c2 = factory.get_client()
    assert c2 is mock_client
    mock_mongo_client.assert_called_once()

@patch("kosmos.mongo.client.AsyncMongoClient")
def test_db_client_factory_async(mock_async_mongo_client):
    mock_client = mock_async_mongo_client.return_value
    
    factory = DbClientFactory("mongodb://localhost")
    
    # Since pytest runs this synchronously, no running loop is active
    c1 = factory.get_client_async()
    assert c1 is mock_client
    mock_async_mongo_client.assert_called_once_with("mongodb://localhost", tz_aware=True)
    
    # Verify it runs inside an event loop if we set one up
    async def run_in_loop():
        c2 = factory.get_client_async()
        assert c2 is mock_client
        
    asyncio.run(run_in_loop())
