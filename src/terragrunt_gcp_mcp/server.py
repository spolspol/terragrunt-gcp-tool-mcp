"""MCP server for Terragrunt GCP infrastructure management with experimental features."""

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
    StackStatus,
    TerragruntStack,
    StackExecution,
)
from .terragrunt_manager import TerragruntManager
from .stack_manager import StackManager
from .cost_manager import CostManager
from .utils import setup_logging


logger = logging.getLogger(__name__)


class TerragruntGCPMCPServer:
    """MCP server for Terragrunt GCP infrastructure management with experimental features."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the MCP server."""
        self.config = Config.load_from_file(config_path)
        self.terragrunt_manager = TerragruntManager(self.config)
        self.stack_manager = StackManager(self.config)
        self.cost_manager = CostManager(self.config)
        
        # Set up logging
        setup_logging(
            level=self.config.logging.level,
            format_str=self.config.logging.format
        )
        
        # Initialize FastMCP server
        self.app = FastMCP("Terragrunt GCP MCP Server with Experimental Features")
        self._register_tools()

    def _register_tools(self):
        """Register MCP tools with the server."""
        
        # Original tools (keeping for backward compatibility)
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
                        "last_modified": resource.last_modified.isoformat() if resource.last_modified else None,
                        "unit_type": resource.unit_type.value,
                        "stack_path": resource.stack_path,
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

        # New experimental stacks tools
        @self.app.tool()
        async def list_stacks(environment: Optional[str] = None) -> MCPToolResult:
            """List all Terragrunt stacks using experimental features.
            
            Args:
                environment: Filter by environment (optional)
            """
            try:
                start_time = datetime.now()
                
                if not self.config.is_experimental_enabled("stacks_enabled"):
                    return MCPToolResult(
                        success=False,
                        message="Stacks experimental feature is disabled",
                        error_details="Enable stacks in configuration to use this feature"
                    )
                
                stacks = await self.stack_manager.discover_stacks(environment)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                stack_data = []
                for stack in stacks:
                    stack_data.append({
                        "name": stack.name,
                        "path": stack.path,
                        "status": stack.status.value,
                        "unit_count": len(stack.units),
                        "parallel_groups": len(stack.execution_order),
                        "dependencies": stack.dependencies,
                        "created_at": stack.created_at.isoformat() if stack.created_at else None,
                        "last_executed": stack.last_executed.isoformat() if stack.last_executed else None,
                    })
                
                return MCPToolResult(
                    success=True,
                    message=f"Found {len(stacks)} stacks",
                    data={
                        "stacks": stack_data,
                        "total_count": len(stacks),
                        "environment_filter": environment,
                        "experimental_features_enabled": True
                    },
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to list stacks: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to list stacks",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_stack_details(stack_path: str) -> MCPToolResult:
            """Get detailed information about a specific stack.
            
            Args:
                stack_path: Path to the stack (e.g., live/dev-account/test-dev/dev-99)
            """
            try:
                start_time = datetime.now()
                
                if not self.config.is_experimental_enabled("stacks_enabled"):
                    return MCPToolResult(
                        success=False,
                        message="Stacks experimental feature is disabled",
                        error_details="Enable stacks in configuration to use this feature"
                    )
                
                # Find the stack
                stacks = await self.stack_manager.discover_stacks()
                matching_stack = None
                
                for stack in stacks:
                    if stack.path == stack_path or stack.name == stack_path:
                        matching_stack = stack
                        break
                
                if not matching_stack:
                    return MCPToolResult(
                        success=False,
                        message=f"Stack not found: {stack_path}",
                        error_details=f"No stack found matching '{stack_path}'"
                    )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Build detailed stack information
                stack_details = {
                    "basic_info": {
                        "name": matching_stack.name,
                        "path": matching_stack.path,
                        "status": matching_stack.status.value,
                        "unit_count": len(matching_stack.units),
                        "parallel_groups": len(matching_stack.execution_order),
                    },
                    "units": [
                        {
                            "name": unit.name,
                            "path": unit.path,
                            "type": unit.type.value,
                            "status": unit.status.value,
                            "dependencies": unit.dependencies,
                            "last_modified": unit.last_modified.isoformat() if unit.last_modified else None,
                        }
                        for unit in matching_stack.units
                    ],
                    "execution_order": matching_stack.execution_order,
                    "dependencies": matching_stack.dependencies,
                    "configuration": matching_stack.configuration,
                    "metadata": matching_stack.metadata,
                    "timestamps": {
                        "created_at": matching_stack.created_at.isoformat() if matching_stack.created_at else None,
                        "last_executed": matching_stack.last_executed.isoformat() if matching_stack.last_executed else None,
                    }
                }
                
                return MCPToolResult(
                    success=True,
                    message=f"Retrieved stack details for: {matching_stack.name}",
                    data=stack_details,
                    execution_time=execution_time,
                    resource_id=matching_stack.path
                )
                
            except Exception as e:
                logger.error(f"Failed to get stack details for {stack_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to get stack details for {stack_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def execute_stack_command(
            stack_path: str,
            command: str,
            dry_run: bool = False
        ) -> MCPToolResult:
            """Execute a command on a stack using experimental features.
            
            Args:
                stack_path: Path to the stack
                command: Command to execute (e.g., plan, apply, destroy)
                dry_run: Whether to run in dry-run mode (default: False)
            """
            try:
                start_time = datetime.now()
                
                if not self.config.is_experimental_enabled("stacks_enabled"):
                    return MCPToolResult(
                        success=False,
                        message="Stacks experimental feature is disabled",
                        error_details="Enable stacks in configuration to use this feature"
                    )
                
                # Execute the stack command
                execution = await self.stack_manager.execute_stack_command(
                    stack_path, command, dry_run
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                success = execution.status == StackStatus.DEPLOYED
                
                return MCPToolResult(
                    success=success,
                    message=f"Stack command '{command}' {'completed successfully' if success else 'failed'} for {stack_path}",
                    data={
                        "execution": {
                            "id": execution.id,
                            "stack_path": execution.stack_path,
                            "command": execution.command,
                            "status": execution.status.value,
                            "started_at": execution.started_at.isoformat() if execution.started_at else None,
                            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                            "execution_plan": execution.execution_plan,
                            "unit_results": execution.unit_results,
                            "metadata": execution.metadata,
                        }
                    },
                    execution_time=execution_time,
                    resource_id=stack_path,
                    error_details=execution.error_message if not success else None
                )
                
            except Exception as e:
                logger.error(f"Failed to execute stack command {command} on {stack_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to execute stack command {command} on {stack_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_stack_outputs(stack_path: str) -> MCPToolResult:
            """Get outputs from a stack using experimental features.
            
            Args:
                stack_path: Path to the stack
            """
            try:
                start_time = datetime.now()
                
                if not self.config.is_experimental_enabled("stack_outputs"):
                    return MCPToolResult(
                        success=False,
                        message="Stack outputs experimental feature is disabled",
                        error_details="Enable stack_outputs in configuration to use this feature"
                    )
                
                outputs = await self.stack_manager.get_stack_outputs(stack_path)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=True,
                    message=f"Retrieved stack outputs for {stack_path}",
                    data={
                        "stack_path": stack_path,
                        "outputs": outputs,
                        "output_count": len(outputs),
                    },
                    execution_time=execution_time,
                    resource_id=stack_path
                )
                
            except Exception as e:
                logger.error(f"Failed to get stack outputs for {stack_path}: {e}")
                return MCPToolResult(
                    success=False,
                    message=f"Failed to get stack outputs for {stack_path}",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_enhanced_infrastructure_status(
            environment: Optional[str] = None,
            include_stacks: bool = True,
            include_costs: bool = False
        ) -> MCPToolResult:
            """Get enhanced infrastructure status including experimental features.
            
            Args:
                environment: Filter by environment (optional)
                include_stacks: Whether to include stack information (default: True)
                include_costs: Whether to include cost information (default: False)
            """
            try:
                start_time = datetime.now()
                
                # Get traditional resources
                resources = await self.terragrunt_manager.discover_resources(environment)
                
                # Calculate traditional metrics
                total_resources = len(resources)
                deployed_resources = len([r for r in resources if r.status.value == "deployed"])
                failed_resources = len([r for r in resources if r.status.value == "failed"])
                outdated_resources = len([r for r in resources if r.status.value == "outdated"])
                drift_detected = len([r for r in resources if r.status.value == "drift_detected"])
                
                # Calculate health score
                from .utils import calculate_health_score
                health_score = calculate_health_score(
                    total_resources, deployed_resources, failed_resources, drift_detected
                )
                
                status_data = {
                    "environment": environment or "all",
                    "traditional_resources": {
                        "total_resources": total_resources,
                        "deployed_resources": deployed_resources,
                        "failed_resources": failed_resources,
                        "outdated_resources": outdated_resources,
                        "drift_detected": drift_detected,
                        "health_score": health_score,
                    },
                    "last_check": datetime.now().isoformat(),
                    "experimental_features": {
                        "stacks_enabled": self.config.is_experimental_enabled("stacks_enabled"),
                        "enhanced_dependency_resolution": self.config.is_experimental_enabled("enhanced_dependency_resolution"),
                        "parallel_execution": self.config.is_experimental_enabled("parallel_execution"),
                    }
                }
                
                # Add stack information if enabled and requested
                if include_stacks and self.config.is_experimental_enabled("stacks_enabled"):
                    try:
                        stacks = await self.stack_manager.discover_stacks(environment)
                        
                        total_stacks = len(stacks)
                        deployed_stacks = len([s for s in stacks if s.status == StackStatus.DEPLOYED])
                        failed_stacks = len([s for s in stacks if s.status == StackStatus.FAILED])
                        
                        stack_health_score = calculate_health_score(
                            total_stacks, deployed_stacks, failed_stacks, 0
                        )
                        
                        status_data["stacks"] = {
                            "total_stacks": total_stacks,
                            "deployed_stacks": deployed_stacks,
                            "failed_stacks": failed_stacks,
                            "stack_health_score": stack_health_score,
                            "stack_breakdown": [
                                {
                                    "name": stack.name,
                                    "path": stack.path,
                                    "status": stack.status.value,
                                    "unit_count": len(stack.units),
                                }
                                for stack in stacks
                            ]
                        }
                    except Exception as e:
                        logger.warning(f"Failed to get stack information: {e}")
                        status_data["stacks"] = {"error": str(e)}
                
                # Add resource type breakdown
                status_data["resource_breakdown"] = {}
                for resource_type in ResourceType:
                    type_resources = [r for r in resources if r.type == resource_type]
                    if type_resources:
                        status_data["resource_breakdown"][resource_type.value] = {
                            "total": len(type_resources),
                            "deployed": len([r for r in type_resources if r.status.value == "deployed"]),
                            "failed": len([r for r in type_resources if r.status.value == "failed"])
                        }
                
                if include_costs:
                    # Placeholder for cost information
                    status_data["cost_info"] = {
                        "message": "Cost analysis not yet implemented",
                        "total_cost": 0.0,
                        "currency": "USD"
                    }
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=True,
                    message=f"Enhanced infrastructure status retrieved for {environment or 'all environments'}",
                    data=status_data,
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to get enhanced infrastructure status: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to get enhanced infrastructure status",
                    error_details=str(e)
                )

        # Keep existing tools for backward compatibility
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
                        "status": matching_resource.status.value,
                        "unit_type": matching_resource.unit_type.value,
                        "stack_path": matching_resource.stack_path,
                        "parent_stack": matching_resource.parent_stack,
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
        async def draw_resource_tree(
            environment: Optional[str] = None,
            format: str = "tree",
            include_dependencies: bool = True,
            max_depth: Optional[int] = None
        ) -> MCPToolResult:
            """Draw a visual resource tree using Terragrunt CLI redesign commands.
            
            Args:
                environment: Filter by environment (optional)
                format: Output format ("tree", "dag", "json")
                include_dependencies: Whether to include dependency information (default: True)
                max_depth: Maximum depth to display (optional)
            """
            try:
                start_time = datetime.now()
                
                # Generate the resource tree
                tree_result = await self.terragrunt_manager.draw_resource_tree(
                    environment=environment,
                    format=format,
                    include_dependencies=include_dependencies,
                    max_depth=max_depth
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=True,
                    message=f"Generated resource tree in {format} format for {environment or 'all environments'}",
                    data={
                        "tree_data": tree_result,
                        "visual_tree": tree_result["visual_representation"],
                        "summary": {
                            "total_resources": tree_result["total_resources"],
                            "format": tree_result["format"],
                            "environment_filter": tree_result["environment_filter"],
                            "include_dependencies": include_dependencies,
                            "max_depth": max_depth,
                        }
                    },
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to draw resource tree: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to draw resource tree",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_dependency_graph(
            environment: Optional[str] = None,
            output_format: str = "dot"
        ) -> MCPToolResult:
            """Get dependency graph using Terragrunt CLI redesign commands.
            
            Args:
                environment: Filter by environment (optional)
                output_format: Output format ("dot", "json", "mermaid")
            """
            try:
                start_time = datetime.now()
                
                # Generate the dependency graph
                graph_result = await self.terragrunt_manager.get_dependency_graph(
                    environment=environment,
                    output_format=output_format
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=True,
                    message=f"Generated dependency graph in {output_format} format for {environment or 'all environments'}",
                    data={
                        "graph_data": graph_result["graph_data"],
                        "metadata": {
                            "format": graph_result["format"],
                            "environment_filter": graph_result["environment_filter"],
                            "command_used": graph_result["command_used"],
                            "generated_at": graph_result["generated_at"],
                        }
                    },
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to get dependency graph: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to get dependency graph",
                    error_details=str(e)
                )

        @self.app.tool()
        async def visualize_infrastructure(
            environment: Optional[str] = None,
            visualization_type: str = "tree",
            include_dependencies: bool = True,
            output_format: str = "ascii"
        ) -> MCPToolResult:
            """Comprehensive infrastructure visualization using Terragrunt CLI redesign.
            
            Args:
                environment: Filter by environment (optional)
                visualization_type: Type of visualization ("tree", "dag", "hierarchy")
                include_dependencies: Whether to include dependency information (default: True)
                output_format: Output format ("ascii", "dot", "mermaid", "json")
            """
            try:
                start_time = datetime.now()
                
                results = {}
                
                if visualization_type in ["tree", "hierarchy"]:
                    # Generate tree visualization
                    tree_format = "tree" if output_format == "ascii" else output_format
                    tree_result = await self.terragrunt_manager.draw_resource_tree(
                        environment=environment,
                        format=tree_format,
                        include_dependencies=include_dependencies,
                        max_depth=None
                    )
                    results["tree"] = tree_result
                
                if visualization_type in ["dag", "dependencies"] or include_dependencies:
                    # Generate dependency graph
                    graph_format = "dot" if output_format == "ascii" else output_format
                    graph_result = await self.terragrunt_manager.get_dependency_graph(
                        environment=environment,
                        output_format=graph_format
                    )
                    results["dependency_graph"] = graph_result
                
                # Create comprehensive visualization
                visualization_data = {
                    "environment": environment or "all",
                    "visualization_type": visualization_type,
                    "output_format": output_format,
                    "include_dependencies": include_dependencies,
                    "results": results,
                    "summary": {
                        "total_visualizations": len(results),
                        "available_formats": ["ascii", "dot", "mermaid", "json"],
                        "available_types": ["tree", "dag", "hierarchy"],
                    }
                }
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=True,
                    message=f"Generated {visualization_type} visualization in {output_format} format",
                    data=visualization_data,
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to visualize infrastructure: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to visualize infrastructure",
                    error_details=str(e)
                )

        # Add other existing tools here for backward compatibility...
        # (validate_resource_config, plan_resource_deployment, apply_resource_deployment, etc.)

        @self.app.tool()
        async def get_autodevops_system_prompt(
            variant: str = "compact",
            format: str = "text"
        ) -> MCPToolResult:
            """Get AutoDevOps system prompt for LLM integration.
            
            Args:
                variant: Prompt variant ("compact", "extended", "cli")
                format: Output format ("text", "json", "context")
            """
            try:
                from .autodevops_prompt import get_system_prompt, create_autodevops_context
                
                if format == "context":
                    # Return full context information
                    context = create_autodevops_context()
                    context["system_prompt"] = get_system_prompt(variant)
                    
                    return MCPToolResult(
                        success=True,
                        message=f"Retrieved AutoDevOps context with {variant} prompt",
                        data={
                            "context": context,
                            "variant": variant,
                            "usage": "Inject this into LLM conversations for AutoDevOps assistance"
                        }
                    )
                
                elif format == "json":
                    # Return structured JSON
                    return MCPToolResult(
                        success=True,
                        message=f"Retrieved AutoDevOps {variant} system prompt",
                        data={
                            "system_prompt": get_system_prompt(variant),
                            "variant": variant,
                            "role": "system",
                            "purpose": "AutoDevOps Infrastructure Assistant",
                            "integration_guide": {
                                "claude_desktop": "Add this prompt to your Claude Desktop configuration",
                                "api": "Include as system message in API calls",
                                "cli": "Use with --system-prompt flag in CLI tools"
                            }
                        }
                    )
                
                else:  # text format
                    prompt = get_system_prompt(variant)
                    
                    return MCPToolResult(
                        success=True,
                        message=f"Retrieved AutoDevOps {variant} system prompt",
                        data={
                            "system_prompt": prompt,
                            "variant": variant,
                            "character_count": len(prompt),
                            "word_count": len(prompt.split())
                        }
                    )
                
            except Exception as e:
                logger.error(f"Failed to get AutoDevOps system prompt: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to get AutoDevOps system prompt",
                    error_details=str(e)
                )

        # Cost Management Tools
        @self.app.tool()
        async def get_cost_analysis(
            environment: Optional[str] = None,
            period_days: int = 30,
            include_forecasting: bool = True,
            include_recommendations: bool = True
        ) -> MCPToolResult:
            """Get comprehensive cost analysis for infrastructure.
            
            Args:
                environment: Filter by environment (optional)
                period_days: Analysis period in days (default: 30)
                include_forecasting: Include cost forecasting (default: True)
                include_recommendations: Include optimization recommendations (default: True)
            """
            try:
                start_time = datetime.now()
                
                cost_analysis = await self.cost_manager.get_cost_analysis(
                    environment=environment,
                    period_days=period_days,
                    include_forecasting=include_forecasting,
                    include_recommendations=include_recommendations
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=True,
                    message=f"Cost analysis completed for {environment or 'all environments'} ({period_days} days)",
                    data={
                        "cost_analysis": {
                            "total_cost": cost_analysis.total_cost,
                            "currency": cost_analysis.currency,
                            "period": cost_analysis.period,
                            "breakdown_by_service": cost_analysis.breakdown_by_service,
                            "breakdown_by_environment": cost_analysis.breakdown_by_environment,
                            "breakdown_by_resource": cost_analysis.breakdown_by_resource,
                            "trends": cost_analysis.trends,
                            "forecast": cost_analysis.forecast,
                            "recommendations": cost_analysis.recommendations,
                            "last_updated": cost_analysis.last_updated.isoformat(),
                            "metadata": cost_analysis.metadata
                        },
                        "summary": {
                            "total_cost": cost_analysis.total_cost,
                            "top_services": sorted(
                                cost_analysis.breakdown_by_service.items(), 
                                key=lambda x: x[1], 
                                reverse=True
                            )[:5],
                            "recommendations_count": len(cost_analysis.recommendations),
                            "has_forecast": cost_analysis.forecast is not None
                        }
                    },
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to get cost analysis: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to get cost analysis",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_cost_alerts(
            threshold_percentage: float = 80.0
        ) -> MCPToolResult:
            """Get cost alerts based on budget thresholds and unusual spending patterns.
            
            Args:
                threshold_percentage: Budget threshold percentage for alerts (default: 80.0)
            """
            try:
                start_time = datetime.now()
                
                alerts = await self.cost_manager.get_cost_alerts(threshold_percentage)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Categorize alerts by severity
                high_severity = [alert for alert in alerts if alert.get("severity") == "high"]
                medium_severity = [alert for alert in alerts if alert.get("severity") == "medium"]
                low_severity = [alert for alert in alerts if alert.get("severity") == "low"]
                
                return MCPToolResult(
                    success=True,
                    message=f"Found {len(alerts)} cost alerts",
                    data={
                        "alerts": alerts,
                        "summary": {
                            "total_alerts": len(alerts),
                            "high_severity": len(high_severity),
                            "medium_severity": len(medium_severity),
                            "low_severity": len(low_severity),
                            "threshold_percentage": threshold_percentage
                        },
                        "categorized_alerts": {
                            "high": high_severity,
                            "medium": medium_severity,
                            "low": low_severity
                        }
                    },
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to get cost alerts: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to get cost alerts",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_cost_optimization_score() -> MCPToolResult:
            """Get cost optimization score for the infrastructure."""
            try:
                start_time = datetime.now()
                
                optimization_score = await self.cost_manager.get_cost_optimization_score()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MCPToolResult(
                    success=True,
                    message=f"Cost optimization score: {optimization_score['grade']} ({optimization_score['score']:.1f}/100)",
                    data={
                        "optimization_score": optimization_score,
                        "interpretation": {
                            "grade": optimization_score["grade"],
                            "score": optimization_score["score"],
                            "status": "excellent" if optimization_score["score"] >= 90 
                                     else "good" if optimization_score["score"] >= 80
                                     else "fair" if optimization_score["score"] >= 70
                                     else "poor",
                            "recommendations_needed": optimization_score.get("recommendations_count", 0) > 0
                        }
                    },
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to get cost optimization score: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to get cost optimization score",
                    error_details=str(e)
                )

        @self.app.tool()
        async def get_cost_status(
            environment: Optional[str] = None,
            include_alerts: bool = True,
            include_optimization_score: bool = True
        ) -> MCPToolResult:
            """Get comprehensive cost status including analysis, alerts, and optimization score.
            
            Args:
                environment: Filter by environment (optional)
                include_alerts: Include cost alerts (default: True)
                include_optimization_score: Include optimization score (default: True)
            """
            try:
                start_time = datetime.now()
                
                # Get cost analysis
                cost_analysis = await self.cost_manager.get_cost_analysis(
                    environment=environment,
                    period_days=30,
                    include_forecasting=True,
                    include_recommendations=True
                )
                
                status_data = {
                    "cost_summary": {
                        "total_cost": cost_analysis.total_cost,
                        "currency": cost_analysis.currency,
                        "period": cost_analysis.period,
                        "environment_filter": environment,
                        "last_updated": cost_analysis.last_updated.isoformat()
                    },
                    "service_breakdown": cost_analysis.breakdown_by_service,
                    "environment_breakdown": cost_analysis.breakdown_by_environment,
                    "trends": cost_analysis.trends[-7:] if cost_analysis.trends else [],  # Last 7 days
                    "forecast": cost_analysis.forecast,
                    "recommendations": cost_analysis.recommendations
                }
                
                # Add alerts if requested
                if include_alerts:
                    alerts = await self.cost_manager.get_cost_alerts()
                    status_data["alerts"] = {
                        "total_count": len(alerts),
                        "alerts": alerts,
                        "has_critical_alerts": any(alert.get("severity") == "high" for alert in alerts)
                    }
                
                # Add optimization score if requested
                if include_optimization_score:
                    optimization_score = await self.cost_manager.get_cost_optimization_score()
                    status_data["optimization"] = optimization_score
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Determine overall status
                overall_status = "healthy"
                if include_alerts and status_data.get("alerts", {}).get("has_critical_alerts"):
                    overall_status = "critical"
                elif include_optimization_score and optimization_score.get("score", 100) < 70:
                    overall_status = "needs_attention"
                elif cost_analysis.total_cost == 0:
                    overall_status = "no_data"
                
                return MCPToolResult(
                    success=True,
                    message=f"Cost status: {overall_status} - Total: ${cost_analysis.total_cost:.2f}",
                    data={
                        "overall_status": overall_status,
                        "cost_status": status_data,
                        "summary": {
                            "total_cost": cost_analysis.total_cost,
                            "top_service": max(cost_analysis.breakdown_by_service.items(), key=lambda x: x[1])[0] if cost_analysis.breakdown_by_service else "none",
                            "alerts_count": len(status_data.get("alerts", {}).get("alerts", [])),
                            "recommendations_count": len(cost_analysis.recommendations),
                            "optimization_grade": optimization_score.get("grade", "N/A") if include_optimization_score else "N/A"
                        }
                    },
                    execution_time=execution_time
                )
                
            except Exception as e:
                logger.error(f"Failed to get cost status: {e}")
                return MCPToolResult(
                    success=False,
                    message="Failed to get cost status",
                    error_details=str(e)
                )

        # Add other existing tools here for backward compatibility...
        # (validate_resource_config, plan_resource_deployment, apply_resource_deployment, etc.)

    def run(self):
        """Run the MCP server."""
        logger.info("Starting Terragrunt GCP MCP Server with Experimental Features")
        
        # Log experimental features status
        if self.config.is_experimental_enabled("stacks_enabled"):
            logger.info("✨ Experimental stacks feature is ENABLED")
        else:
            logger.warning("⚠️  Experimental stacks feature is DISABLED")
        
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