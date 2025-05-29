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


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main() 