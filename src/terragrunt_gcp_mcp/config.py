"""Configuration management for Terragrunt GCP MCP Tool."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class GCPConfig(BaseModel):
    """GCP configuration settings."""
    
    project_id: Optional[str] = None
    credentials_path: Optional[str] = None
    default_region: str = "europe-west2"
    default_zone: str = "europe-west2-a"


class TerragruntConfig(BaseModel):
    """Terragrunt configuration settings."""
    
    root_path: str = Field(default="../terragrunt-gcp-org-automation", description="Path to terragrunt-gcp-org-automation repository")
    binary_path: str = "terragrunt"
    terraform_binary: str = "tofu"
    cache_dir: str = ".terragrunt-cache"
    parallelism: int = 10
    timeout: int = 3600  # seconds
    
    # New CLI redesign settings
    backend_bootstrap: bool = Field(default=True, description="Enable automatic backend resource provisioning")
    non_interactive: bool = Field(default=True, description="Run in non-interactive mode")
    use_run_command: bool = Field(default=True, description="Use 'run' command prefix for Terragrunt operations")
    
    # Advanced settings
    max_retries: int = Field(default=3, description="Maximum number of retries for failed operations")
    retry_delay: int = Field(default=5, description="Delay between retries in seconds")


class SlackConfig(BaseModel):
    """Slack configuration settings."""
    
    webhook_url: Optional[str] = None
    default_channel: str = "#infrastructure"
    username: str = "Terragrunt Bot"
    icon_emoji: str = ":terraform:"


class MonitoringConfig(BaseModel):
    """Monitoring configuration settings."""
    
    enabled: bool = True
    check_interval: int = 300  # seconds
    max_retries: int = 3
    alert_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "cost_increase_percent": 20.0,
        "deployment_duration_minutes": 30.0,
        "error_rate_percent": 5.0,
    })


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: str = "10MB"
    backup_count: int = 5


class Config(BaseModel):
    """Main configuration class."""
    
    gcp: GCPConfig = Field(default_factory=GCPConfig)
    terragrunt: TerragruntConfig = Field(default_factory=TerragruntConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from YAML file."""
        if config_path is None:
            # Try default locations
            possible_paths = [
                "config/config.yaml",
                "config.yaml",
                os.path.expanduser("~/.terragrunt-gcp-mcp/config.yaml"),
                "/etc/terragrunt-gcp-mcp/config.yaml",
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            else:
                # No config file found, use defaults
                return cls()
        
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)

    def save_to_file(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        config_dir = os.path.dirname(config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        
        with open(config_path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, indent=2)

    def validate_paths(self) -> None:
        """Validate that required paths exist."""
        if not os.path.exists(self.terragrunt.root_path):
            raise ValueError(f"Terragrunt root path does not exist: {self.terragrunt.root_path}")
        
        if self.gcp.credentials_path and not os.path.exists(self.gcp.credentials_path):
            raise ValueError(f"GCP credentials path does not exist: {self.gcp.credentials_path}")


def get_config() -> Config:
    """Get the global configuration instance."""
    return Config.load_from_file() 