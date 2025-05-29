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


class DeploymentPlan(BaseModel):
    """Represents a deployment plan."""
    
    id: str
    resources: List[str]
    changes: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    status: DeploymentStatus = DeploymentStatus.NOT_STARTED
    dry_run: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


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


class DependencyGraph(BaseModel):
    """Resource dependency graph."""
    
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, str]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


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