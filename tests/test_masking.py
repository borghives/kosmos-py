import pytest
from unittest.mock import patch
from kosmos.mongo.client import MaskMongoURI, CollapseMongoURISecret, CollapseURIFor, PurposeAffinity

def test_mask_mongo_uri_cases():
    # Empty URI
    assert MaskMongoURI("") == "[Empty URI]"
    
    # Invalid format (no scheme)
    assert MaskMongoURI("localhost:27017") == "[Mongo URI has invalid format (no scheme)]"
    
    # No credentials
    assert MaskMongoURI("mongodb://localhost:27017") == "mongodb://localhost:27017"
    
    # Only user, no password
    assert MaskMongoURI("mongodb://testuser@localhost:27017") == "mongodb://testuser@localhost:27017"
    
    # User and password
    assert MaskMongoURI("mongodb://testuser:password123@localhost:27017") == "mongodb://testuser:****@localhost:27017"
    
    # Complex case with multiple hosts
    assert MaskMongoURI("mongodb://user:pass@host1,host2/?replicaSet=rs") == "mongodb://user:****@host1,host2/?replicaSet=rs"

def test_collapse_mongo_uri_secret_no_secret():
    # Empty URI
    assert CollapseMongoURISecret("") == ""
    
    # Invalid URI
    assert CollapseMongoURISecret("localhost:27017") == ""
    
    # No credentials
    assert CollapseMongoURISecret("mongodb://localhost") == "mongodb://localhost"
    
    # Only user
    assert CollapseMongoURISecret("mongodb://user@localhost") == "mongodb://user@localhost"
    
    # Standard password (no secret format)
    assert CollapseMongoURISecret("mongodb://user:pass@localhost") == "mongodb://user:pass@localhost"

@patch("kosmos.ether.CollapseSecretSource")
def test_collapse_mongo_uri_secret_with_secret(mock_collapse):
    mock_collapse.return_value = "resolved_secret_password"
    
    uri = "mongodb://user:__secret:my-secret:latest__@localhost:27017/db"
    collapsed = CollapseMongoURISecret(uri)
    
    assert collapsed == "mongodb://user:resolved_secret_password@localhost:27017/db"
    mock_collapse.assert_called_once_with("__secret:my-secret:latest__")

@patch("kosmos.mongo.client.CollapseMongoURISecret")
@patch("kosmos.ether.MongoConstants.Collapse")
def test_collapse_uri_for(mock_mongo_constants, mock_collapse_uri):
    mock_constants = mock_mongo_constants.return_value
    mock_constants.URI = "uri_val"
    mock_constants.CreatorURI = "creator_val"
    mock_constants.AdminURI = "admin_val"
    
    mock_collapse_uri.side_effect = lambda x: f"collapsed_{x}"
    
    assert CollapseURIFor(PurposeAffinity.Observer) == "collapsed_uri_val"
    assert CollapseURIFor(PurposeAffinity.Creator) == "collapsed_creator_val"
    assert CollapseURIFor(PurposeAffinity.Admin) == "collapsed_admin_val"
    assert CollapseURIFor(PurposeAffinity.Unknown) == "collapsed_uri_val"
