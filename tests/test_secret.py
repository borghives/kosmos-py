import pytest
from unittest.mock import MagicMock, patch
from kosmos.ether.secret import (
    is_secret_source_format,
    collapse_secret_source,
    collapse_secret_string,
    summon_secret_manager,
    GCPSecretManager
)

def test_is_secret_source_format():
    assert is_secret_source_format("__secret:my-secret:v1__") is True
    assert is_secret_source_format("not_a_secret") is False
    assert is_secret_source_format("__secret:some__") is True

def test_collapse_secret_source_invalid():
    with pytest.raises(ValueError, match="Not a secret source string"):
        collapse_secret_source("not_a_secret")
        
    with pytest.raises(ValueError, match="Invalid secret source string format"):
        collapse_secret_source("__secret:my-secret__")
        
    with pytest.raises(ValueError, match="Not a secret source string"):
        collapse_secret_source("__notsecret:my-secret:v1__")

@patch("kosmos.ether.secret.summon_secret_manager")
def test_collapse_secret_source_valid(mock_summon):
    mock_mgr = mock_summon.return_value
    mock_mgr.access_secret.return_value = "secret_value_123"
    
    res = collapse_secret_source("__secret:db-password:latest__")
    assert res == "secret_value_123"
    mock_mgr.access_secret.assert_called_once_with("db-password", "latest")

@patch("kosmos.ether.secret.summon_secret_manager")
def test_collapse_secret_string(mock_summon):
    mock_mgr = mock_summon.return_value
    mock_mgr.access_secret.return_value = "access_granted"
    
    assert collapse_secret_string("__secret:my-secret:v1__") == "access_granted"
    mock_mgr.access_secret.assert_called_with("my-secret", "v1")
    
    assert collapse_secret_string("another-secret:v2") == "access_granted"
    mock_mgr.access_secret.assert_called_with("another-secret", "v2")
    
    assert collapse_secret_string("simple-secret") == "access_granted"
    mock_mgr.access_secret.assert_called_with("simple-secret", "latest")

@patch("kosmos.ether.UniversalConstants.collapse")
def test_summon_secret_manager(mock_constants):
    mock_constants.return_value.project_id = ""
    with pytest.raises(ValueError, match="Project ID is missing"):
        summon_secret_manager()
        
    mock_constants.return_value.project_id = "my-gcp-project"
    mgr = summon_secret_manager()
    assert isinstance(mgr, GCPSecretManager)
    assert mgr.project_id == "my-gcp-project"

@patch("google.cloud.secretmanager.SecretManagerServiceClient")
def test_gcp_secret_manager_client_caching(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.access_secret_version.return_value.payload.data = b"my-payload"
    
    mgr = GCPSecretManager(project_id="test-project")
    
    assert mgr._client is None
    
    val1 = mgr.access_secret("sec1", "v1")
    assert val1 == "my-payload"
    assert mgr._client is mock_client
    mock_client_cls.assert_called_once()
    
    val2 = mgr.access_secret("sec2", "v2")
    assert val2 == "my-payload"
    mock_client_cls.assert_called_once()
