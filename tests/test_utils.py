"""Tests for the utils module."""

import pytest
from terragrunt_gcp_mcp.utils import (
    sanitize_resource_name,
    parse_terragrunt_path,
    build_terragrunt_path,
    get_environment_type,
    format_duration,
    calculate_health_score,
    safe_json_loads
)


def test_sanitize_resource_name():
    """Test resource name sanitization."""
    assert sanitize_resource_name("test-resource") == "test-resource"
    assert sanitize_resource_name("test_resource") == "test-resource"
    assert sanitize_resource_name("Test Resource") == "test-resource"
    assert sanitize_resource_name("test@resource#123") == "test-resource-123"


def test_parse_terragrunt_path():
    """Test Terragrunt path parsing."""
    path = "live/dev-account/test-dev/dev-99/europe-west2/compute/web-server-01"
    parsed = parse_terragrunt_path(path)
    
    assert parsed["account"] == "dev-account"
    assert parsed["environment"] == "test-dev"
    assert parsed["project"] == "dev-99"
    assert parsed["region"] == "europe-west2"
    assert parsed["resource_type"] == "compute"
    assert parsed["resource_name"] == "web-server-01"


def test_parse_terragrunt_path_minimal():
    """Test Terragrunt path parsing with minimal path."""
    path = "live/prod-account/production"
    parsed = parse_terragrunt_path(path)
    
    assert parsed["account"] == "prod-account"
    assert parsed["environment"] == "production"
    assert parsed["project"] is None
    assert parsed["region"] is None
    assert parsed["resource_type"] is None
    assert parsed["resource_name"] is None


def test_build_terragrunt_path():
    """Test building Terragrunt paths."""
    path = build_terragrunt_path(
        account="dev-account",
        environment="test-dev",
        project="dev-99",
        resource_type="compute"
    )
    
    expected = "live/dev-account/test-dev/dev-99/compute"
    assert path == expected


def test_build_terragrunt_path_with_region_and_resource():
    """Test building Terragrunt paths with region and resource name."""
    path = build_terragrunt_path(
        account="dev-account",
        environment="test-dev",
        project="dev-99",
        resource_type="compute",
        region="europe-west2",
        resource_name="web-server-01"
    )
    
    expected = "live/dev-account/test-dev/dev-99/europe-west2/compute/web-server-01"
    assert path == expected


def test_get_environment_type():
    """Test environment type detection."""
    assert get_environment_type("production") == "production"
    assert get_environment_type("prod") == "production"
    assert get_environment_type("staging") == "non-production"
    assert get_environment_type("development") == "non-production"
    assert get_environment_type("dev") == "non-production"
    assert get_environment_type("test") == "non-production"
    assert get_environment_type("unknown") == "non-production"


def test_format_duration():
    """Test duration formatting."""
    assert format_duration(30) == "30.0s"
    assert format_duration(90) == "1m 30s"
    assert format_duration(3661) == "1h 1m 1s"
    assert format_duration(0.5) == "0.5s"


def test_calculate_health_score():
    """Test health score calculation."""
    # Perfect health
    assert calculate_health_score(10, 10, 0, 0) == 100.0
    
    # Some failures
    assert calculate_health_score(10, 8, 2, 0) == 80.0
    
    # Some drift
    assert calculate_health_score(10, 9, 0, 1) == 95.0
    
    # Mixed issues
    assert calculate_health_score(10, 7, 2, 1) == 70.0
    
    # No resources
    assert calculate_health_score(0, 0, 0, 0) == 100.0


def test_safe_json_loads():
    """Test safe JSON loading."""
    # Valid JSON
    result = safe_json_loads('{"key": "value"}')
    assert result == {"key": "value"}
    
    # Invalid JSON
    result = safe_json_loads('invalid json')
    assert result is None
    
    # Empty string
    result = safe_json_loads('')
    assert result is None
    
    # Valid JSON array
    result = safe_json_loads('[1, 2, 3]')
    assert result == [1, 2, 3] 