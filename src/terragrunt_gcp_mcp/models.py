"""Data models for Terragrunt GCP MCP Tool."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """Supported resource types."""
    
    FOLDER = "folder"
    PROJECT = "project"
    VPC_NETWORK = "vpc-network"
    PRIVATE_SERVICE_ACCESS = "private-service-access"
    COMPUTE = "compute"
    SQLSERVER = "sqlserver"
    BIGQUERY = "bigquery"
    SECRETS = "secrets"


class EnvironmentType(str, Enum):
    """Environment types."""
    
    PRODUCTION = "production"
    NON_PRODUCTION = "non-production"


class DeploymentStatus(str, Enum):
    """Deployment status values."""
    
    NOT_STARTED = "not_started"
    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResourceStatus(str, Enum):
    """Resource status values."""
    
    UNKNOWN = "unknown"
    NOT_DEPLOYED = "not_deployed"
    DEPLOYED = "deployed"
    OUTDATED = "outdated"
    FAILED = "failed"
    DRIFT_DETECTED = "drift_detected"


class StackStatus(str, Enum):
    """Stack status values for experimental stacks feature."""
    
    UNKNOWN = "unknown"
    READY = "ready"
    PLANNING = "planning"
    APPLYING = "applying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    DESTROYING = "destroying"


class UnitType(str, Enum):
    """Unit types for Terragrunt experimental features."""
    
    TERRAGRUNT = "terragrunt"
    TERRAFORM = "terraform"
    STACK = "stack"


class Resource(BaseModel):
    """Represents a Terragrunt resource."""
    
    name: str
    type: ResourceType
    path: str
    environment: str
    environment_type: EnvironmentType
    region: Optional[str] = None
    status: ResourceStatus = ResourceStatus.UNKNOWN
    dependencies: List[str] = Field(default_factory=list)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    last_modified: Optional[datetime] = None
    last_deployed: Optional[datetime] = None
    terraform_state: Optional[Dict[str, Any]] = None
    
    # New fields for experimental features
    unit_type: UnitType = UnitType.TERRAGRUNT
    stack_path: Optional[str] = None
    parent_stack: Optional[str] = None


class TerragruntUnit(BaseModel):
    """Represents a Terragrunt unit (experimental feature)."""
    
    name: str
    path: str
    type: UnitType
    dependencies: List[str] = Field(default_factory=list)
    dependents: List[str] = Field(default_factory=list)
    stack_path: Optional[str] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    status: ResourceStatus = ResourceStatus.UNKNOWN
    last_modified: Optional[datetime] = None


class TerragruntStack(BaseModel):
    """Represents a Terragrunt stack (experimental feature)."""
    
    name: str
    path: str
    units: List[TerragruntUnit] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    status: StackStatus = StackStatus.UNKNOWN
    configuration: Dict[str, Any] = Field(default_factory=dict)
    execution_order: List[List[str]] = Field(default_factory=list)  # Parallel execution groups
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    last_executed: Optional[datetime] = None


class StackExecution(BaseModel):
    """Represents a stack execution (experimental feature)."""
    
    id: str
    stack_path: str
    command: str
    status: StackStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_plan: List[List[str]] = Field(default_factory=list)
    unit_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeploymentPlan(BaseModel):
    """Represents a deployment plan."""
    
    id: str
    resources: List[str]
    changes: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    status: DeploymentStatus = DeploymentStatus.NOT_STARTED
    dry_run: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # New fields for experimental features
    stack_plan: Optional[Dict[str, Any]] = None
    execution_order: List[List[str]] = Field(default_factory=list)


class Deployment(BaseModel):
    """Represents a deployment execution."""
    
    id: str
    plan_id: str
    resources: List[str]
    status: DeploymentStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InfrastructureStatus(BaseModel):
    """Overall infrastructure status."""
    
    environment: str
    total_resources: int
    deployed_resources: int
    failed_resources: int
    outdated_resources: int
    drift_detected: int
    last_check: datetime
    health_score: float = Field(ge=0.0, le=100.0)
    cost_info: Optional[Dict[str, Any]] = None
    
    # New fields for experimental features
    total_stacks: int = 0
    deployed_stacks: int = 0
    failed_stacks: int = 0
    stack_health_score: float = Field(default=100.0, ge=0.0, le=100.0)


class DependencyGraph(BaseModel):
    """Resource dependency graph with experimental features support."""
    
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, str]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # New fields for experimental features
    stacks: List[Dict[str, Any]] = Field(default_factory=list)
    execution_order: List[List[str]] = Field(default_factory=list)
    parallel_groups: List[List[str]] = Field(default_factory=list)


class CostAnalysis(BaseModel):
    """Cost analysis data."""
    
    total_cost: float
    currency: str = "USD"
    period: str  # e.g., "monthly", "daily"
    breakdown_by_service: Dict[str, float] = Field(default_factory=dict)
    breakdown_by_environment: Dict[str, float] = Field(default_factory=dict)
    trends: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime


class AuditLogEntry(BaseModel):
    """Audit log entry."""
    
    timestamp: datetime
    user: str
    action: str
    resource: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None


class SlackNotification(BaseModel):
    """Slack notification data."""
    
    channel: str
    message: str
    username: Optional[str] = None
    icon_emoji: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


@dataclass
class TerragruntCommand:
    """Represents a Terragrunt command to execute."""
    
    command: str
    working_dir: str
    timeout: int = 3600
    env_vars: Optional[Dict[str, str]] = None
    capture_output: bool = True
    
    # New fields for experimental features
    use_experimental: bool = True
    stack_mode: bool = False
    parallel_execution: bool = True


@dataclass
class CommandResult:
    """Result of executing a command."""
    
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: str
    working_dir: str


class ResourceTemplate(BaseModel):
    """Template for creating new resources."""
    
    name: str
    type: ResourceType
    description: str
    template_path: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required_parameters: List[str] = Field(default_factory=list)
    example_configuration: Dict[str, Any] = Field(default_factory=dict)


class MCPToolResult(BaseModel):
    """Result of an MCP tool operation."""
    
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    execution_time: Optional[float] = None
    resource_id: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of resource validation."""
    
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    resource_path: str
    validated_at: datetime


class ExperimentalFeatures(BaseModel):
    """Configuration for experimental features."""
    
    stacks_enabled: bool = True
    enhanced_dependency_resolution: bool = True
    parallel_execution: bool = True
    stack_outputs: bool = True
    recursive_stacks: bool = False  # Not yet stable
    stack_run_commands: bool = True 