"""Tests for the models module."""

import pytest
from datetime import datetime
from terragrunt_gcp_mcp.models import (
    Resource, ResourceType, ResourceStatus, EnvironmentType,
    TerragruntStack, TerragruntUnit, UnitType, StackStatus,
    DeploymentPlan, DeploymentStatus, InfrastructureStatus,
    MCPToolResult, ValidationResult
)


def test_resource_creation():
    """Test basic resource creation."""
    resource = Resource(
        name="test-resource",
        type=ResourceType.COMPUTE,
        path="/test/path",
        environment="dev",
        environment_type=EnvironmentType.NON_PRODUCTION
    )
    
    assert resource.name == "test-resource"
    assert resource.type == ResourceType.COMPUTE
    assert resource.path == "/test/path"
    assert resource.environment == "dev"
    assert resource.environment_type == EnvironmentType.NON_PRODUCTION
    assert resource.status == ResourceStatus.UNKNOWN
    assert resource.dependencies == []
    assert resource.unit_type == UnitType.TERRAGRUNT


def test_terragrunt_stack_creation():
    """Test Terragrunt stack creation."""
    stack = TerragruntStack(
        name="test-stack",
        path="/stack/path"
    )
    
    assert stack.name == "test-stack"
    assert stack.path == "/stack/path"
    assert stack.status == StackStatus.UNKNOWN
    assert stack.units == []
    assert stack.dependencies == []
    assert stack.execution_order == []


def test_terragrunt_unit_creation():
    """Test Terragrunt unit creation."""
    unit = TerragruntUnit(
        name="test-unit",
        path="/unit/path",
        type=UnitType.TERRAGRUNT
    )
    
    assert unit.name == "test-unit"
    assert unit.path == "/unit/path"
    assert unit.type == UnitType.TERRAGRUNT
    assert unit.status == ResourceStatus.UNKNOWN
    assert unit.dependencies == []
    assert unit.dependents == []


def test_deployment_plan_creation():
    """Test deployment plan creation."""
    plan = DeploymentPlan(
        id="test-plan-123",
        resources=["resource1", "resource2"],
        created_at=datetime.now()
    )
    
    assert plan.id == "test-plan-123"
    assert plan.resources == ["resource1", "resource2"]
    assert plan.status == DeploymentStatus.NOT_STARTED
    assert plan.dry_run is False
    assert plan.changes == []


def test_infrastructure_status_creation():
    """Test infrastructure status creation."""
    status = InfrastructureStatus(
        environment="production",
        total_resources=10,
        deployed_resources=8,
        failed_resources=1,
        outdated_resources=1,
        drift_detected=0,
        last_check=datetime.now(),
        health_score=80.0
    )
    
    assert status.environment == "production"
    assert status.total_resources == 10
    assert status.deployed_resources == 8
    assert status.failed_resources == 1
    assert status.health_score == 80.0
    assert status.total_stacks == 0
    assert status.stack_health_score == 100.0


def test_mcp_tool_result_success():
    """Test successful MCP tool result."""
    result = MCPToolResult(
        success=True,
        message="Operation completed successfully",
        data={"key": "value"}
    )
    
    assert result.success is True
    assert result.message == "Operation completed successfully"
    assert result.data == {"key": "value"}
    assert result.error_details is None


def test_mcp_tool_result_failure():
    """Test failed MCP tool result."""
    result = MCPToolResult(
        success=False,
        message="Operation failed",
        error_details="Detailed error message"
    )
    
    assert result.success is False
    assert result.message == "Operation failed"
    assert result.error_details == "Detailed error message"
    assert result.data is None


def test_validation_result_valid():
    """Test valid validation result."""
    result = ValidationResult(
        valid=True,
        resource_path="/test/resource",
        validated_at=datetime.now()
    )
    
    assert result.valid is True
    assert result.resource_path == "/test/resource"
    assert result.errors == []
    assert result.warnings == []


def test_validation_result_invalid():
    """Test invalid validation result."""
    result = ValidationResult(
        valid=False,
        errors=["Error 1", "Error 2"],
        warnings=["Warning 1"],
        resource_path="/test/resource",
        validated_at=datetime.now()
    )
    
    assert result.valid is False
    assert result.errors == ["Error 1", "Error 2"]
    assert result.warnings == ["Warning 1"]
    assert result.resource_path == "/test/resource" 