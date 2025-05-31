"""Tests for the configuration module."""

import pytest
from terragrunt_gcp_mcp.config import Config, GCPConfig, TerragruntConfig


def test_config_creation():
    """Test basic config creation."""
    config = Config()
    assert config is not None
    assert isinstance(config.gcp, GCPConfig)
    assert isinstance(config.terragrunt, TerragruntConfig)


def test_gcp_config_defaults():
    """Test GCP config default values."""
    gcp_config = GCPConfig()
    assert gcp_config.default_region == "europe-west2"
    assert gcp_config.default_zone == "europe-west2-a"
    assert gcp_config.project_id is None
    assert gcp_config.credentials_path is None


def test_terragrunt_config_defaults():
    """Test Terragrunt config default values."""
    terragrunt_config = TerragruntConfig()
    assert terragrunt_config.binary_path == "terragrunt"
    assert terragrunt_config.terraform_binary == "tofu"
    assert terragrunt_config.parallelism == 10
    assert terragrunt_config.timeout == 3600
    assert terragrunt_config.experimental.stacks_enabled is True


def test_config_experimental_features():
    """Test experimental features configuration."""
    config = Config()
    assert config.terragrunt.experimental.stacks_enabled is True
    assert config.terragrunt.experimental.enhanced_dependency_resolution is True
    assert config.terragrunt.experimental.parallel_execution is True
    assert config.terragrunt.experimental.max_parallel_units == 10


def test_config_validation():
    """Test config validation methods."""
    config = Config()
    
    # Test experimental feature check
    assert config.is_experimental_enabled("stacks") is True
    assert config.is_experimental_enabled("nonexistent") is False
    
    # Test stack config
    stack_config = config.get_stack_config()
    assert isinstance(stack_config, dict)
    assert "enabled" in stack_config
    assert "max_parallel_units" in stack_config 