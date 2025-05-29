"""MCP server for Terragrunt GCP infrastructure management."""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from .config import Config
from .models import (
    CommandResult,
    DeploymentPlan,
    DeploymentStatus,
    InfrastructureStatus,
    MCPToolResult,
    Resource,
    ResourceType,
)
from .terragrunt_manager import TerragruntManager
from .utils import setup_logging


logger = logging.getLogger(__name__)


class TerragruntGCPMCPServer:
    """MCP server for Terragrunt GCP infrastructure management."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the MCP server."""
        self.config = Config.load_from_file(config_path)
        self.terragrunt_manager = TerragruntManager(self.config)
        
        # Set up logging
        setup_logging(
            level=self.config.logging.level,
            format_str=self.config.logging.format
        )
        
        # Initialize FastMCP server
        self.app = FastMCP("Terragrunt GCP MCP Server")
        self._register_tools()

    def _register_tools(self):
        """Register MCP tools with the server."""
        
        @self.app.tool()
        async def list_resources(environment: Optional[str] = None) -> MCPToolResult:
            """List all Terragrunt resources in the infrastructure.
            
            Args:
                environment: Filter by environment (optional)
            """
            try:
                start_time = datetime.now()
                resources = await self.terragrunt_manager.discover_resources(environment)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                resource_data = []
                for resource in resources:
                    resource_data.append({
                        "name": resource.name,
                        "type": resource.type.value,
                        "path": resource.path,
                        "environment": resource.environment,
                        "status": resource.status.value,
                        "region": resource.region,
                        "last_modified": resource.last_modified.isoformat() if resource.last_modified else None
                    })
                
                return MCPToolResult(
                    success=True,
                    message=f"Found {len(resources)} resources",
                    data={
                        "resources": resource_data,
                        "total_count": len(resources),
                        "environment_filter": environment
                    },
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to list resources: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to list resources",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_resource(resource_path: str) -> MCPToolResult:
            """Get detailed information about a specific resource.
            
            Args:
                resource_path: Path to the resource (e.g., live/dev-account/test-dev/dev-99/project)
            """
            try:
                start_time = datetime.now()
                
                # Validate the resource
                validation_result = await self.terragrunt_manager.validate_resource(resource_path)
                if not validation_result.valid:
                    return MCPToolResult(
                        success=False,
                        message="Resource validation failed",
                        error_details="; ".join(validation_result.errors)
                    )
                
                # Get state information
                state_info = await self.terragrunt_manager.get_state_info(resource_path)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=True,
                    message=f"Retrieved resource information for {resource_path}",
                    data={
                        "resource_path": resource_path,
                        "validation": {
                            "valid": validation_result.valid,
                            "warnings": validation_result.warnings
                        },
                        "state": state_info,
                        "validated_at": validation_result.validated_at.isoformat()
                    },
                    execution_time=execution_time,
                    resource_id=resource_path
                )
                
            except Exception as e:
                logger.error(f"Failed to get resource {resource_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to get resource {resource_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def plan_deployment(
            resource_path: str,
            dry_run: bool = True
        ) -> MCPToolResult:
            """Generate a deployment plan for a resource.
            
            Args:
                resource_path: Path to the resource
                dry_run: Whether this is a dry run (default: True)
            """
            try:
                start_time = datetime.now()
                
                plan = await self.terragrunt_manager.plan_resource(resource_path, dry_run)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=True,
                    message=f"Generated deployment plan for {resource_path}",
                    data={
                        "plan_id": plan.id,
                        "resource_path": resource_path,
                        "dry_run": dry_run,
                        "changes_count": len(plan.changes),
                        "changes": plan.changes,
                        "created_at": plan.created_at.isoformat(),
                        "status": plan.status.value,
                        "metadata": plan.metadata
                    },
                    execution_time=execution_time,
                    resource_id=resource_path
                )
                
            except Exception as e:
                logger.error(f"Failed to plan deployment for {resource_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to plan deployment for {resource_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def deploy_resource(
            resource_path: str,
            plan_file: Optional[str] = None
        ) -> MCPToolResult:
            """Deploy a resource using Terragrunt.
            
            Args:
                resource_path: Path to the resource
                plan_file: Optional plan file to use (default: None, will run apply directly)
            """
            try:
                start_time = datetime.now()
                
                result = await self.terragrunt_manager.apply_resource(resource_path, plan_file)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                success = result.exit_code == 0
                
                return MCPToolResult(
                    success=success,
                    message=f"Deployment {'completed' if success else 'failed'} for {resource_path}",
                    data={
                        "resource_path": resource_path,
                        "exit_code": result.exit_code,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "execution_time": result.execution_time,
                        "command": result.command
                    },
                    execution_time=execution_time,
                    resource_id=resource_path,
                    error_details=result.stderr if not success else None
                )
                
            except Exception as e:
                logger.error(f"Failed to deploy resource {resource_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to deploy resource {resource_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def destroy_resource(resource_path: str) -> MCPToolResult:
            """Destroy a resource using Terragrunt.
            
            Args:
                resource_path: Path to the resource
            """
            try:
                start_time = datetime.now()
                
                result = await self.terragrunt_manager.destroy_resource(resource_path)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                success = result.exit_code == 0
                
                return MCPToolResult(
                    success=success,
                    message=f"Destruction {'completed' if success else 'failed'} for {resource_path}",
                    data={
                        "resource_path": resource_path,
                        "exit_code": result.exit_code,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "execution_time": result.execution_time,
                        "command": result.command
                    },
                    execution_time=execution_time,
                    resource_id=resource_path,
                    error_details=result.stderr if not success else None
                )
                
            except Exception as e:
                logger.error(f"Failed to destroy resource {resource_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to destroy resource {resource_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_infrastructure_status(
            environment: Optional[str] = None,
            include_costs: bool = False
        ) -> MCPToolResult:
            """Get overall infrastructure status and health.
            
            Args:
                environment: Filter by environment (optional)
                include_costs: Whether to include cost information (default: False)
            """
            try:
                start_time = datetime.now()
                
                resources = await self.terragrunt_manager.discover_resources(environment)
                
                # Calculate status metrics
                total_resources = len(resources)
                deployed_resources = len([r for r in resources if r.status == "deployed"])
                failed_resources = len([r for r in resources if r.status == "failed"])
                outdated_resources = len([r for r in resources if r.status == "outdated"])
                drift_detected = len([r for r in resources if r.status == "drift_detected"])
                
                # Calculate health score
                from .utils import calculate_health_score
                health_score = calculate_health_score(
                    total_resources, deployed_resources, failed_resources, drift_detected
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                status_data = {
                    "environment": environment or "all",
                    "total_resources": total_resources,
                    "deployed_resources": deployed_resources,
                    "failed_resources": failed_resources,
                    "outdated_resources": outdated_resources,
                    "drift_detected": drift_detected,
                    "health_score": health_score,
                    "last_check": datetime.now().isoformat(),
                    "resource_breakdown": {}
                }
                
                # Add resource type breakdown
                for resource_type in ResourceType:
                    type_resources = [r for r in resources if r.type == resource_type]
                    if type_resources:
                        status_data["resource_breakdown"][resource_type.value] = {
                            "total": len(type_resources),
                            "deployed": len([r for r in type_resources if r.status == "deployed"]),
                            "failed": len([r for r in type_resources if r.status == "failed"])
                        }
                
                if include_costs:
                    # Placeholder for cost information
                    status_data["cost_info"] = {
                        "message": "Cost analysis not yet implemented",
                        "total_cost": 0.0,
                        "currency": "USD"
                    }
                
                return MCPToolResult(
                    success=True,
                    message=f"Infrastructure status retrieved for {environment or 'all environments'}",
                    data=status_data,
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to get infrastructure status: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to get infrastructure status",
                    error_details=str(e)
                )

        @self.app.tool()
        async def run_custom_command(
            resource_path: str,
            command: List[str]
        ) -> MCPToolResult:
            """Run a custom Terragrunt command on a resource.
            
            Args:
                resource_path: Path to the resource
                command: List of command arguments (e.g., ["state", "list"])
            """
            try:
                start_time = datetime.now()
                
                result = await self.terragrunt_manager.run_custom_command(resource_path, command)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                success = result.exit_code == 0
                
                return MCPToolResult(
                    success=success,
                    message=f"Custom command {'completed' if success else 'failed'} for {resource_path}",
                    data={
                        "resource_path": resource_path,
                        "command": command,
                        "exit_code": result.exit_code,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "execution_time": result.execution_time,
                        "full_command": result.command
                    },
                    execution_time=execution_time,
                    resource_id=resource_path,
                    error_details=result.stderr if not success else None
                )
                
            except Exception as e:
                logger.error(f"Failed to run custom command on {resource_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to run custom command on {resource_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def send_slack_notification(
            message: str,
            channel: Optional[str] = None,
            title: Optional[str] = None
        ) -> MCPToolResult:
            """Send a notification to Slack.
            
            Args:
                message: Message to send
                channel: Slack channel (optional, uses default from config)
                title: Optional title for the message
            """
            try:
                # This is a placeholder implementation
                # In a real implementation, you would use the Slack API
                
                target_channel = channel or self.config.slack.default_channel
                
                notification_data = {
                    "channel": target_channel,
                    "message": message,
                    "title": title,
                    "timestamp": datetime.now().isoformat(),
                    "status": "simulated"  # Remove this when implementing real Slack integration
                }
                
                logger.info(f"Slack notification (simulated): {message} to {target_channel}")
                
                return MCPToolResult(
                    success=True,
                    message=f"Notification sent to {target_channel}",
                    data=notification_data
                )
                
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to send Slack notification",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_resource_details(
            resource_path: str,
            include_configuration: bool = False
        ) -> MCPToolResult:
            """Get detailed information about a specific resource including attributes, state, and configuration.
            
            Args:
                resource_path: Path to the resource (e.g., live/dev-account/test-dev/dev-99/project) or resource name
                include_configuration: Whether to include full configuration content (default: False)
            """
            try:
                start_time = datetime.now()
                
                # First, discover all resources to find the matching one
                all_resources = await self.terragrunt_manager.discover_resources()
                matching_resource = None
                
                for resource in all_resources:
                    if resource.path == resource_path or resource.name == resource_path:
                        matching_resource = resource
                        break
                
                if not matching_resource:
                    available_resources = [{"name": r.name, "path": r.path} for r in all_resources[:10]]
                    return MCPToolResult(
                        success=False,
                        message=f"Resource not found: {resource_path}",
                        data={
                            "available_resources": available_resources,
                            "total_available": len(all_resources)
                        },
                        error_details=f"No resource found matching '{resource_path}'. Check available resources."
                    )
                
                # Get additional information
                state_info = {}
                validation_result = None
                
                try:
                    state_info = await self.terragrunt_manager.get_state_info(matching_resource.path)
                except Exception as e:
                    state_info = {"error": str(e)}
                
                try:
                    validation_result = await self.terragrunt_manager.validate_resource(matching_resource.path)
                except Exception as e:
                    logger.warning(f"Failed to validate resource {matching_resource.path}: {e}")
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Build detailed resource information
                resource_details = {
                    "basic_info": {
                        "name": matching_resource.name,
                        "type": matching_resource.type.value,
                        "path": matching_resource.path,
                        "environment": matching_resource.environment,
                        "environment_type": matching_resource.environment_type,
                        "region": matching_resource.region,
                        "status": matching_resource.status.value
                    },
                    "timestamps": {
                        "last_modified": matching_resource.last_modified.isoformat() if matching_resource.last_modified else None,
                        "last_deployed": matching_resource.last_deployed.isoformat() if matching_resource.last_deployed else None
                    },
                    "dependencies": {
                        "count": len(matching_resource.dependencies),
                        "list": matching_resource.dependencies
                    },
                    "state_info": state_info,
                    "validation": {
                        "valid": validation_result.valid if validation_result else None,
                        "errors": validation_result.errors if validation_result else [],
                        "warnings": validation_result.warnings if validation_result else [],
                        "validated_at": validation_result.validated_at.isoformat() if validation_result else None
                    } if validation_result else None
                }
                
                # Include configuration if requested
                if include_configuration:
                    resource_details["configuration"] = matching_resource.configuration
                else:
                    # Just include a summary
                    config_summary = {}
                    if matching_resource.configuration:
                        for key, value in matching_resource.configuration.items():
                            if key == "content":
                                config_summary[key] = f"[{len(str(value))} characters]"
                            else:
                                config_summary[key] = value
                    resource_details["configuration_summary"] = config_summary
                
                return MCPToolResult(
                    success=True,
                    message=f"Retrieved detailed information for resource: {matching_resource.name}",
                    data=resource_details,
                    execution_time=execution_time,
                    resource_id=matching_resource.path
                )
                
            except Exception as e:
                logger.error(f"Failed to get resource details for {resource_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to get resource details for {resource_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def validate_resource_config(
            resource_path: str,
            check_dependencies: bool = True
        ) -> MCPToolResult:
            """Validate a Terragrunt resource configuration.
            
            Args:
                resource_path: Path to the resource (e.g., live/dev-account/test-dev/dev-99/project) or resource name
                check_dependencies: Whether to also validate dependencies (default: True)
            """
            try:
                start_time = datetime.now()
                
                # Find the resource
                all_resources = await self.terragrunt_manager.discover_resources()
                matching_resource = None
                
                for resource in all_resources:
                    if resource.path == resource_path or resource.name == resource_path:
                        matching_resource = resource
                        break
                
                if not matching_resource:
                    return MCPToolResult(
                        success=False,
                        message=f"Resource not found: {resource_path}",
                        error_details=f"No resource found matching '{resource_path}'"
                    )
                
                # Validate the resource
                validation_result = await self.terragrunt_manager.validate_resource(matching_resource.path)
                
                # Optionally check dependencies
                dependency_results = []
                if check_dependencies and matching_resource.dependencies:
                    for dep_path in matching_resource.dependencies:
                        try:
                            dep_validation = await self.terragrunt_manager.validate_resource(dep_path)
                            dependency_results.append({
                                "path": dep_path,
                                "valid": dep_validation.valid,
                                "errors": dep_validation.errors,
                                "warnings": dep_validation.warnings
                            })
                        except Exception as e:
                            dependency_results.append({
                                "path": dep_path,
                                "valid": False,
                                "errors": [str(e)],
                                "warnings": []
                            })
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=validation_result.valid,
                    message=f"Validation {'passed' if validation_result.valid else 'failed'} for {matching_resource.name}",
                    data={
                        "resource": {
                            "name": matching_resource.name,
                            "path": matching_resource.path,
                            "type": matching_resource.type.value
                        },
                        "validation": {
                            "valid": validation_result.valid,
                            "errors": validation_result.errors,
                            "warnings": validation_result.warnings,
                            "validated_at": validation_result.validated_at.isoformat()
                        },
                        "dependencies": {
                            "checked": check_dependencies,
                            "count": len(dependency_results),
                            "results": dependency_results
                        }
                    },
                    execution_time=execution_time,
                    resource_id=matching_resource.path,
                    error_details="; ".join(validation_result.errors) if validation_result.errors else None
                )
                
            except Exception as e:
                logger.error(f"Failed to validate resource {resource_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to validate resource {resource_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def plan_resource_deployment(
            resource_path: str,
            dry_run: bool = True,
            save_plan: bool = False
        ) -> MCPToolResult:
            """Generate a deployment plan for a Terragrunt resource.
            
            Args:
                resource_path: Path to the resource (e.g., live/dev-account/test-dev/dev-99/project) or resource name
                dry_run: Whether this is a dry run (default: True)
                save_plan: Whether to save the plan file for later use (default: False)
            """
            try:
                start_time = datetime.now()
                
                # Find the resource
                all_resources = await self.terragrunt_manager.discover_resources()
                matching_resource = None
                
                for resource in all_resources:
                    if resource.path == resource_path or resource.name == resource_path:
                        matching_resource = resource
                        break
                
                if not matching_resource:
                    return MCPToolResult(
                        success=False,
                        message=f"Resource not found: {resource_path}",
                        error_details=f"No resource found matching '{resource_path}'"
                    )
                
                # Validate first
                validation_result = await self.terragrunt_manager.validate_resource(matching_resource.path)
                if not validation_result.valid:
                    return MCPToolResult(
                        success=False,
                        message=f"Cannot plan deployment: resource validation failed",
                        data={
                            "validation_errors": validation_result.errors,
                            "validation_warnings": validation_result.warnings
                        },
                        error_details="Resource must pass validation before planning deployment"
                    )
                
                # Generate plan
                plan = await self.terragrunt_manager.plan_resource(matching_resource.path, dry_run)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Analyze plan changes
                changes_summary = {
                    "total_changes": len(plan.changes),
                    "has_changes": len(plan.changes) > 0,
                    "changes_by_action": {}
                }
                
                for change in plan.changes:
                    action = change.get("action", "unknown")
                    changes_summary["changes_by_action"][action] = changes_summary["changes_by_action"].get(action, 0) + 1
                
                return MCPToolResult(
                    success=True,
                    message=f"Deployment plan generated for {matching_resource.name}",
                    data={
                        "resource": {
                            "name": matching_resource.name,
                            "path": matching_resource.path,
                            "type": matching_resource.type.value
                        },
                        "plan": {
                            "id": plan.id,
                            "dry_run": dry_run,
                            "save_plan": save_plan,
                            "status": plan.status.value,
                            "created_at": plan.created_at.isoformat(),
                            "changes_summary": changes_summary,
                            "changes": plan.changes,
                            "metadata": plan.metadata
                        }
                    },
                    execution_time=execution_time,
                    resource_id=matching_resource.path
                )
                
            except Exception as e:
                logger.error(f"Failed to plan deployment for {resource_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to plan deployment for {resource_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def apply_resource_deployment(
            resource_path: str,
            auto_approve: bool = False,
            plan_file: Optional[str] = None,
            notify_on_completion: bool = True
        ) -> MCPToolResult:
            """Apply changes to a Terragrunt resource.
            
            Args:
                resource_path: Path to the resource (e.g., live/dev-account/test-dev/dev-99/project) or resource name
                auto_approve: Whether to automatically approve the deployment (default: False)
                plan_file: Optional plan file to use (default: None, will run apply directly)
                notify_on_completion: Whether to send notifications on completion (default: True)
            """
            try:
                start_time = datetime.now()
                
                # Find the resource
                all_resources = await self.terragrunt_manager.discover_resources()
                matching_resource = None
                
                for resource in all_resources:
                    if resource.path == resource_path or resource.name == resource_path:
                        matching_resource = resource
                        break
                
                if not matching_resource:
                    return MCPToolResult(
                        success=False,
                        message=f"Resource not found: {resource_path}",
                        error_details=f"No resource found matching '{resource_path}'"
                    )
                
                # Safety check: validate first unless auto_approve is True
                if not auto_approve:
                    validation_result = await self.terragrunt_manager.validate_resource(matching_resource.path)
                    if not validation_result.valid:
                        return MCPToolResult(
                            success=False,
                            message=f"Cannot apply deployment: resource validation failed",
                            data={
                                "validation_errors": validation_result.errors,
                                "validation_warnings": validation_result.warnings,
                                "suggestion": "Use auto_approve=True to bypass validation or fix validation errors first"
                            },
                            error_details="Resource must pass validation before deployment"
                        )
                
                # Apply the deployment
                result = await self.terragrunt_manager.apply_resource(matching_resource.path, plan_file)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                success = result.exit_code == 0
                
                # Prepare notification if requested
                notification_sent = False
                if notify_on_completion and success:
                    try:
                        # Send notification (placeholder implementation)
                        notification_message = f"✅ Deployment completed successfully for {matching_resource.name}"
                        logger.info(f"Notification: {notification_message}")
                        notification_sent = True
                    except Exception as e:
                        logger.warning(f"Failed to send notification: {e}")
                
                return MCPToolResult(
                    success=success,
                    message=f"Deployment {'completed successfully' if success else 'failed'} for {matching_resource.name}",
                    data={
                        "resource": {
                            "name": matching_resource.name,
                            "path": matching_resource.path,
                            "type": matching_resource.type.value
                        },
                        "deployment": {
                            "auto_approved": auto_approve,
                            "plan_file_used": plan_file,
                            "exit_code": result.exit_code,
                            "execution_time": result.execution_time,
                            "command": result.command,
                            "stdout": result.stdout,
                            "stderr": result.stderr if not success else None
                        },
                        "notification": {
                            "requested": notify_on_completion,
                            "sent": notification_sent
                        }
                    },
                    execution_time=execution_time,
                    resource_id=matching_resource.path,
                    error_details=result.stderr if not success else None
                )
                
            except Exception as e:
                logger.error(f"Failed to apply deployment for {resource_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to apply deployment for {resource_path}",
                    error_details=str(e)
                )

    def run(self):
        """Run the MCP server."""
        logger.info("Starting Terragrunt GCP MCP Server")
        
        # Validate configuration
        try:
            self.config.validate_paths()
            logger.info("Configuration validated successfully")
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        
        # Run the FastMCP server (synchronous call)
        self.app.run()


def main():
    """Main entry point for the MCP server."""
    import sys
    
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    server = TerragruntGCPMCPServer(config_path)
    server.run()


if __name__ == "__main__":
    main() 