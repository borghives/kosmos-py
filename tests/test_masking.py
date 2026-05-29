import pytest
from unittest.mock import patch
from kosmos.mongo.client import mask_mongo_uri, collapse_mongo_uri_secret, collapse_uri_for, PurposeAffinity

def test_mask_mongo_uri_cases():
    # Empty URI
    assert mask_mongo_uri("") == "[Empty URI]"
    
    # Invalid format (no scheme)
    assert mask_mongo_uri("localhost:27017") == "[Mongo URI has invalid format (no scheme)]"
    
    # No credentials
    assert mask_mongo_uri("mongodb://localhost:27017") == "mongodb://localhost:27017"
    
    # Only user, no password
    assert mask_mongo_uri("mongodb://testuser@localhost:27017") == "mongodb://testuser@localhost:27017"
    
    # User and password
    assert mask_mongo_uri("mongodb://testuser:password123@localhost:27017") == "mongodb://testuser:****@localhost:27017"
    
    # Complex case with multiple hosts
    assert mask_mongo_uri("mongodb://user:pass@host1,host2/?replicaSet=rs") == "mongodb://user:****@host1,host2/?replicaSet=rs"

def test_collapse_mongo_uri_secret_no_secret():
    # Empty URI
    assert collapse_mongo_uri_secret("") == ""
    
    # Invalid URI
    assert collapse_mongo_uri_secret("localhost:27017") == ""
    
    # No credentials
    assert collapse_mongo_uri_secret("mongodb://localhost") == "mongodb://localhost"
    
    # Only user
    assert collapse_mongo_uri_secret("mongodb://user@localhost") == "mongodb://user@localhost"
    
    # Standard password (no secret format)
    assert collapse_mongo_uri_secret("mongodb://user:pass@localhost") == "mongodb://user:pass@localhost"

@patch("kosmos.ether.collapse_secret_source")
def test_collapse_mongo_uri_secret_with_secret(mock_collapse):
    mock_collapse.return_value = "resolved_secret_password"
    
    uri = "mongodb://user:__secret:my-secret:latest__@localhost:27017/db"
    collapsed = collapse_mongo_uri_secret(uri)
    
    assert collapsed == "mongodb://user:resolved_secret_password@localhost:27017/db"
    mock_collapse.assert_called_once_with("__secret:my-secret:latest__")

@patch("kosmos.mongo.client.collapse_mongo_uri_secret")
@patch("kosmos.ether.MongoConstants.collapse")
def test_collapse_uri_for(mock_mongo_constants, mock_collapse_uri):
    mock_constants = mock_mongo_constants.return_value
    mock_constants.uri = "uri_val"
    mock_constants.creator_uri = "creator_val"
    mock_constants.admin_uri = "admin_val"
    
    mock_collapse_uri.side_effect = lambda x: f"collapsed_{x}"
    
    assert collapse_uri_for(PurposeAffinity.Observer) == "collapsed_uri_val"
    assert collapse_uri_for(PurposeAffinity.Creator) == "collapsed_creator_val"
    assert collapse_uri_for(PurposeAffinity.Admin) == "collapsed_admin_val"
    assert collapse_uri_for(PurposeAffinity.Unknown) == "collapsed_uri_val"

