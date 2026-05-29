import pytest
from kosmos.mongo.client import PurposeAffinity

def test_purpose_affinity_values():
    assert PurposeAffinity.Unknown == 0
    assert PurposeAffinity.Admin == 1
    assert PurposeAffinity.Creator == 2
    assert PurposeAffinity.Observer == 3

def test_purpose_affinity_to_string():
    assert PurposeAffinity.Unknown.ToString() == "Unknown"
    assert PurposeAffinity.Admin.ToString() == "Admin"
    assert PurposeAffinity.Creator.ToString() == "Creator"
    assert PurposeAffinity.Observer.ToString() == "Observer"
    # Test undefined behavior (fallback) using class method call
    # pyrefly: ignore [bad-argument-type]
    assert PurposeAffinity.ToString(99) == "Undefined"

def test_purpose_affinity_from_string():
    assert PurposeAffinity.from_string("Unknown") == PurposeAffinity.Unknown
    assert PurposeAffinity.from_string("Admin") == PurposeAffinity.Admin
    assert PurposeAffinity.from_string("Creator") == PurposeAffinity.Creator
    assert PurposeAffinity.from_string("Observer") == PurposeAffinity.Observer
    # Test whitespace trimming
    assert PurposeAffinity.from_string(" Admin ") == PurposeAffinity.Admin
    # Test fallback
    assert PurposeAffinity.from_string("InvalidName") == PurposeAffinity.Unknown
