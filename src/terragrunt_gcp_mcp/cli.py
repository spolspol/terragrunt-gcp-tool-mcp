"""Command line interface for Terragrunt GCP MCP Tool."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .config import Config
from .server import TerragruntGCPMCPServer
from .terragrunt_manager import TerragruntManager
from .stack_manager import StackManager
from .cost_manager import CostManager
from .utils import setup_logging


console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--config", 
    "-c", 
    type=click.Path(exists=True), 
    help="Path to configuration file"
)
@click.option(
    "--verbose", 
    "-v", 
    is_flag=True, 
    help="Enable verbose logging"
)
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """Terragrunt GCP MCP Tool - Infrastructure automation and management."""
    # Set up logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load configuration
    try:
        ctx.ensure_object(dict)
        ctx.obj["config_path"] = config
        ctx.obj["verbose"] = verbose
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def server(ctx):
    """Start the MCP server."""
    try:
        config_path = ctx.obj.get("config_path")
        server_instance = TerragruntGCPMCPServer(config_path)
        
        console.print(f"[green]Starting MCP server...[/green]")
        server_instance.run()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting server: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.pass_context
def list_resources(ctx, environment: Optional[str], format: str):
    """List all Terragrunt resources."""
    async def _list_resources():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print("[blue]Discovering resources...[/blue]")
            resources = await manager.discover_resources(environment)
            
            if format == "json":
                import json
                resource_data = []
                for resource in resources:
                    resource_data.append({
                        "name": resource.name,
                        "type": resource.type.value,
                        "path": resource.path,
                        "environment": resource.environment,
                        "status": resource.status.value,
                        "region": resource.region
                    })
                console.print(json.dumps(resource_data, indent=2))
            else:
                # Table format
                table = Table(title=f"Terragrunt Resources {f'({environment})' if environment else ''}")
                table.add_column("Name", style="cyan")
                table.add_column("Type", style="magenta")
                table.add_column("Environment", style="green")
                table.add_column("Status", style="yellow")
                table.add_column("Region", style="blue")
                
                for resource in resources:
                    table.add_row(
                        resource.name,
                        resource.type.value,
                        resource.environment,
                        resource.status.value,
                        resource.region or "N/A"
                    )
                
                console.print(table)
                console.print(f"\n[green]Found {len(resources)} resources[/green]")
                
        except Exception as e:
            console.print(f"[red]Error listing resources: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_list_resources())


@cli.command()
@click.argument("resource_path")
@click.option(
    "--check-dependencies", 
    is_flag=True, 
    default=True,
    help="Also validate dependencies (default: True)"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.pass_context
def validate_resource(ctx, resource_path: str, check_dependencies: bool, format: str):
    """Validate a Terragrunt resource configuration."""
    async def _validate_resource():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print(f"[blue]Validating resource: {resource_path}[/blue]")
            
            # Find the resource
            all_resources = await manager.discover_resources()
            matching_resource = None
            
            for resource in all_resources:
                if resource.path == resource_path or resource.name == resource_path:
                    matching_resource = resource
                    break
            
            if not matching_resource:
                console.print(f"[red]Resource not found: {resource_path}[/red]")
                console.print("[yellow]Available resources:[/yellow]")
                for resource in all_resources[:10]:
                    console.print(f"  - {resource.path} ({resource.name})")
                if len(all_resources) > 10:
                    console.print(f"  ... and {len(all_resources) - 10} more")
                sys.exit(1)
            
            # Validate the resource
            validation_result = await manager.validate_resource(matching_resource.path)
            
            # Check dependencies if requested
            dependency_results = []
            if check_dependencies and matching_resource.dependencies:
                console.print(f"[blue]Checking {len(matching_resource.dependencies)} dependencies...[/blue]")
                for dep_path in matching_resource.dependencies:
                    try:
                        dep_validation = await manager.validate_resource(dep_path)
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
            
            if format == "json":
                import json
                result_data = {
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
                }
                console.print(json.dumps(result_data, indent=2))
            else:
                # Table format
                table = Table(title=f"Validation Results: {matching_resource.name}")
                table.add_column("Attribute", style="cyan", width=20)
                table.add_column("Value", style="white", width=60)
                
                # Basic info
                table.add_row("Resource Name", matching_resource.name)
                table.add_row("Resource Type", matching_resource.type.value)
                table.add_row("Resource Path", matching_resource.path)
                
                # Validation results
                status = "✅ Valid" if validation_result.valid else "❌ Invalid"
                table.add_row("Validation Status", status)
                
                if validation_result.errors:
                    errors_str = "\n".join(validation_result.errors)
                    table.add_row("Errors", errors_str)
                
                if validation_result.warnings:
                    warnings_str = "\n".join(validation_result.warnings)
                    table.add_row("Warnings", warnings_str)
                
                table.add_row("Validated At", validation_result.validated_at.strftime("%Y-%m-%d %H:%M:%S"))
                
                console.print(table)
                
                # Dependencies table
                if check_dependencies and dependency_results:
                    console.print(f"\n[yellow]Dependency Validation Results ({len(dependency_results)}):[/yellow]")
                    dep_table = Table()
                    dep_table.add_column("Dependency", style="cyan")
                    dep_table.add_column("Status", style="white")
                    dep_table.add_column("Issues", style="red")
                    
                    for dep in dependency_results:
                        status = "✅ Valid" if dep["valid"] else "❌ Invalid"
                        issues = "; ".join(dep["errors"]) if dep["errors"] else "None"
                        dep_table.add_row(dep["path"], status, issues)
                    
                    console.print(dep_table)
                
                # Summary
                if validation_result.valid:
                    console.print(f"\n[green]✅ Resource {matching_resource.name} is valid[/green]")
                else:
                    console.print(f"\n[red]❌ Resource {matching_resource.name} has validation errors[/red]")
                    sys.exit(1)
                
        except Exception as e:
            console.print(f"[red]Error validating resource: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_validate_resource())


@cli.command()
@click.argument("resource_path")
@click.option(
    "--dry-run", 
    is_flag=True, 
    default=True,
    help="Run in dry-run mode (default: True)"
)
@click.option(
    "--save-plan", 
    is_flag=True, 
    help="Save the plan file for later use"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.pass_context
def plan_deployment(ctx, resource_path: str, dry_run: bool, save_plan: bool, format: str):
    """Generate a deployment plan for a resource."""
    async def _plan_deployment():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print(f"[blue]Planning deployment for: {resource_path}[/blue]")
            
            # Find the resource
            all_resources = await manager.discover_resources()
            matching_resource = None
            
            for resource in all_resources:
                if resource.path == resource_path or resource.name == resource_path:
                    matching_resource = resource
                    break
            
            if not matching_resource:
                console.print(f"[red]Resource not found: {resource_path}[/red]")
                sys.exit(1)
            
            # Validate first
            console.print("[blue]Validating resource before planning...[/blue]")
            validation_result = await manager.validate_resource(matching_resource.path)
            if not validation_result.valid:
                console.print("[red]❌ Resource validation failed. Cannot proceed with planning.[/red]")
                console.print("[red]Errors:[/red]")
                for error in validation_result.errors:
                    console.print(f"  - {error}")
                sys.exit(1)
            
            console.print("[green]✅ Resource validation passed[/green]")
            
            # Generate plan
            plan = await manager.plan_resource(matching_resource.path, dry_run)
            
            # Analyze changes
            changes_summary = {
                "total_changes": len(plan.changes),
                "has_changes": len(plan.changes) > 0,
                "changes_by_action": {}
            }
            
            for change in plan.changes:
                action = change.get("action", "unknown")
                changes_summary["changes_by_action"][action] = changes_summary["changes_by_action"].get(action, 0) + 1
            
            if format == "json":
                import json
                result_data = {
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
                }
                console.print(json.dumps(result_data, indent=2))
            else:
                # Table format
                table = Table(title=f"Deployment Plan: {matching_resource.name}")
                table.add_column("Attribute", style="cyan", width=20)
                table.add_column("Value", style="white", width=60)
                
                table.add_row("Plan ID", plan.id)
                table.add_row("Resource", matching_resource.name)
                table.add_row("Type", matching_resource.type.value)
                table.add_row("Status", plan.status.value)
                table.add_row("Dry Run", "Yes" if dry_run else "No")
                table.add_row("Save Plan", "Yes" if save_plan else "No")
                table.add_row("Created", plan.created_at.strftime("%Y-%m-%d %H:%M:%S"))
                table.add_row("Total Changes", str(changes_summary["total_changes"]))
                
                if changes_summary["changes_by_action"]:
                    actions_str = ", ".join([f"{action}: {count}" for action, count in changes_summary["changes_by_action"].items()])
                    table.add_row("Changes by Action", actions_str)
                
                console.print(table)
                
                # Show changes if any
                if plan.changes:
                    console.print(f"\n[yellow]Planned Changes ({len(plan.changes)}):[/yellow]")
                    for i, change in enumerate(plan.changes[:10], 1):  # Show first 10
                        action = change.get("action", "unknown")
                        resource_name = change.get("name", "unknown")
                        console.print(f"  {i}. {action}: {resource_name}")
                    
                    if len(plan.changes) > 10:
                        console.print(f"  ... and {len(plan.changes) - 10} more changes")
                else:
                    console.print("\n[green]No changes detected[/green]")
                
                console.print(f"\n[green]✅ Plan generated successfully[/green]")
                
        except Exception as e:
            console.print(f"[red]Error planning deployment: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_plan_deployment())


@cli.command()
@click.argument("resource_path")
@click.option(
    "--auto-approve", 
    is_flag=True, 
    help="Skip confirmation prompt and validation"
)
@click.option(
    "--plan-file", 
    type=str, 
    help="Use a specific plan file"
)
@click.option(
    "--notify", 
    is_flag=True, 
    default=True,
    help="Send notification on completion (default: True)"
)
@click.pass_context
def apply_deployment(ctx, resource_path: str, auto_approve: bool, plan_file: Optional[str], notify: bool):
    """Apply changes to a resource."""
    async def _apply_deployment():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print(f"[blue]Applying deployment for: {resource_path}[/blue]")
            
            # Find the resource
            all_resources = await manager.discover_resources()
            matching_resource = None
            
            for resource in all_resources:
                if resource.path == resource_path or resource.name == resource_path:
                    matching_resource = resource
                    break
            
            if not matching_resource:
                console.print(f"[red]Resource not found: {resource_path}[/red]")
                sys.exit(1)
            
            # Safety check unless auto-approved
            if not auto_approve:
                console.print("[blue]Validating resource before deployment...[/blue]")
                validation_result = await manager.validate_resource(matching_resource.path)
                if not validation_result.valid:
                    console.print("[red]❌ Resource validation failed. Cannot proceed with deployment.[/red]")
                    console.print("[red]Errors:[/red]")
                    for error in validation_result.errors:
                        console.print(f"  - {error}")
                    console.print("\n[yellow]Use --auto-approve to bypass validation[/yellow]")
                    sys.exit(1)
                
                console.print("[green]✅ Resource validation passed[/green]")
                
                # Confirmation prompt
                if not click.confirm(f"\nApply deployment to {matching_resource.name}?"):
                    console.print("[yellow]Deployment cancelled[/yellow]")
                    return
            
            # Apply deployment
            console.print(f"[blue]Applying changes to: {matching_resource.name}[/blue]")
            result = await manager.apply_resource(matching_resource.path, plan_file)
            
            success = result.exit_code == 0
            
            if success:
                console.print(f"[green]✅ Deployment completed successfully for {matching_resource.name}[/green]")
                console.print(f"Execution time: {result.execution_time:.2f}s")
                
                if notify:
                    console.print("[blue]📢 Notification sent[/blue]")
                
                # Show summary of output
                if result.stdout:
                    lines = result.stdout.split('\n')
                    if len(lines) > 10:
                        console.print("\n[yellow]Output (last 10 lines):[/yellow]")
                        for line in lines[-10:]:
                            if line.strip():
                                console.print(f"  {line}")
                    else:
                        console.print(f"\n[yellow]Output:[/yellow]\n{result.stdout}")
            else:
                console.print(f"[red]❌ Deployment failed for {matching_resource.name}[/red]")
                console.print(f"Exit code: {result.exit_code}")
                console.print(f"Execution time: {result.execution_time:.2f}s")
                
                if result.stderr:
                    console.print(f"\n[red]Error output:[/red]\n{result.stderr}")
                
                sys.exit(1)
                
        except Exception as e:
            console.print(f"[red]Error applying deployment: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_apply_deployment())


@cli.command()
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.option(
    "--include-costs", 
    is_flag=True, 
    help="Include cost information"
)
@click.pass_context
def status(ctx, environment: Optional[str], include_costs: bool):
    """Get infrastructure status."""
    async def _status():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print("[blue]Getting infrastructure status...[/blue]")
            resources = await manager.discover_resources(environment)
            
            # Calculate metrics
            total = len(resources)
            deployed = len([r for r in resources if r.status.value == "deployed"])
            failed = len([r for r in resources if r.status.value == "failed"])
            
            # Create status table
            table = Table(title="Infrastructure Status")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Resources", str(total))
            table.add_row("Deployed", str(deployed))
            table.add_row("Failed", str(failed))
            table.add_row("Success Rate", f"{(deployed/total*100):.1f}%" if total > 0 else "N/A")
            
            if environment:
                table.add_row("Environment", environment)
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error getting status: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_status())


@cli.command()
@click.argument("resource_path")
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.option(
    "--include-config", 
    is_flag=True, 
    help="Include full configuration content"
)
@click.pass_context
def get_resource(ctx, resource_path: str, format: str, include_config: bool):
    """Get detailed information about a specific resource."""
    async def _get_resource():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print(f"[blue]Getting resource information for: {resource_path}[/blue]")
            
            # First, discover all resources to find the matching one
            all_resources = await manager.discover_resources()
            matching_resource = None
            
            for resource in all_resources:
                if resource.path == resource_path or resource.name == resource_path:
                    matching_resource = resource
                    break
            
            if not matching_resource:
                console.print(f"[red]Resource not found: {resource_path}[/red]")
                console.print("[yellow]Available resources:[/yellow]")
                for resource in all_resources[:10]:  # Show first 10
                    console.print(f"  - {resource.path} ({resource.name})")
                if len(all_resources) > 10:
                    console.print(f"  ... and {len(all_resources) - 10} more")
                sys.exit(1)
            
            # Get additional state information
            try:
                state_info = await manager.get_state_info(matching_resource.path)
            except Exception as e:
                state_info = {"error": str(e)}
            
            # Get validation information
            try:
                validation_result = await manager.validate_resource(matching_resource.path)
            except Exception as e:
                validation_result = None
            
            if format == "json":
                import json
                resource_data = {
                    "name": matching_resource.name,
                    "type": matching_resource.type.value,
                    "path": matching_resource.path,
                    "environment": matching_resource.environment,
                    "environment_type": matching_resource.environment_type,
                    "region": matching_resource.region,
                    "status": matching_resource.status.value,
                    "dependencies": matching_resource.dependencies,
                    "last_modified": matching_resource.last_modified.isoformat() if matching_resource.last_modified else None,
                    "last_deployed": matching_resource.last_deployed.isoformat() if matching_resource.last_deployed else None,
                    "state_info": state_info,
                    "validation": {
                        "valid": validation_result.valid if validation_result else None,
                        "errors": validation_result.errors if validation_result else [],
                        "warnings": validation_result.warnings if validation_result else []
                    } if validation_result else None
                }
                
                if include_config:
                    resource_data["configuration"] = matching_resource.configuration
                
                console.print(json.dumps(resource_data, indent=2))
            else:
                # Table format
                table = Table(title=f"Resource Details: {matching_resource.name}")
                table.add_column("Attribute", style="cyan", width=20)
                table.add_column("Value", style="white", width=60)
                
                # Basic information
                table.add_row("Name", matching_resource.name)
                table.add_row("Type", matching_resource.type.value)
                table.add_row("Path", matching_resource.path)
                table.add_row("Environment", matching_resource.environment)
                table.add_row("Environment Type", matching_resource.environment_type)
                table.add_row("Region", matching_resource.region or "N/A")
                table.add_row("Status", matching_resource.status.value)
                
                # Timestamps
                if matching_resource.last_modified:
                    table.add_row("Last Modified", matching_resource.last_modified.strftime("%Y-%m-%d %H:%M:%S"))
                if matching_resource.last_deployed:
                    table.add_row("Last Deployed", matching_resource.last_deployed.strftime("%Y-%m-%d %H:%M:%S"))
                
                # Dependencies
                if matching_resource.dependencies:
                    deps_str = "\n".join(matching_resource.dependencies)
                    table.add_row("Dependencies", deps_str)
                else:
                    table.add_row("Dependencies", "None")
                
                # State information
                if isinstance(state_info, dict) and "resources" in state_info:
                    resource_count = state_info.get("resource_count", 0)
                    table.add_row("State Resources", str(resource_count))
                elif isinstance(state_info, dict) and "error" in state_info:
                    table.add_row("State Info", f"Error: {state_info['error']}")
                
                # Validation
                if validation_result:
                    validation_status = "✓ Valid" if validation_result.valid else "✗ Invalid"
                    table.add_row("Validation", validation_status)
                    
                    if validation_result.errors:
                        errors_str = "\n".join(validation_result.errors)
                        table.add_row("Validation Errors", errors_str)
                    
                    if validation_result.warnings:
                        warnings_str = "\n".join(validation_result.warnings)
                        table.add_row("Validation Warnings", warnings_str)
                
                # Configuration (if requested)
                if include_config and matching_resource.configuration:
                    config_str = ""
                    for key, value in matching_resource.configuration.items():
                        if key == "content" and len(str(value)) > 200:
                            config_str += f"{key}: [Content too long, use --format json to see full content]\n"
                        else:
                            config_str += f"{key}: {value}\n"
                    table.add_row("Configuration", config_str.strip())
                
                console.print(table)
                
                # Show state details if available
                if isinstance(state_info, dict) and "resources" in state_info and state_info["resources"]:
                    console.print(f"\n[yellow]Terraform State Resources ({len(state_info['resources'])}):[/yellow]")
                    for i, resource in enumerate(state_info["resources"][:10]):  # Show first 10
                        console.print(f"  {i+1}. {resource}")
                    if len(state_info["resources"]) > 10:
                        console.print(f"  ... and {len(state_info['resources']) - 10} more")
                
        except Exception as e:
            console.print(f"[red]Error getting resource information: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_get_resource())


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize a new configuration file."""
    try:
        config_path = click.prompt("Configuration file path", default="config/config.yaml")
        terragrunt_path = click.prompt("Terragrunt root path", default="../terragrunt-gcp-org-automation")
        
        # Create configuration
        config = Config()
        config.terragrunt.root_path = terragrunt_path
        
        # Save configuration
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        config.save_to_file(config_path)
        
        console.print(f"[green]✓ Configuration saved to {config_path}[/green]")
        console.print("[blue]You can now edit the configuration file with your settings[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error initializing configuration: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--dag", 
    is_flag=True, 
    help="Show dependency graph information"
)
@click.option(
    "--json", 
    "output_json",
    is_flag=True, 
    help="Output in JSON format"
)
@click.option(
    "--dependencies", 
    is_flag=True, 
    help="Include dependency information"
)
@click.pass_context
def find(ctx, dag: bool, output_json: bool, dependencies: bool):
    """Find and discover Terragrunt configurations (replaces output-module-groups)."""
    async def _find():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print("[blue]Finding Terragrunt configurations...[/blue]")
            resources = await manager.discover_resources()
            
            if output_json:
                import json
                result = []
                for resource in resources:
                    item = {
                        "type": "unit",
                        "path": resource.path.replace("live/", ""),  # Remove live/ prefix for cleaner output
                        "name": resource.name,
                        "resource_type": resource.type.value,
                        "environment": resource.environment
                    }
                    
                    if dependencies and resource.dependencies:
                        item["dependencies"] = [dep.replace("live/", "") for dep in resource.dependencies]
                    
                    result.append(item)
                
                console.print(json.dumps(result, indent=2))
            else:
                # Table format
                table = Table(title="Terragrunt Units")
                table.add_column("Path", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Type", style="green")
                table.add_column("Environment", style="yellow")
                if dependencies:
                    table.add_column("Dependencies", style="blue")
                
                for resource in resources:
                    row = [
                        resource.path.replace("live/", ""),
                        resource.name,
                        resource.type.value,
                        resource.environment
                    ]
                    if dependencies:
                        deps = ", ".join([dep.replace("live/", "") for dep in resource.dependencies]) if resource.dependencies else "None"
                        row.append(deps)
                    
                    table.add_row(*row)
                
                console.print(table)
                console.print(f"\n[green]Found {len(resources)} units[/green]")
                
        except Exception as e:
            console.print(f"[red]Error finding configurations: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_find())


@cli.command()
@click.option(
    "--dag", 
    is_flag=True, 
    help="Show dependency graph"
)
@click.option(
    "--tree", 
    is_flag=True, 
    help="Show tree format"
)
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.pass_context
def list_units(ctx, dag: bool, tree: bool, environment: Optional[str]):
    """List Terragrunt units with dependency information (replaces graph-dependencies)."""
    async def _list_units():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print("[blue]Listing Terragrunt units...[/blue]")
            resources = await manager.discover_resources(environment)
            
            if tree:
                # Build dependency tree
                console.print(f"[yellow]Dependency Tree{f' ({environment})' if environment else ''}:[/yellow]")
                
                # Find root nodes (no dependencies)
                root_nodes = [r for r in resources if not r.dependencies]
                
                def print_tree(resource, level=0, visited=None):
                    if visited is None:
                        visited = set()
                    
                    if resource.path in visited:
                        return
                    visited.add(resource.path)
                    
                    indent = "  " * level
                    prefix = "├── " if level > 0 else ""
                    console.print(f"{indent}{prefix}{resource.name} ({resource.type.value})")
                    
                    # Find dependents
                    dependents = [r for r in resources if resource.path in r.dependencies]
                    for dependent in dependents:
                        print_tree(dependent, level + 1, visited)
                
                if root_nodes:
                    for root in root_nodes:
                        print_tree(root)
                else:
                    console.print("No clear dependency hierarchy found")
            
            elif dag:
                # Show DAG information
                console.print(f"[yellow]Dependency Graph{f' ({environment})' if environment else ''}:[/yellow]")
                
                for resource in resources:
                    if resource.dependencies:
                        console.print(f"{resource.name} depends on:")
                        for dep in resource.dependencies:
                            dep_resource = next((r for r in resources if r.path == dep), None)
                            dep_name = dep_resource.name if dep_resource else dep
                            console.print(f"  - {dep_name}")
                    else:
                        console.print(f"{resource.name} (no dependencies)")
            
            else:
                # Simple list
                table = Table(title=f"Terragrunt Units{f' ({environment})' if environment else ''}")
                table.add_column("Name", style="cyan")
                table.add_column("Type", style="magenta")
                table.add_column("Environment", style="green")
                table.add_column("Dependencies", style="yellow")
                
                for resource in resources:
                    deps_count = len(resource.dependencies) if resource.dependencies else 0
                    table.add_row(
                        resource.name,
                        resource.type.value,
                        resource.environment,
                        str(deps_count)
                    )
                
                console.print(table)
                console.print(f"\n[green]Found {len(resources)} units[/green]")
                
        except Exception as e:
            console.print(f"[red]Error listing units: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_list_units())


@cli.command()
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["dot", "json"]), 
    default="dot", 
    help="Output format for the graph"
)
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.pass_context
def dag_graph(ctx, format: str, environment: Optional[str]):
    """Generate dependency graph (replaces graph-dependencies command)."""
    async def _dag_graph():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print("[blue]Generating dependency graph...[/blue]")
            resources = await manager.discover_resources(environment)
            
            if format == "json":
                import json
                graph_data = {
                    "nodes": [],
                    "edges": []
                }
                
                for resource in resources:
                    graph_data["nodes"].append({
                        "id": resource.path,
                        "name": resource.name,
                        "type": resource.type.value,
                        "environment": resource.environment
                    })
                    
                    for dep in resource.dependencies:
                        graph_data["edges"].append({
                            "from": dep,
                            "to": resource.path
                        })
                
                console.print(json.dumps(graph_data, indent=2))
            
            else:  # dot format
                console.print("digraph terragrunt_dependencies {")
                console.print("  rankdir=TB;")
                console.print("  node [shape=box];")
                
                for resource in resources:
                    node_id = resource.path.replace("/", "_").replace("-", "_")
                    console.print(f'  {node_id} [label="{resource.name}\\n({resource.type.value})"];')
                
                for resource in resources:
                    node_id = resource.path.replace("/", "_").replace("-", "_")
                    for dep in resource.dependencies:
                        dep_id = dep.replace("/", "_").replace("-", "_")
                        console.print(f"  {dep_id} -> {node_id};")
                
                console.print("}")
                
        except Exception as e:
            console.print(f"[red]Error generating graph: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_dag_graph())


@cli.command()
@click.argument("terragrunt_command")
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.option(
    "--dry-run", 
    is_flag=True, 
    help="Show what would be executed without running"
)
@click.option(
    "--parallelism", 
    type=int, 
    help="Number of parallel executions"
)
@click.pass_context
def run_all(ctx, terragrunt_command: str, environment: Optional[str], dry_run: bool, parallelism: Optional[int]):
    """Run a Terragrunt command across all units (uses 'run --all' internally)."""
    async def _run_all():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print(f"[blue]Running '{terragrunt_command}' across all units{f' in {environment}' if environment else ''}...[/blue]")
            
            if dry_run:
                resources = await manager.discover_resources(environment)
                console.print(f"[yellow]Would execute '{terragrunt_command}' on {len(resources)} units:[/yellow]")
                for resource in resources:
                    console.print(f"  - {resource.name} ({resource.path})")
                return
            
            # Build the command using new CLI structure
            command = ["run", "--all", terragrunt_command]
            if parallelism:
                command.extend(["--terragrunt-parallelism", str(parallelism)])
            
            # Execute the command from the terragrunt root
            from .utils import run_command
            env_vars = manager._prepare_environment()
            
            console.print(f"[blue]Executing: terragrunt {' '.join(command)}[/blue]")
            
            exit_code, stdout, stderr, execution_time = await run_command(
                [manager.binary_path] + command,
                working_dir=manager.root_path,
                timeout=config.terragrunt.timeout * 2,  # Double timeout for run-all
                env_vars=env_vars,
            )
            
            if exit_code == 0:
                console.print(f"[green]✅ Command completed successfully in {execution_time:.2f}s[/green]")
                if stdout:
                    console.print(f"\n[yellow]Output:[/yellow]\n{stdout}")
            else:
                console.print(f"[red]❌ Command failed with exit code {exit_code}[/red]")
                if stderr:
                    console.print(f"\n[red]Error:[/red]\n{stderr}")
                sys.exit(1)
                
        except Exception as e:
            console.print(f"[red]Error running command across all units: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_run_all())


@cli.command()
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.pass_context
def list_stacks(ctx, environment: Optional[str], format: str):
    """List all Terragrunt stacks using experimental features."""
    async def _list_stacks():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            
            if not config.is_experimental_enabled("stacks_enabled"):
                console.print("[red]❌ Stacks experimental feature is disabled[/red]")
                console.print("[yellow]Enable stacks in configuration to use this feature[/yellow]")
                sys.exit(1)
            
            from .stack_manager import StackManager
            manager = StackManager(config)
            
            console.print("[blue]Discovering stacks...[/blue]")
            stacks = await manager.discover_stacks(environment)
            
            if format == "json":
                import json
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
                    })
                console.print(json.dumps(stack_data, indent=2))
            else:
                # Table format
                table = Table(title=f"Terragrunt Stacks {f'({environment})' if environment else ''}")
                table.add_column("Name", style="cyan")
                table.add_column("Status", style="magenta")
                table.add_column("Units", style="green")
                table.add_column("Parallel Groups", style="yellow")
                table.add_column("Dependencies", style="blue")
                
                for stack in stacks:
                    table.add_row(
                        stack.name,
                        stack.status.value,
                        str(len(stack.units)),
                        str(len(stack.execution_order)),
                        str(len(stack.dependencies))
                    )
                
                console.print(table)
                console.print(f"\n[green]Found {len(stacks)} stacks[/green]")
                
        except Exception as e:
            console.print(f"[red]Error listing stacks: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_list_stacks())


@cli.command()
@click.argument("stack_path")
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.pass_context
def get_stack_details(ctx, stack_path: str, format: str):
    """Get detailed information about a specific stack."""
    async def _get_stack_details():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            
            if not config.is_experimental_enabled("stacks_enabled"):
                console.print("[red]❌ Stacks experimental feature is disabled[/red]")
                sys.exit(1)
            
            from .stack_manager import StackManager
            manager = StackManager(config)
            
            console.print(f"[blue]Getting stack details for: {stack_path}[/blue]")
            
            # Find the stack
            stacks = await manager.discover_stacks()
            matching_stack = None
            
            for stack in stacks:
                if stack.path == stack_path or stack.name == stack_path:
                    matching_stack = stack
                    break
            
            if not matching_stack:
                console.print(f"[red]Stack not found: {stack_path}[/red]")
                console.print("[yellow]Available stacks:[/yellow]")
                for stack in stacks[:10]:
                    console.print(f"  - {stack.path} ({stack.name})")
                if len(stacks) > 10:
                    console.print(f"  ... and {len(stacks) - 10} more")
                sys.exit(1)
            
            if format == "json":
                import json
                stack_data = {
                    "name": matching_stack.name,
                    "path": matching_stack.path,
                    "status": matching_stack.status.value,
                    "unit_count": len(matching_stack.units),
                    "parallel_groups": len(matching_stack.execution_order),
                    "units": [
                        {
                            "name": unit.name,
                            "path": unit.path,
                            "type": unit.type.value,
                            "status": unit.status.value,
                            "dependencies": unit.dependencies,
                        }
                        for unit in matching_stack.units
                    ],
                    "execution_order": matching_stack.execution_order,
                    "dependencies": matching_stack.dependencies,
                    "metadata": matching_stack.metadata,
                }
                console.print(json.dumps(stack_data, indent=2))
            else:
                # Table format
                table = Table(title=f"Stack Details: {matching_stack.name}")
                table.add_column("Attribute", style="cyan", width=20)
                table.add_column("Value", style="white", width=60)
                
                table.add_row("Name", matching_stack.name)
                table.add_row("Path", matching_stack.path)
                table.add_row("Status", matching_stack.status.value)
                table.add_row("Unit Count", str(len(matching_stack.units)))
                table.add_row("Parallel Groups", str(len(matching_stack.execution_order)))
                table.add_row("Dependencies", str(len(matching_stack.dependencies)))
                
                if matching_stack.created_at:
                    table.add_row("Created", matching_stack.created_at.strftime("%Y-%m-%d %H:%M:%S"))
                
                console.print(table)
                
                # Show units
                if matching_stack.units:
                    console.print(f"\n[yellow]Units ({len(matching_stack.units)}):[/yellow]")
                    units_table = Table()
                    units_table.add_column("Name", style="cyan")
                    units_table.add_column("Type", style="magenta")
                    units_table.add_column("Status", style="green")
                    units_table.add_column("Dependencies", style="yellow")
                    
                    for unit in matching_stack.units:
                        units_table.add_row(
                            unit.name,
                            unit.type.value,
                            unit.status.value,
                            str(len(unit.dependencies))
                        )
                    
                    console.print(units_table)
                
                # Show execution order
                if matching_stack.execution_order:
                    console.print(f"\n[yellow]Execution Order ({len(matching_stack.execution_order)} groups):[/yellow]")
                    for i, group in enumerate(matching_stack.execution_order, 1):
                        console.print(f"  Group {i}: {', '.join(group)}")
                
        except Exception as e:
            console.print(f"[red]Error getting stack details: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_get_stack_details())


@cli.command()
@click.argument("stack_path")
@click.argument("command")
@click.option(
    "--dry-run", 
    is_flag=True, 
    help="Run in dry-run mode"
)
@click.pass_context
def execute_stack_command(ctx, stack_path: str, command: str, dry_run: bool):
    """Execute a command on a stack using experimental features."""
    async def _execute_stack_command():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            
            if not config.is_experimental_enabled("stacks_enabled"):
                console.print("[red]❌ Stacks experimental feature is disabled[/red]")
                sys.exit(1)
            
            from .stack_manager import StackManager
            manager = StackManager(config)
            
            console.print(f"[blue]Executing '{command}' on stack: {stack_path}[/blue]")
            if dry_run:
                console.print("[yellow]Running in dry-run mode[/yellow]")
            
            # Execute the command
            execution = await manager.execute_stack_command(stack_path, command, dry_run)
            
            # Display results
            console.print(f"\n[cyan]Execution ID:[/cyan] {execution.id}")
            console.print(f"[cyan]Status:[/cyan] {execution.status.value}")
            console.print(f"[cyan]Started:[/cyan] {execution.started_at}")
            console.print(f"[cyan]Completed:[/cyan] {execution.completed_at}")
            
            if execution.unit_results:
                console.print(f"\n[yellow]Unit Results ({len(execution.unit_results)}):[/yellow]")
                for unit_path, result in execution.unit_results.items():
                    status_color = "green" if result["status"] == "completed" else "red"
                    console.print(f"  [{status_color}]{unit_path}[/{status_color}]: {result['status']}")
                    
                    if result.get("errors"):
                        for error in result["errors"]:
                            console.print(f"    [red]Error: {error}[/red]")
            
            if execution.status.value == "failed":
                console.print(f"\n[red]❌ Execution failed[/red]")
                if execution.error_message:
                    console.print(f"[red]Error: {execution.error_message}[/red]")
                sys.exit(1)
            else:
                console.print(f"\n[green]✅ Execution completed successfully[/green]")
                
        except Exception as e:
            console.print(f"[red]Error executing stack command: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_execute_stack_command())


@cli.command()
@click.argument("stack_path")
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.pass_context
def get_stack_outputs(ctx, stack_path: str, format: str):
    """Get outputs from a stack using experimental features."""
    async def _get_stack_outputs():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            
            if not config.is_experimental_enabled("stack_outputs"):
                console.print("[red]❌ Stack outputs experimental feature is disabled[/red]")
                sys.exit(1)
            
            from .stack_manager import StackManager
            manager = StackManager(config)
            
            console.print(f"[blue]Getting outputs for stack: {stack_path}[/blue]")
            
            outputs = await manager.get_stack_outputs(stack_path)
            
            if format == "json":
                import json
                console.print(json.dumps(outputs, indent=2))
            else:
                # Table format
                table = Table(title=f"Stack Outputs: {stack_path}")
                table.add_column("Output Name", style="cyan")
                table.add_column("Value", style="white")
                
                for key, value in outputs.items():
                    # Truncate long values
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:97] + "..."
                    table.add_row(key, value_str)
                
                console.print(table)
                console.print(f"\n[green]Found {len(outputs)} outputs[/green]")
                
        except Exception as e:
            console.print(f"[red]Error getting stack outputs: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_get_stack_outputs())


@cli.command()
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["tree", "dag", "json"]), 
    default="tree", 
    help="Output format"
)
@click.option(
    "--include-dependencies", 
    is_flag=True, 
    default=True,
    help="Include dependency information"
)
@click.option(
    "--max-depth", 
    type=int, 
    help="Maximum depth to display"
)
@click.pass_context
def draw_tree(ctx, environment: Optional[str], format: str, include_dependencies: bool, max_depth: Optional[int]):
    """Draw a visual resource tree using Terragrunt CLI redesign commands."""
    async def _draw_tree():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print(f"[blue]Drawing resource tree{f' for {environment}' if environment else ''}...[/blue]")
            
            # Generate the resource tree
            tree_result = await manager.draw_resource_tree(
                environment=environment,
                format=format,
                include_dependencies=include_dependencies,
                max_depth=max_depth
            )
            
            if format == "json":
                import json
                console.print(json.dumps(tree_result, indent=2))
            else:
                # Display the visual tree
                console.print(f"\n[yellow]Resource Tree ({tree_result['format']} format):[/yellow]")
                if tree_result["environment_filter"]:
                    console.print(f"[cyan]Environment: {tree_result['environment_filter']}[/cyan]")
                console.print(f"[cyan]Total Resources: {tree_result['total_resources']}[/cyan]")
                if include_dependencies:
                    console.print("[cyan]Dependencies: Included[/cyan]")
                if max_depth:
                    console.print(f"[cyan]Max Depth: {max_depth}[/cyan]")
                
                console.print()
                
                # Print the visual representation
                visual_lines = tree_result["visual_representation"]
                for line in visual_lines:
                    console.print(line)
                
                console.print(f"\n[green]✅ Tree generated successfully[/green]")
                
        except Exception as e:
            console.print(f"[red]Error drawing resource tree: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_draw_tree())


@cli.command()
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["dot", "json", "mermaid"]), 
    default="dot", 
    help="Output format"
)
@click.pass_context
def dependency_graph(ctx, environment: Optional[str], format: str):
    """Generate dependency graph using Terragrunt CLI redesign commands."""
    async def _dependency_graph():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print(f"[blue]Generating dependency graph{f' for {environment}' if environment else ''}...[/blue]")
            
            # Generate the dependency graph
            graph_result = await manager.get_dependency_graph(
                environment=environment,
                output_format=format
            )
            
            if format == "json":
                import json
                console.print(json.dumps(graph_result, indent=2))
            elif format == "dot":
                console.print(f"\n[yellow]Dependency Graph (DOT format):[/yellow]")
                if graph_result["environment_filter"]:
                    console.print(f"[cyan]Environment: {graph_result['environment_filter']}[/cyan]")
                console.print()
                
                dot_content = graph_result["graph_data"]["dot_content"]
                console.print(dot_content)
                
                console.print(f"\n[green]✅ DOT graph generated successfully[/green]")
                console.print("[blue]You can visualize this with Graphviz:[/blue]")
                console.print("  echo '<dot_content>' | dot -Tpng -o graph.png")
                
            elif format == "mermaid":
                console.print(f"\n[yellow]Dependency Graph (Mermaid format):[/yellow]")
                if graph_result["environment_filter"]:
                    console.print(f"[cyan]Environment: {graph_result['environment_filter']}[/cyan]")
                console.print()
                
                mermaid_content = graph_result["graph_data"]["mermaid_content"]
                console.print(mermaid_content)
                
                console.print(f"\n[green]✅ Mermaid graph generated successfully[/green]")
                console.print("[blue]You can visualize this at: https://mermaid.live[/blue]")
            
            # Show summary
            graph_data = graph_result["graph_data"]
            if "nodes" in graph_data and "edges" in graph_data:
                console.print(f"\n[cyan]Graph Summary:[/cyan]")
                console.print(f"  Nodes: {len(graph_data['nodes'])}")
                console.print(f"  Edges: {len(graph_data['edges'])}")
            
            console.print(f"[blue]Command used: {graph_result['command_used']}[/blue]")
                
        except Exception as e:
            console.print(f"[red]Error generating dependency graph: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_dependency_graph())


@cli.command()
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.option(
    "--type", 
    "-t",
    "visualization_type",
    type=click.Choice(["tree", "dag", "hierarchy"]), 
    default="tree", 
    help="Type of visualization"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["ascii", "dot", "mermaid", "json"]), 
    default="ascii", 
    help="Output format"
)
@click.option(
    "--include-dependencies", 
    is_flag=True, 
    default=True, 
    help="Include dependency information"
)
@click.pass_context
def visualize(ctx, environment: Optional[str], visualization_type: str, format: str, include_dependencies: bool):
    """Comprehensive infrastructure visualization using Terragrunt CLI redesign."""
    async def _visualize():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            manager = TerragruntManager(config)
            
            console.print(f"[blue]Generating {visualization_type} visualization{f' for {environment}' if environment else ''}...[/blue]")
            
            results = {}
            
            if visualization_type in ["tree", "hierarchy"]:
                # Generate tree visualization
                tree_format = "tree" if format == "ascii" else format
                tree_result = await manager.draw_resource_tree(
                    environment=environment,
                    format=tree_format,
                    include_dependencies=include_dependencies,
                    max_depth=None
                )
                results["tree"] = tree_result
            
            if visualization_type in ["dag", "dependencies"] or include_dependencies:
                # Generate dependency graph
                graph_format = "dot" if format == "ascii" else format
                graph_result = await manager.get_dependency_graph(
                    environment=environment,
                    output_format=graph_format
                )
                results["dependency_graph"] = graph_result
            
            if format == "json":
                import json
                console.print(json.dumps(results, indent=2))
            else:
                # Display results
                console.print(f"\n[yellow]Infrastructure Visualization ({visualization_type}):[/yellow]")
                if environment:
                    console.print(f"[cyan]Environment: {environment}[/cyan]")
                console.print(f"[cyan]Format: {format}[/cyan]")
                console.print(f"[cyan]Include Dependencies: {include_dependencies}[/cyan]")
                console.print()
                
                # Show tree if available
                if "tree" in results:
                    console.print("[yellow]📊 Resource Tree:[/yellow]")
                    tree_lines = results["tree"]["visual_representation"]
                    for line in tree_lines:
                        console.print(line)
                    console.print()
                
                # Show dependency graph if available
                if "dependency_graph" in results:
                    console.print("[yellow]🔗 Dependency Graph:[/yellow]")
                    graph_data = results["dependency_graph"]["graph_data"]
                    
                    if format == "ascii" and "dot_content" in graph_data:
                        # Show simplified dependency list for ASCII
                        if "edges" in graph_data:
                            for source, target in graph_data["edges"]:
                                console.print(f"  {source} → {target}")
                    elif "dot_content" in graph_data:
                        console.print(graph_data["dot_content"])
                    elif "mermaid_content" in graph_data:
                        console.print(graph_data["mermaid_content"])
                
                console.print(f"\n[green]✅ Visualization generated successfully[/green]")
                
        except Exception as e:
            console.print(f"[red]Error generating visualization: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_visualize())


@cli.command()
@click.option(
    "--variant", 
    "-v",
    type=click.Choice(["compact", "extended", "cli"]), 
    default="compact", 
    help="System prompt variant"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["text", "json", "context"]), 
    default="text", 
    help="Output format"
)
@click.option(
    "--output-file", 
    "-o", 
    type=click.Path(), 
    help="Save prompt to file"
)
@click.pass_context
def get_autodevops_prompt(ctx, variant: str, format: str, output_file: Optional[str]):
    """Get AutoDevOps system prompt for LLM integration."""
    try:
        from .autodevops_prompt import get_system_prompt, create_autodevops_context
        
        if format == "context":
            # Return full context information
            context = create_autodevops_context()
            context["system_prompt"] = get_system_prompt(variant)
            
            if format == "json":
                import json
                output = json.dumps(context, indent=2)
            else:
                output = f"""AutoDevOps Assistant Context:
Role: {context['role']}

Capabilities:
{chr(10).join(f"- {cap}" for cap in context['capabilities'])}

Available Tools:
{chr(10).join(f"- {tool}" for tool in context['tools'])}

Safety Principles:
{chr(10).join(f"- {principle}" for principle in context['safety_principles'])}

System Prompt ({variant}):
{context['system_prompt']}"""
        
        elif format == "json":
            import json
            data = {
                "system_prompt": get_system_prompt(variant),
                "variant": variant,
                "role": "system",
                "purpose": "AutoDevOps Infrastructure Assistant",
                "integration_guide": {
                    "claude_desktop": "Add this prompt to your Claude Desktop configuration",
                    "api": "Include as system message in API calls",
                    "cli": "Use with --system-prompt flag in CLI tools"
                },
                "character_count": len(get_system_prompt(variant)),
                "word_count": len(get_system_prompt(variant).split())
            }
            output = json.dumps(data, indent=2)
        
        else:  # text format
            prompt = get_system_prompt(variant)
            output = prompt
        
        # Output to file or console
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            console.print(f"[green]✅ AutoDevOps {variant} system prompt saved to {output_file}[/green]")
            
            # Show stats
            console.print(f"[cyan]Variant:[/cyan] {variant}")
            console.print(f"[cyan]Format:[/cyan] {format}")
            console.print(f"[cyan]Characters:[/cyan] {len(output)}")
            console.print(f"[cyan]Words:[/cyan] {len(output.split())}")
        else:
            console.print(output)
            
        # Show integration tips
        if not output_file:
            console.print(f"\n[yellow]💡 Integration Tips:[/yellow]")
            console.print(f"[blue]• Claude Desktop:[/blue] Add as system message in MCP configuration")
            console.print(f"[blue]• API Integration:[/blue] Use as 'system' role in conversation history")
            console.print(f"[blue]• Save to file:[/blue] --output-file prompt.txt")
            console.print(f"[blue]• Get JSON format:[/blue] --format json")
            
    except Exception as e:
        console.print(f"[red]Error getting AutoDevOps prompt: {e}[/red]")
        sys.exit(1)

    asyncio.run(_get_autodevops_prompt())


# Cost Management Commands
@cli.command()
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.option(
    "--period-days", 
    "-p", 
    type=int, 
    default=30, 
    help="Analysis period in days (default: 30)"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.option(
    "--include-forecasting/--no-forecasting", 
    default=True, 
    help="Include cost forecasting"
)
@click.option(
    "--include-recommendations/--no-recommendations", 
    default=True, 
    help="Include optimization recommendations"
)
@click.pass_context
def cost_analysis(ctx, environment: Optional[str], period_days: int, format: str, 
                 include_forecasting: bool, include_recommendations: bool):
    """Get comprehensive cost analysis for infrastructure."""
    async def _cost_analysis():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            
            cost_manager = CostManager(config)
            
            console.print(f"[blue]📊 Analyzing costs for {environment or 'all environments'} ({period_days} days)...[/blue]")
            
            cost_analysis = await cost_manager.get_cost_analysis(
                environment=environment,
                period_days=period_days,
                include_forecasting=include_forecasting,
                include_recommendations=include_recommendations
            )
            
            if format == "json":
                import json
                output = {
                    "total_cost": cost_analysis.total_cost,
                    "currency": cost_analysis.currency,
                    "period": cost_analysis.period,
                    "breakdown_by_service": cost_analysis.breakdown_by_service,
                    "breakdown_by_environment": cost_analysis.breakdown_by_environment,
                    "breakdown_by_resource": cost_analysis.breakdown_by_resource,
                    "trends": cost_analysis.trends,
                    "forecast": cost_analysis.forecast,
                    "recommendations": cost_analysis.recommendations,
                    "last_updated": cost_analysis.last_updated.isoformat()
                }
                console.print(json.dumps(output, indent=2))
            else:
                # Table format
                console.print(f"\n[bold green]💰 Cost Analysis Summary[/bold green]")
                console.print(f"Total Cost: [bold]${cost_analysis.total_cost:.2f} {cost_analysis.currency}[/bold]")
                console.print(f"Period: {cost_analysis.period}")
                
                if cost_analysis.breakdown_by_service:
                    console.print(f"\n[bold]📋 Service Breakdown:[/bold]")
                    service_table = Table(show_header=True, header_style="bold magenta")
                    service_table.add_column("Service", style="cyan")
                    service_table.add_column("Cost", justify="right", style="green")
                    service_table.add_column("Percentage", justify="right", style="yellow")
                    
                    for service, cost in sorted(cost_analysis.breakdown_by_service.items(), key=lambda x: x[1], reverse=True):
                        percentage = (cost / cost_analysis.total_cost * 100) if cost_analysis.total_cost > 0 else 0
                        service_table.add_row(service, f"${cost:.2f}", f"{percentage:.1f}%")
                    
                    console.print(service_table)
                
                if cost_analysis.breakdown_by_environment:
                    console.print(f"\n[bold]🌍 Environment Breakdown:[/bold]")
                    env_table = Table(show_header=True, header_style="bold magenta")
                    env_table.add_column("Environment", style="cyan")
                    env_table.add_column("Cost", justify="right", style="green")
                    env_table.add_column("Percentage", justify="right", style="yellow")
                    
                    for env, cost in sorted(cost_analysis.breakdown_by_environment.items(), key=lambda x: x[1], reverse=True):
                        percentage = (cost / cost_analysis.total_cost * 100) if cost_analysis.total_cost > 0 else 0
                        env_table.add_row(env, f"${cost:.2f}", f"{percentage:.1f}%")
                    
                    console.print(env_table)
                
                if cost_analysis.forecast and include_forecasting:
                    console.print(f"\n[bold]🔮 Cost Forecast:[/bold]")
                    forecast = cost_analysis.forecast
                    console.print(f"Next 30 days: [bold]${forecast.get('next_30_days', 0):.2f}[/bold]")
                    console.print(f"Next 90 days: [bold]${forecast.get('next_90_days', 0):.2f}[/bold]")
                    console.print(f"Monthly estimate: [bold]${forecast.get('monthly_estimate', 0):.2f}[/bold]")
                    console.print(f"Daily growth rate: [bold]${forecast.get('daily_growth_rate', 0):.2f}[/bold]")
                
                if cost_analysis.recommendations and include_recommendations:
                    console.print(f"\n[bold]💡 Optimization Recommendations:[/bold]")
                    for i, rec in enumerate(cost_analysis.recommendations, 1):
                        priority_color = "red" if rec.get("priority") == "high" else "yellow" if rec.get("priority") == "medium" else "green"
                        console.print(f"{i}. [{priority_color}]{rec.get('title', 'Unknown')}[/{priority_color}]")
                        console.print(f"   Priority: {rec.get('priority', 'unknown').upper()}")
                        console.print(f"   Potential Savings: ${rec.get('potential_savings', 0):.2f}")
                        console.print(f"   Action: {rec.get('action', 'No action specified')}")
                        console.print()
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            sys.exit(1)

    asyncio.run(_cost_analysis())


@cli.command()
@click.option(
    "--threshold", 
    "-t", 
    type=float, 
    default=80.0, 
    help="Budget threshold percentage for alerts (default: 80.0)"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.pass_context
def cost_alerts(ctx, threshold: float, format: str):
    """Get cost alerts based on budget thresholds and spending patterns."""
    async def _cost_alerts():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            
            cost_manager = CostManager(config)
            
            console.print(f"[blue]🚨 Checking cost alerts (threshold: {threshold}%)...[/blue]")
            
            alerts = await cost_manager.get_cost_alerts(threshold)
            
            if format == "json":
                import json
                console.print(json.dumps(alerts, indent=2))
            else:
                if not alerts:
                    console.print("[green]✅ No cost alerts found[/green]")
                    return
                
                console.print(f"\n[bold red]🚨 Found {len(alerts)} Cost Alerts[/bold red]")
                
                for i, alert in enumerate(alerts, 1):
                    severity_color = "red" if alert.get("severity") == "high" else "yellow" if alert.get("severity") == "medium" else "green"
                    console.print(f"\n{i}. [{severity_color}]{alert.get('type', 'Unknown').replace('_', ' ').title()}[/{severity_color}]")
                    console.print(f"   Severity: {alert.get('severity', 'unknown').upper()}")
                    console.print(f"   Message: {alert.get('message', 'No message')}")
                    
                    if 'current_cost' in alert:
                        console.print(f"   Current Cost: ${alert['current_cost']:.2f}")
                    if 'budget' in alert:
                        console.print(f"   Budget: ${alert['budget']:.2f}")
                    if 'recommendation' in alert:
                        console.print(f"   Recommendation: {alert['recommendation']}")
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            sys.exit(1)

    asyncio.run(_cost_alerts())


@cli.command()
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.pass_context
def cost_optimization_score(ctx, format: str):
    """Get cost optimization score for the infrastructure."""
    async def _cost_optimization_score():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            
            cost_manager = CostManager(config)
            
            console.print("[blue]📈 Calculating cost optimization score...[/blue]")
            
            score_data = await cost_manager.get_cost_optimization_score()
            
            if format == "json":
                import json
                console.print(json.dumps(score_data, indent=2))
            else:
                score = score_data.get("score", 0)
                grade = score_data.get("grade", "F")
                
                grade_color = "green" if grade in ["A", "B"] else "yellow" if grade == "C" else "red"
                
                console.print(f"\n[bold {grade_color}]🎯 Cost Optimization Score: {grade} ({score:.1f}/100)[/bold {grade_color}]")
                
                status = "excellent" if score >= 90 else "good" if score >= 80 else "fair" if score >= 70 else "poor"
                console.print(f"Status: {status.title()}")
                
                if "factors" in score_data:
                    console.print(f"\n[bold]📊 Optimization Factors:[/bold]")
                    factors_table = Table(show_header=True, header_style="bold magenta")
                    factors_table.add_column("Factor", style="cyan")
                    factors_table.add_column("Score", justify="right", style="green")
                    factors_table.add_column("Status", justify="center")
                    
                    for factor, factor_score in score_data["factors"].items():
                        factor_name = factor.replace("_", " ").title()
                        factor_status = "✅" if factor_score >= 80 else "⚠️" if factor_score >= 60 else "❌"
                        factors_table.add_row(factor_name, f"{factor_score:.1f}", factor_status)
                    
                    console.print(factors_table)
                
                if score < 80:
                    console.print(f"\n[yellow]💡 Consider running 'cost-analysis --include-recommendations' for optimization suggestions[/yellow]")
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            sys.exit(1)

    asyncio.run(_cost_optimization_score())


@cli.command()
@click.option(
    "--environment", 
    "-e", 
    help="Filter by environment"
)
@click.option(
    "--format", 
    "-f", 
    type=click.Choice(["table", "json"]), 
    default="table", 
    help="Output format"
)
@click.option(
    "--include-alerts/--no-alerts", 
    default=True, 
    help="Include cost alerts"
)
@click.option(
    "--include-optimization/--no-optimization", 
    default=True, 
    help="Include optimization score"
)
@click.pass_context
def cost_status(ctx, environment: Optional[str], format: str, include_alerts: bool, include_optimization: bool):
    """Get comprehensive cost status including analysis, alerts, and optimization score."""
    async def _cost_status():
        try:
            config_path = ctx.obj.get("config_path")
            if config_path:
                config = Config.load_from_file(config_path)
            else:
                config = Config.load_from_file()
            
            cost_manager = CostManager(config)
            
            console.print(f"[blue]💰 Getting comprehensive cost status for {environment or 'all environments'}...[/blue]")
            
            # Get cost analysis
            cost_analysis = await cost_manager.get_cost_analysis(
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
                "trends": cost_analysis.trends[-7:] if cost_analysis.trends else [],
                "forecast": cost_analysis.forecast,
                "recommendations": cost_analysis.recommendations
            }
            
            # Add alerts if requested
            if include_alerts:
                alerts = await cost_manager.get_cost_alerts()
                status_data["alerts"] = {
                    "total_count": len(alerts),
                    "alerts": alerts,
                    "has_critical_alerts": any(alert.get("severity") == "high" for alert in alerts)
                }
            
            # Add optimization score if requested
            if include_optimization:
                optimization_score = await cost_manager.get_cost_optimization_score()
                status_data["optimization"] = optimization_score
            
            # Determine overall status
            overall_status = "healthy"
            if include_alerts and status_data.get("alerts", {}).get("has_critical_alerts"):
                overall_status = "critical"
            elif include_optimization and optimization_score.get("score", 100) < 70:
                overall_status = "needs_attention"
            elif cost_analysis.total_cost == 0:
                overall_status = "no_data"
            
            if format == "json":
                import json
                output = {
                    "overall_status": overall_status,
                    "cost_status": status_data
                }
                console.print(json.dumps(output, indent=2))
            else:
                # Determine status color
                status_color = "green" if overall_status == "healthy" else "red" if overall_status == "critical" else "yellow"
                
                console.print(f"\n[bold {status_color}]💰 Overall Cost Status: {overall_status.replace('_', ' ').title()}[/bold {status_color}]")
                console.print(f"Total Cost: [bold]${cost_analysis.total_cost:.2f} {cost_analysis.currency}[/bold]")
                console.print(f"Period: {cost_analysis.period}")
                
                # Top services
                if cost_analysis.breakdown_by_service:
                    top_service = max(cost_analysis.breakdown_by_service.items(), key=lambda x: x[1])
                    console.print(f"Top Service: {top_service[0]} (${top_service[1]:.2f})")
                
                # Alerts summary
                if include_alerts and status_data.get("alerts"):
                    alerts_info = status_data["alerts"]
                    alert_color = "red" if alerts_info["has_critical_alerts"] else "yellow" if alerts_info["total_count"] > 0 else "green"
                    console.print(f"Alerts: [{alert_color}]{alerts_info['total_count']} alerts[/{alert_color}]")
                
                # Optimization score
                if include_optimization and "optimization" in status_data:
                    opt_score = status_data["optimization"]
                    grade_color = "green" if opt_score["grade"] in ["A", "B"] else "yellow" if opt_score["grade"] == "C" else "red"
                    console.print(f"Optimization Score: [{grade_color}]{opt_score['grade']} ({opt_score['score']:.1f}/100)[/{grade_color}]")
                
                # Recommendations count
                rec_count = len(cost_analysis.recommendations)
                if rec_count > 0:
                    console.print(f"Recommendations: [yellow]{rec_count} optimization opportunities[/yellow]")
                else:
                    console.print("Recommendations: [green]No immediate optimizations needed[/green]")
                
                # Quick actions
                console.print(f"\n[bold]🔧 Quick Actions:[/bold]")
                if rec_count > 0:
                    console.print("• Run 'cost-analysis --include-recommendations' for detailed optimization suggestions")
                if include_alerts and status_data.get("alerts", {}).get("total_count", 0) > 0:
                    console.print("• Run 'cost-alerts' to see detailed alert information")
                if include_optimization and optimization_score.get("score", 100) < 80:
                    console.print("• Run 'cost-optimization-score' for detailed optimization factors")
                
                console.print(f"• Use '--environment <env>' to filter by specific environment")
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            sys.exit(1)

    asyncio.run(_cost_status())


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main() 