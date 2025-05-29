"""Terragrunt Stack Manager for experimental stacks feature."""

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
    StackExecution,
    StackStatus,
    TerragruntStack,
    TerragruntUnit,
    UnitType,
    ResourceStatus,
)
from .utils import run_command


logger = logging.getLogger(__name__)


class StackManager:
    """Manages Terragrunt stacks using experimental features."""

    def __init__(self, config: Config):
        """Initialize the Stack manager."""
        self.config = config
        self.root_path = config.terragrunt.root_path
        self.binary_path = config.terragrunt.binary_path
        self.stack_config = config.get_stack_config()

    def _prepare_environment(self) -> Dict[str, str]:
        """Prepare environment variables for Terragrunt stack commands."""
        env_vars = {}
        
        # Set GOOGLE_APPLICATION_CREDENTIALS if specified in config
        if self.config.gcp.credentials_path:
            credentials_path = os.path.expandvars(self.config.gcp.credentials_path)
            credentials_path = os.path.expanduser(credentials_path)
            if not os.path.isabs(credentials_path):
                credentials_path = os.path.abspath(credentials_path)
            env_vars["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            logger.debug(f"Setting GOOGLE_APPLICATION_CREDENTIALS to: {credentials_path}")
        
        # Set Google Cloud project if specified
        if self.config.gcp.project_id:
            env_vars["GOOGLE_CLOUD_PROJECT"] = self.config.gcp.project_id
            env_vars["GCLOUD_PROJECT"] = self.config.gcp.project_id
        
        # Set default region and zone
        if self.config.gcp.default_region:
            env_vars["GOOGLE_REGION"] = self.config.gcp.default_region
            env_vars["GOOGLE_CLOUD_REGION"] = self.config.gcp.default_region
        
        if self.config.gcp.default_zone:
            env_vars["GOOGLE_ZONE"] = self.config.gcp.default_zone
            env_vars["GOOGLE_CLOUD_ZONE"] = self.config.gcp.default_zone
        
        # Terragrunt CLI redesign environment variables
        env_vars["TG_NON_INTERACTIVE"] = "true"
        env_vars["TG_BACKEND_BOOTSTRAP"] = "true"
        
        # Experimental features environment variables
        env_vars["TG_EXPERIMENT_MODE"] = "true"
        env_vars["TG_STACKS_ENABLED"] = str(self.stack_config["enabled"]).lower()
        
        # Stack-specific settings
        if self.stack_config["max_parallel_units"]:
            env_vars["TG_PARALLELISM"] = str(self.stack_config["max_parallel_units"])
        
        return env_vars

    async def discover_stacks(self, environment: Optional[str] = None) -> List[TerragruntStack]:
        """Discover all Terragrunt stacks in the repository."""
        if not self.stack_config["enabled"]:
            logger.warning("Stacks feature is disabled in configuration")
            return []

        stacks = []
        live_path = os.path.join(self.root_path, "live")
        
        if not os.path.exists(live_path):
            logger.warning(f"Live directory not found: {live_path}")
            return stacks

        # Look for stack.hcl files which define stacks
        for root, dirs, files in os.walk(live_path):
            if ".terragrunt-cache" in root:
                continue
                
            if ".terragrunt-cache" in dirs:
                dirs.remove(".terragrunt-cache")
            
            # Check for stack.hcl file (experimental stacks feature)
            if "stack.hcl" in files:
                stack_path = os.path.relpath(root, self.root_path)
                
                try:
                    stack = await self._create_stack_from_path(stack_path)
                    if stack and (not environment or environment in stack.name):
                        stacks.append(stack)
                except Exception as e:
                    logger.warning(f"Failed to create stack from {stack_path}: {e}")

        return stacks

    async def _create_stack_from_path(self, stack_path: str) -> Optional[TerragruntStack]:
        """Create a TerragruntStack object from a stack path."""
        full_path = os.path.join(self.root_path, stack_path)
        stack_file = os.path.join(full_path, "stack.hcl")
        
        if not os.path.exists(stack_file):
            return None

        try:
            # Parse stack configuration
            stack_config = await self._parse_stack_config(stack_file)
            
            # Discover units within the stack
            units = await self._discover_stack_units(stack_path)
            
            # Determine execution order based on dependencies
            execution_order = await self._calculate_execution_order(units)
            
            stack_name = os.path.basename(stack_path)
            
            return TerragruntStack(
                name=stack_name,
                path=stack_path,
                units=units,
                dependencies=stack_config.get("dependencies", []),
                status=await self._get_stack_status(stack_path),
                configuration=stack_config,
                execution_order=execution_order,
                metadata={
                    "stack_file": stack_file,
                    "unit_count": len(units),
                    "parallel_groups": len(execution_order),
                },
                created_at=self._get_stack_created_time(stack_file),
            )
            
        except Exception as e:
            logger.error(f"Failed to create stack from {stack_path}: {e}")
            return None

    async def _parse_stack_config(self, stack_file: str) -> Dict[str, Any]:
        """Parse stack.hcl configuration file."""
        try:
            with open(stack_file, "r") as f:
                content = f.read()
            
            # Basic HCL parsing (simplified)
            config = {"dependencies": []}
            
            # Extract dependencies
            import re
            dep_pattern = r'dependency\s+"([^"]+)"\s*\{[^}]*config_path\s*=\s*"([^"]+)"'
            for match in re.finditer(dep_pattern, content):
                config["dependencies"].append(match.group(2))
            
            # Extract other configuration
            if "locals" in content:
                # Extract locals block for additional configuration
                locals_match = re.search(r'locals\s*\{([^}]+)\}', content, re.DOTALL)
                if locals_match:
                    locals_content = locals_match.group(1)
                    # Parse key-value pairs
                    for line in locals_content.split('\n'):
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'").rstrip(',')
                            config[key] = value
            
            return config
            
        except Exception as e:
            logger.warning(f"Failed to parse stack config {stack_file}: {e}")
            return {}

    async def _discover_stack_units(self, stack_path: str) -> List[TerragruntUnit]:
        """Discover all units within a stack."""
        units = []
        stack_full_path = os.path.join(self.root_path, stack_path)
        
        for root, dirs, files in os.walk(stack_full_path):
            if ".terragrunt-cache" in root:
                continue
                
            if ".terragrunt-cache" in dirs:
                dirs.remove(".terragrunt-cache")
            
            # Skip the stack root directory itself
            if root == stack_full_path and "stack.hcl" in files:
                continue
            
            if "terragrunt.hcl" in files:
                unit_path = os.path.relpath(root, self.root_path)
                
                try:
                    unit = await self._create_unit_from_path(unit_path, stack_path)
                    if unit:
                        units.append(unit)
                except Exception as e:
                    logger.warning(f"Failed to create unit from {unit_path}: {e}")

        return units

    async def _create_unit_from_path(self, unit_path: str, stack_path: str) -> Optional[TerragruntUnit]:
        """Create a TerragruntUnit object from a unit path."""
        full_path = os.path.join(self.root_path, unit_path)
        terragrunt_file = os.path.join(full_path, "terragrunt.hcl")
        
        if not os.path.exists(terragrunt_file):
            return None

        try:
            # Parse unit configuration and dependencies
            config = await self._parse_unit_config(terragrunt_file)
            dependencies = await self._get_unit_dependencies(terragrunt_file)
            
            unit_name = os.path.basename(unit_path)
            
            return TerragruntUnit(
                name=unit_name,
                path=unit_path,
                type=UnitType.TERRAGRUNT,
                dependencies=dependencies,
                stack_path=stack_path,
                configuration=config,
                status=await self._get_unit_status(unit_path),
                last_modified=self._get_unit_last_modified(terragrunt_file),
            )
            
        except Exception as e:
            logger.error(f"Failed to create unit from {unit_path}: {e}")
            return None

    async def _parse_unit_config(self, terragrunt_file: str) -> Dict[str, Any]:
        """Parse terragrunt.hcl configuration file."""
        try:
            with open(terragrunt_file, "r") as f:
                content = f.read()
            
            config = {"content": content}
            
            # Extract source
            if "source" in content:
                import re
                source_match = re.search(r'source\s*=\s*"([^"]+)"', content)
                if source_match:
                    config["source"] = source_match.group(1)
            
            return config
            
        except Exception as e:
            logger.warning(f"Failed to parse unit config {terragrunt_file}: {e}")
            return {}

    async def _get_unit_dependencies(self, terragrunt_file: str) -> List[str]:
        """Get dependencies for a unit."""
        dependencies = []
        
        try:
            with open(terragrunt_file, "r") as f:
                content = f.read()
            
            import re
            dependency_pattern = r'dependency\s+"([^"]+)"\s*\{[^}]*config_path\s*=\s*"([^"]+)"'
            
            for match in re.finditer(dependency_pattern, content):
                dep_path = match.group(2)
                if dep_path.startswith("../"):
                    # Convert relative path to absolute
                    unit_dir = os.path.dirname(terragrunt_file)
                    abs_dep_path = os.path.normpath(os.path.join(unit_dir, dep_path))
                    abs_dep_path = os.path.relpath(abs_dep_path, self.root_path)
                    dependencies.append(abs_dep_path)
                else:
                    dependencies.append(dep_path)
                    
        except Exception as e:
            logger.warning(f"Failed to parse dependencies for {terragrunt_file}: {e}")

        return dependencies

    async def _calculate_execution_order(self, units: List[TerragruntUnit]) -> List[List[str]]:
        """Calculate execution order for units based on dependencies."""
        if not units:
            return []

        # Create dependency graph
        unit_map = {unit.path: unit for unit in units}
        remaining_units = set(unit.path for unit in units)
        execution_order = []
        
        while remaining_units:
            # Find units with no unresolved dependencies
            ready_units = []
            for unit_path in remaining_units:
                unit = unit_map[unit_path]
                unresolved_deps = [dep for dep in unit.dependencies if dep in remaining_units]
                if not unresolved_deps:
                    ready_units.append(unit_path)
            
            if not ready_units:
                # Circular dependency or other issue
                logger.warning("Circular dependency detected or unresolvable dependencies")
                ready_units = list(remaining_units)  # Force execution of remaining units
            
            execution_order.append(ready_units)
            remaining_units -= set(ready_units)
        
        return execution_order

    async def _get_stack_status(self, stack_path: str) -> StackStatus:
        """Get the status of a stack."""
        try:
            # Use stack run command to check status
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, _ = await run_command(
                [self.binary_path, "stack", "run", "state", "list"],
                working_dir=os.path.join(self.root_path, stack_path),
                timeout=60,
                env_vars=env_vars,
            )
            
            if exit_code == 0:
                return StackStatus.DEPLOYED
            else:
                return StackStatus.UNKNOWN
                
        except Exception as e:
            logger.warning(f"Failed to check stack status for {stack_path}: {e}")
            return StackStatus.UNKNOWN

    async def _get_unit_status(self, unit_path: str) -> ResourceStatus:
        """Get the status of a unit."""
        full_path = os.path.join(self.root_path, unit_path)
        cache_path = os.path.join(full_path, ".terragrunt-cache")
        
        if not os.path.exists(cache_path):
            return ResourceStatus.NOT_DEPLOYED

        try:
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, _ = await run_command(
                [self.binary_path, "run", "state", "list"],
                working_dir=full_path,
                timeout=60,
                env_vars=env_vars,
            )
            
            if exit_code == 0 and stdout.strip():
                return ResourceStatus.DEPLOYED
            else:
                return ResourceStatus.NOT_DEPLOYED
                
        except Exception as e:
            logger.warning(f"Failed to check unit status for {unit_path}: {e}")
            return ResourceStatus.UNKNOWN

    def _get_stack_created_time(self, stack_file: str) -> Optional[datetime]:
        """Get the creation time of a stack."""
        if os.path.exists(stack_file):
            try:
                stat = os.stat(stack_file)
                return datetime.fromtimestamp(stat.st_ctime)
            except Exception:
                pass
        return None

    def _get_unit_last_modified(self, terragrunt_file: str) -> Optional[datetime]:
        """Get the last modified time of a unit."""
        if os.path.exists(terragrunt_file):
            try:
                stat = os.stat(terragrunt_file)
                return datetime.fromtimestamp(stat.st_mtime)
            except Exception:
                pass
        return None

    async def execute_stack_command(
        self, 
        stack_path: str, 
        command: str, 
        dry_run: bool = False
    ) -> StackExecution:
        """Execute a command on a stack using experimental features."""
        execution_id = f"stack_exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get stack information
        stack = await self._create_stack_from_path(stack_path)
        if not stack:
            raise Exception(f"Stack not found: {stack_path}")
        
        execution = StackExecution(
            id=execution_id,
            stack_path=stack_path,
            command=command,
            status=StackStatus.PLANNING,
            started_at=datetime.now(),
            execution_plan=stack.execution_order,
            metadata={
                "dry_run": dry_run,
                "unit_count": len(stack.units),
                "parallel_groups": len(stack.execution_order),
            }
        )
        
        try:
            # Execute stack command using experimental stack run
            stack_command = [self.binary_path, "stack", "run"]
            if dry_run:
                stack_command.append("--dry-run")
            stack_command.append(command)
            
            env_vars = self._prepare_environment()
            
            execution.status = StackStatus.APPLYING
            
            exit_code, stdout, stderr, exec_time = await run_command(
                stack_command,
                working_dir=os.path.join(self.root_path, stack_path),
                timeout=self.stack_config["timeout"],
                env_vars=env_vars,
            )
            
            execution.completed_at = datetime.now()
            
            if exit_code == 0:
                execution.status = StackStatus.DEPLOYED
            else:
                execution.status = StackStatus.FAILED
                execution.error_message = stderr
            
            # Parse unit results from output
            execution.unit_results = self._parse_stack_output(stdout, stderr)
            
            return execution
            
        except Exception as e:
            execution.status = StackStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            logger.error(f"Failed to execute stack command {command} on {stack_path}: {e}")
            return execution

    def _parse_stack_output(self, stdout: str, stderr: str) -> Dict[str, Dict[str, Any]]:
        """Parse stack execution output to extract unit results."""
        unit_results = {}
        
        # This is a simplified parser - in practice, you'd want more sophisticated parsing
        # based on the actual output format of the stack run command
        
        lines = stdout.split('\n') + stderr.split('\n')
        current_unit = None
        
        for line in lines:
            # Look for unit execution indicators
            if "Executing unit:" in line or "Running in" in line:
                # Extract unit name/path
                import re
                unit_match = re.search(r'(?:Executing unit:|Running in)\s+([^\s]+)', line)
                if unit_match:
                    current_unit = unit_match.group(1)
                    unit_results[current_unit] = {
                        "status": "running",
                        "output": [],
                        "errors": []
                    }
            
            elif current_unit and line.strip():
                if "Error:" in line or "Failed:" in line:
                    unit_results[current_unit]["errors"].append(line.strip())
                    unit_results[current_unit]["status"] = "failed"
                else:
                    unit_results[current_unit]["output"].append(line.strip())
        
        # Mark successful units
        for unit_path, result in unit_results.items():
            if result["status"] == "running" and not result["errors"]:
                result["status"] = "completed"
        
        return unit_results

    async def get_stack_outputs(self, stack_path: str) -> Dict[str, Any]:
        """Get outputs from a stack (experimental feature)."""
        if not self.config.terragrunt.experimental.stack_outputs:
            raise Exception("Stack outputs feature is disabled")
        
        try:
            env_vars = self._prepare_environment()
            exit_code, stdout, stderr, _ = await run_command(
                [self.binary_path, "stack", "output"],
                working_dir=os.path.join(self.root_path, stack_path),
                timeout=300,
                env_vars=env_vars,
            )
            
            if exit_code != 0:
                raise Exception(f"Failed to get stack outputs: {stderr}")
            
            # Parse JSON output
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                # Fallback to parsing text output
                outputs = {}
                for line in stdout.split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        outputs[key.strip()] = value.strip()
                return outputs
                
        except Exception as e:
            logger.error(f"Failed to get stack outputs for {stack_path}: {e}")
            raise 