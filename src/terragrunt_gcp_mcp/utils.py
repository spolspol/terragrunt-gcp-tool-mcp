"""Utility functions for Terragrunt GCP MCP Tool."""

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from git import Repo


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO", format_str: Optional[str] = None) -> None:
    """Set up logging configuration."""
    if format_str is None:
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_str,
        handlers=[logging.StreamHandler()]
    )


def sanitize_resource_name(name: str) -> str:
    """Sanitize a resource name to be valid for GCP/Terragrunt."""
    # Replace invalid characters with hyphens
    sanitized = re.sub(r'[^a-zA-Z0-9-]', '-', name.lower())
    # Remove leading/trailing hyphens and collapse multiple hyphens
    sanitized = re.sub(r'^-+|-+$', '', sanitized)
    sanitized = re.sub(r'-+', '-', sanitized)
    return sanitized


def parse_terragrunt_path(path: str) -> Dict[str, Optional[str]]:
    """Parse a Terragrunt path to extract components."""
    # Expected pattern: live/account/environment/project/region?/resource_type/resource_name?/sub_resource?
    parts = Path(path).parts
    
    result = {
        "account": None,
        "environment": None,
        "project": None,
        "region": None,
        "resource_type": None,
        "resource_name": None,
    }
    
    if len(parts) < 4 or parts[0] != "live":
        return result
    
    try:
        result["account"] = parts[1]
        result["environment"] = parts[2]
        result["project"] = parts[3]
        
        # Handle different path structures
        if len(parts) >= 5:
            # Could be region or resource_type
            if parts[4] in ["europe-west2", "us-central1", "us-east1", "asia-southeast1"]:
                result["region"] = parts[4]
                if len(parts) >= 6:
                    result["resource_type"] = parts[5]
                    if len(parts) >= 7:
                        # For nested resources, create a unique resource name that includes the full path
                        if len(parts) >= 8:
                            # This is a sub-resource like compute/sql-server-01/instance-template
                            result["resource_name"] = f"{parts[6]}/{parts[7]}"
                        else:
                            result["resource_name"] = parts[6]
            else:
                result["resource_type"] = parts[4]
                if len(parts) >= 6:
                    # For nested resources without region
                    if len(parts) >= 7:
                        # This is a sub-resource like secrets/sftp-sshfs-host/config
                        result["resource_name"] = f"{parts[5]}/{parts[6]}"
                    else:
                        result["resource_name"] = parts[5]
    except IndexError:
        pass
    
    return result


def build_terragrunt_path(
    account: str,
    environment: str,
    project: str,
    resource_type: str,
    region: Optional[str] = None,
    resource_name: Optional[str] = None,
) -> str:
    """Build a Terragrunt path from components."""
    parts = ["live", account, environment, project]
    
    if region:
        parts.append(region)
    
    parts.append(resource_type)
    
    if resource_name:
        parts.append(resource_name)
    
    return "/".join(parts)


def get_environment_type(environment: str) -> str:
    """Determine environment type from environment name."""
    prod_patterns = ["prod", "production", "live"]
    
    for pattern in prod_patterns:
        if pattern in environment.lower():
            return "production"
    
    return "non-production"


def load_hcl_config(file_path: str) -> Dict[str, Any]:
    """Load configuration from HCL file (simplified parser)."""
    try:
        with open(file_path, "r") as f:
            content = f.read()
        
        # Extract locals block (simplified)
        locals_match = re.search(r'locals\s*\{([^}]+)\}', content, re.DOTALL)
        if not locals_match:
            return {}
        
        locals_content = locals_match.group(1)
        
        # Parse key-value pairs (very simplified)
        config = {}
        for line in locals_content.split('\n'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'").rstrip(',')
                config[key] = value
        
        return config
    except Exception as e:
        logger.warning(f"Failed to parse HCL file {file_path}: {e}")
        return {}


async def run_command(
    command: List[str],
    working_dir: str,
    timeout: int = 3600,
    env_vars: Optional[Dict[str, str]] = None,
    capture_output: bool = True,
) -> Tuple[int, str, str, float]:
    """Run a command asynchronously."""
    start_time = time.time()
    
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    try:
        if capture_output:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            
            stdout_str = stdout.decode("utf-8") if stdout else ""
            stderr_str = stderr.decode("utf-8") if stderr else ""
        else:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_dir,
                env=env,
            )
            
            await asyncio.wait_for(process.wait(), timeout=timeout)
            stdout_str = ""
            stderr_str = ""
        
        execution_time = time.time() - start_time
        return process.returncode, stdout_str, stderr_str, execution_time
        
    except asyncio.TimeoutError:
        logger.error(f"Command timed out after {timeout} seconds: {' '.join(command)}")
        return -1, "", "Command timed out", time.time() - start_time
    except Exception as e:
        logger.error(f"Failed to run command {' '.join(command)}: {e}")
        return -1, "", str(e), time.time() - start_time


