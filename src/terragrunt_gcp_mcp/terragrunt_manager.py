"""Terragrunt operations manager."""

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import Config
from .models import (
    CommandResult,
    DeploymentPlan,
    Resource,
    ResourceStatus,
    ResourceType,
    TerragruntCommand,
    ValidationResult,
)
from .utils import (
    extract_terraform_plan_summary,
    parse_terragrunt_path,
    run_command,
    validate_terraform_config,
)


logger = logging.getLogger(__name__)


class TerragruntManager:
    """Manages Terragrunt operations."""

    def __init__(self, config: Config):
        """Initialize the Terragrunt manager."""
        self.config = config
        self.root_path = config.terragrunt.root_path
        self.binary_path = config.terragrunt.binary_path
        self.terraform_binary = config.terragrunt.terraform_binary

    def _prepare_environment(self) -> Dict[str, str]:
        """Prepare environment variables for Terragrunt commands."""
        env_vars = {}
        
        # Set GOOGLE_APPLICATION_CREDENTIALS if specified in config
        if self.config.gcp.credentials_path:
            # Expand environment variables first (like $HOME)
            credentials_path = os.path.expandvars(self.config.gcp.credentials_path)
            
            # Expand user path if needed (like ~)
            credentials_path = os.path.expanduser(credentials_path)
            
            # Convert to absolute path if relative
            if not os.path.isabs(credentials_path):
                credentials_path = os.path.abspath(credentials_path)
            
            env_vars["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            logger.debug(f"Setting GOOGLE_APPLICATION_CREDENTIALS to: {credentials_path}")
        
        # Set Google Cloud project if specified
        if self.config.gcp.project_id:
            env_vars["GOOGLE_CLOUD_PROJECT"] = self.config.gcp.project_id
            env_vars["GCLOUD_PROJECT"] = self.config.gcp.project_id
            logger.debug(f"Setting GOOGLE_CLOUD_PROJECT to: {self.config.gcp.project_id}")
        
        # Set default region and zone
        if self.config.gcp.default_region:
            env_vars["GOOGLE_REGION"] = self.config.gcp.default_region
            env_vars["GOOGLE_CLOUD_REGION"] = self.config.gcp.default_region
        
        if self.config.gcp.default_zone:
            env_vars["GOOGLE_ZONE"] = self.config.gcp.default_zone
            env_vars["GOOGLE_CLOUD_ZONE"] = self.config.gcp.default_zone
        
        return env_vars

    async def discover_resources(self, environment: Optional[str] = None) -> List[Resource]:
        """Discover all Terragrunt resources in the repository."""
        resources = []
        live_path = os.path.join(self.root_path, "live")
        
        if not os.path.exists(live_path):
            logger.warning(f"Live directory not found: {live_path}")
            return resources

        # Walk through the directory structure
        for root, dirs, files in os.walk(live_path):
            # Skip .terragrunt-cache directories and their subdirectories
            if ".terragrunt-cache" in root:
                continue
                
            # Remove .terragrunt-cache from dirs to prevent walking into them
            if ".terragrunt-cache" in dirs:
                dirs.remove(".terragrunt-cache")
            
            # Only consider directories that contain terragrunt.hcl as valid resources
            if "terragrunt.hcl" in files:
                resource_path = os.path.relpath(root, self.root_path)
                path_components = parse_terragrunt_path(resource_path)
                
                if environment and path_components.get("environment") != environment:
                    continue
                
                if path_components.get("resource_type"):
                    try:
                        resource = await self._create_resource_from_path(resource_path)
                        if resource:
                            resources.append(resource)
                    except Exception as e:
                        logger.warning(f"Failed to create resource from {resource_path}: {e}")

        return resources

    async def _create_resource_from_path(self, resource_path: str) -> Optional[Resource]:
        """Create a Resource object from a Terragrunt path."""
        path_components = parse_terragrunt_path(resource_path)
        
        if not all([
            path_components.get("account"),
            path_components.get("environment"),
            path_components.get("project"),
            path_components.get("resource_type"),
        ]):
            return None

        # Determine resource type
        resource_type_str = path_components["resource_type"]
        try:
            resource_type = ResourceType(resource_type_str)
        except ValueError:
            logger.warning(f"Unknown resource type: {resource_type_str}")
            return None

        # Get resource status
        status = await self._get_resource_status(resource_path)

        # Get configuration
        config = await self._get_resource_configuration(resource_path)

        # Get dependencies
        dependencies = await self._get_resource_dependencies(resource_path)

        # Create a meaningful resource name
        resource_name = path_components.get("resource_name")
        if resource_name:
            # If it's a nested resource (contains '/'), use the full path as name
            if '/' in resource_name:
                # For nested resources like "sql-server-01/instance-template"
                resource_name = resource_name
            else:
                # For simple resources, use the resource name
                resource_name = resource_name
        else:
            # Fallback to resource type if no specific name
            resource_name = resource_type_str

        environment = path_components["environment"]
        environment_type = "production" if "prod" in environment else "non-production"

        return Resource(
            name=resource_name,
            type=resource_type,
            path=resource_path,
            environment=environment,
            environment_type=environment_type,
            region=path_components.get("region"),
            status=status,
            dependencies=dependencies,
            configuration=config,
            last_modified=self._get_last_modified(resource_path),
        )

    async def _get_resource_status(self, resource_path: str) -> ResourceStatus:
        """Get the status of a resource."""
        full_path = os.path.join(self.root_path, resource_path)
        
        # Check if .terragrunt-cache exists (indicates it has been initialized)
        cache_path = os.path.join(full_path, ".terragrunt-cache")
        if not os.path.exists(cache_path):
            return ResourceStatus.NOT_DEPLOYED

        # Try to get state information
        try:
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, _ = await run_command(
                [self.binary_path, "state", "list"],
                working_dir=full_path,
                timeout=60,
                env_vars=env_vars,
            )
            
            if exit_code == 0 and stdout.strip():
                return ResourceStatus.DEPLOYED
            else:
                return ResourceStatus.NOT_DEPLOYED
                
        except Exception as e:
            logger.warning(f"Failed to check resource status for {resource_path}: {e}")
            return ResourceStatus.UNKNOWN

    async def _get_resource_configuration(self, resource_path: str) -> Dict[str, Any]:
        """Get the configuration of a resource."""
        full_path = os.path.join(self.root_path, resource_path)
        terragrunt_file = os.path.join(full_path, "terragrunt.hcl")
        
        if not os.path.exists(terragrunt_file):
            return {}

        try:
            with open(terragrunt_file, "r") as f:
                content = f.read()
            
            # Extract basic information from the file
            config = {"content": content}
            
            # Try to extract some basic configuration
            if "source" in content:
                source_match = content.split("source")[1].split("=")[1].split("\n")[0]
                config["source"] = source_match.strip().strip('"')
            
            return config
        except Exception as e:
            logger.warning(f"Failed to read configuration for {resource_path}: {e}")
            return {}

    async def _get_resource_dependencies(self, resource_path: str) -> List[str]:
        """Get the dependencies of a resource."""
        full_path = os.path.join(self.root_path, resource_path)
        terragrunt_file = os.path.join(full_path, "terragrunt.hcl")
        
        dependencies = []
        
        if not os.path.exists(terragrunt_file):
            return dependencies

        try:
            with open(terragrunt_file, "r") as f:
                content = f.read()
            
            # Look for dependency blocks
            import re
            dependency_pattern = r'dependency\s+"([^"]+)"\s*\{[^}]*config_path\s*=\s*"([^"]+)"'
            
            for match in re.finditer(dependency_pattern, content):
                dep_name = match.group(1)
                dep_path = match.group(2)
                
                # Convert relative path to absolute
                if dep_path.startswith("../"):
                    abs_dep_path = os.path.normpath(
                        os.path.join(resource_path, dep_path)
                    )
                    dependencies.append(abs_dep_path)
                else:
                    dependencies.append(dep_path)
                    
        except Exception as e:
            logger.warning(f"Failed to parse dependencies for {resource_path}: {e}")

        return dependencies

    def _get_last_modified(self, resource_path: str) -> Optional[datetime]:
        """Get the last modified time of a resource."""
        full_path = os.path.join(self.root_path, resource_path)
        terragrunt_file = os.path.join(full_path, "terragrunt.hcl")
        
        if os.path.exists(terragrunt_file):
            try:
                stat = os.stat(terragrunt_file)
                return datetime.fromtimestamp(stat.st_mtime)
            except Exception:
                pass
        
        return None

    async def validate_resource(self, resource_path: str) -> ValidationResult:
        """Validate a Terragrunt resource."""
        full_path = os.path.join(self.root_path, resource_path)
        errors = []
        warnings = []
        
        # Check if the resource directory exists
        if not os.path.exists(full_path):
            errors.append(f"Resource directory does not exist: {full_path}")
            return ValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                resource_path=resource_path,
                validated_at=datetime.now(),
            )
        
        # Check if terragrunt.hcl exists
        terragrunt_file = os.path.join(full_path, "terragrunt.hcl")
        if not os.path.exists(terragrunt_file):
            errors.append(f"terragrunt.hcl not found in {full_path}")
            return ValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                resource_path=resource_path,
                validated_at=datetime.now(),
            )
        
        # Validate file structure
        valid, file_errors = validate_terraform_config(full_path)
        if not valid:
            errors.extend(file_errors)

        # Validate with Terragrunt - run from the resource directory
        try:
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, _ = await run_command(
                [self.binary_path, "validate"],
                working_dir=full_path,  # Run from the resource directory
                timeout=300,
                env_vars=env_vars,
            )
            
            if exit_code != 0:
                errors.append(f"Terragrunt validation failed: {stderr}")
            
        except Exception as e:
            errors.append(f"Failed to run terragrunt validate: {e}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            resource_path=resource_path,
            validated_at=datetime.now(),
        )

    async def plan_resource(self, resource_path: str, dry_run: bool = True) -> DeploymentPlan:
        """Generate a deployment plan for a resource."""
        full_path = os.path.join(self.root_path, resource_path)
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Check if the resource directory exists
        if not os.path.exists(full_path):
            raise Exception(f"Resource directory does not exist: {full_path}")
        
        # Initialize if needed - run from the resource directory
        await self._ensure_initialized(full_path)
        
        # Run plan - from the resource directory
        try:
            plan_args = [self.binary_path, "plan"]
            if not dry_run:
                plan_args.extend(["-out=tfplan"])
            
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, _ = await run_command(
                plan_args,
                working_dir=full_path,  # Run from the resource directory
                timeout=self.config.terragrunt.timeout,
                env_vars=env_vars,
            )
            
            if exit_code != 0:
                raise Exception(f"Plan failed: {stderr}")
            
            # Parse plan output
            plan_summary = extract_terraform_plan_summary(stdout)
            
            return DeploymentPlan(
                id=plan_id,
                resources=[resource_path],
                changes=plan_summary.get("resources", []),
                created_at=datetime.now(),
                dry_run=dry_run,
                metadata={
                    "plan_output": stdout,
                    "summary": plan_summary,
                    "working_directory": full_path,
                },
            )
            
        except Exception as e:
            logger.error(f"Failed to plan resource {resource_path}: {e}")
            raise

    async def apply_resource(
        self, resource_path: str, plan_file: Optional[str] = None
    ) -> CommandResult:
        """Apply changes to a resource."""
        full_path = os.path.join(self.root_path, resource_path)
        
        # Check if the resource directory exists
        if not os.path.exists(full_path):
            raise Exception(f"Resource directory does not exist: {full_path}")
        
        # Initialize if needed - run from the resource directory
        await self._ensure_initialized(full_path)
        
        # Prepare command
        command = [self.binary_path, "apply"]
        if plan_file:
            # If plan_file is relative, make it relative to the resource directory
            if not os.path.isabs(plan_file):
                plan_file_path = os.path.join(full_path, plan_file)
                if os.path.exists(plan_file_path):
                    command.append(plan_file)
                else:
                    command.append(plan_file)  # Use as-is if not found
            else:
                command.append(plan_file)
        else:
            command.append("-auto-approve")
        
        # Run apply - from the resource directory
        try:
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, execution_time = await run_command(
                command,
                working_dir=full_path,  # Run from the resource directory
                timeout=self.config.terragrunt.timeout,
                env_vars=env_vars,
            )
            
            return CommandResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                command=" ".join(command),
                working_dir=full_path,
            )
            
        except Exception as e:
            logger.error(f"Failed to apply resource {resource_path}: {e}")
            raise

    async def destroy_resource(self, resource_path: str) -> CommandResult:
        """Destroy a resource."""
        full_path = os.path.join(self.root_path, resource_path)
        
        # Check if the resource directory exists
        if not os.path.exists(full_path):
            raise Exception(f"Resource directory does not exist: {full_path}")
        
        # Run destroy - from the resource directory
        try:
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, execution_time = await run_command(
                [self.binary_path, "destroy", "-auto-approve"],
                working_dir=full_path,  # Run from the resource directory
                timeout=self.config.terragrunt.timeout,
                env_vars=env_vars,
            )
            
            return CommandResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                command="terragrunt destroy -auto-approve",
                working_dir=full_path,
            )
            
        except Exception as e:
            logger.error(f"Failed to destroy resource {resource_path}: {e}")
            raise

    async def _ensure_initialized(self, resource_path: str) -> None:
        """Ensure a resource is initialized."""
        # resource_path should already be the full path to the resource directory
        cache_path = os.path.join(resource_path, ".terragrunt-cache")
        
        if not os.path.exists(cache_path):
            logger.info(f"Initializing {resource_path}")
            
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, _ = await run_command(
                [self.binary_path, "init"],
                working_dir=resource_path,  # Run from the resource directory
                timeout=600,
                env_vars=env_vars,
            )
            
            if exit_code != 0:
                raise Exception(f"Failed to initialize {resource_path}: {stderr}")

    async def get_state_info(self, resource_path: str) -> Dict[str, Any]:
        """Get state information for a resource."""
        full_path = os.path.join(self.root_path, resource_path)
        
        # Check if the resource directory exists
        if not os.path.exists(full_path):
            return {"error": f"Resource directory does not exist: {full_path}"}
        
        try:
            env_vars = self._prepare_environment()
            # Get state list - run from the resource directory
            exit_code, stdout, stderr, _ = await run_command(
                [self.binary_path, "state", "list"],
                working_dir=full_path,  # Run from the resource directory
                timeout=60,
                env_vars=env_vars,
            )
            
            if exit_code != 0:
                return {"error": f"Failed to get state list: {stderr}"}
            
            resources = stdout.strip().split("\n") if stdout.strip() else []
            
            # Get state show for each resource (limited to avoid timeout)
            state_details = {}
            for resource in resources[:5]:  # Limit to first 5 resources
                try:
                    exit_code, detail_stdout, _, _ = await run_command(
                        [self.binary_path, "state", "show", resource],
                        working_dir=full_path,  # Run from the resource directory
                        timeout=30,
                        env_vars=env_vars,
                    )
                    
                    if exit_code == 0:
                        state_details[resource] = detail_stdout
                        
                except Exception:
                    continue
            
            return {
                "resources": resources,
                "resource_count": len(resources),
                "details": state_details,
                "working_directory": full_path,
            }
            
        except Exception as e:
            logger.error(f"Failed to get state info for {resource_path}: {e}")
            return {"error": str(e)}

    async def run_custom_command(
        self, resource_path: str, command: List[str]
    ) -> CommandResult:
        """Run a custom Terragrunt command."""
        full_path = os.path.join(self.root_path, resource_path)
        
        # Check if the resource directory exists
        if not os.path.exists(full_path):
            raise Exception(f"Resource directory does not exist: {full_path}")
        
        # Prepend terragrunt binary
        full_command = [self.binary_path] + command
        
        try:
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, execution_time = await run_command(
                full_command,
                working_dir=full_path,  # Run from the resource directory
                timeout=self.config.terragrunt.timeout,
                env_vars=env_vars,
            )
            
            return CommandResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                command=" ".join(full_command),
                working_dir=full_path,
            )
            
        except Exception as e:
            logger.error(f"Failed to run custom command {command}: {e}")
            raise 