def extract_terraform_plan_summary(plan_output: str) -> Dict[str, Any]:
    """Extract summary information from Terraform plan output."""
    summary = {
        "resources_to_add": 0,
        "resources_to_change": 0,
        "resources_to_destroy": 0,
        "has_changes": False,
        "resources": [],
    }
    
    # Look for plan summary line
    plan_match = re.search(
        r'Plan: (\d+) to add, (\d+) to change, (\d+) to destroy',
        plan_output
    )
    
    if plan_match:
        summary["resources_to_add"] = int(plan_match.group(1))
        summary["resources_to_change"] = int(plan_match.group(2))
        summary["resources_to_destroy"] = int(plan_match.group(3))
        summary["has_changes"] = any([
            summary["resources_to_add"],
            summary["resources_to_change"],
            summary["resources_to_destroy"]
        ])
    
    # Extract individual resource changes
    resource_pattern = r'# ([^\s]+) will be (created|destroyed|updated)'
    for match in re.finditer(resource_pattern, plan_output):
        summary["resources"].append({
            "name": match.group(1),
            "action": match.group(2),
        })
    
    return summary


def validate_terraform_config(config_dir: str) -> Tuple[bool, List[str]]:
    """Validate Terraform configuration files."""
    errors = []
    
    # Check for required files
    required_files = ["terragrunt.hcl"]
    for file_name in required_files:
        file_path = os.path.join(config_dir, file_name)
        if not os.path.exists(file_path):
            errors.append(f"Missing required file: {file_name}")
    
    # Basic HCL syntax validation (simplified)
    terragrunt_file = os.path.join(config_dir, "terragrunt.hcl")
    if os.path.exists(terragrunt_file):
        try:
            with open(terragrunt_file, "r") as f:
                content = f.read()
            
            # Check for balanced braces
            open_braces = content.count("{")
            close_braces = content.count("}")
            if open_braces != close_braces:
                errors.append("Unbalanced braces in terragrunt.hcl")
            
            # Check for required blocks
            if "include" not in content:
                errors.append("Missing include block in terragrunt.hcl")
            
        except Exception as e:
            errors.append(f"Error reading terragrunt.hcl: {e}")
    
    return len(errors) == 0, errors


def generate_resource_id() -> str:
    """Generate a unique resource ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"res_{timestamp}_{os.urandom(4).hex()}"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def get_git_info(repo_path: str) -> Dict[str, Optional[str]]:
    """Get git repository information."""
    try:
        repo = Repo(repo_path)
        return {
            "branch": repo.active_branch.name,
            "commit": repo.head.commit.hexsha[:8],
            "is_dirty": repo.is_dirty(),
            "remote_url": next(iter(repo.remotes)).url if repo.remotes else None,
        }
    except Exception as e:
        logger.warning(f"Failed to get git info: {e}")
        return {
            "branch": None,
            "commit": None,
            "is_dirty": None,
            "remote_url": None,
        }


def merge_configurations(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two configuration dictionaries."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configurations(result[key], value)
        else:
            result[key] = value
    
    return result


def find_files_by_pattern(
    directory: str, pattern: str, recursive: bool = True
) -> List[str]:
    """Find files matching a pattern in a directory."""
    import glob
    
    if recursive:
        search_pattern = os.path.join(directory, "**", pattern)
        return glob.glob(search_pattern, recursive=True)
    else:
        search_pattern = os.path.join(directory, pattern)
        return glob.glob(search_pattern)


def safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON string, returning None on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def calculate_health_score(
    total: int, deployed: int, failed: int, drift: int
) -> float:
    """Calculate infrastructure health score (0-100)."""
    if total == 0:
        return 100.0
    
    # Base score from deployment success rate
    deployment_score = (deployed / total) * 100
    
    # Penalties for failures and drift
    failure_penalty = (failed / total) * 50
    drift_penalty = (drift / total) * 25
    
    # Calculate final score
    score = deployment_score - failure_penalty - drift_penalty
    return max(0.0, min(100.0, score)) 