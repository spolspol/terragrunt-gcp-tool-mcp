# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2025-05-29

### 🌳 Added - Resource Tree Visualization
- **Tree Drawing Functionality**: New comprehensive resource tree visualization using Terragrunt CLI redesign commands
  - `draw_resource_tree()` method in TerragruntManager for generating visual resource trees
  - `get_dependency_graph()` method for creating dependency graphs in multiple formats
  - Support for ASCII tree, DOT (Graphviz), Mermaid, and JSON output formats
  - Hierarchical visualization with configurable depth limits
  - Dependency information display with counts and relationships

- **New MCP Tools**:
  - `draw_resource_tree` - Generate visual resource trees with filtering and depth control
  - `get_dependency_graph` - Create dependency graphs in DOT, Mermaid, or JSON formats
  - `visualize_infrastructure` - Comprehensive infrastructure visualization combining trees and graphs

- **New CLI Commands**:
  - `draw-tree` - Draw visual resource trees with environment filtering and depth limits
  - `dependency-graph` - Generate dependency graphs with multiple output formats
  - `visualize` - Comprehensive visualization with tree and DAG options

- **Enhanced Features**:
  - Environment filtering for focused visualization
  - Maximum depth control for large infrastructures
  - Multiple output formats (ASCII, DOT, Mermaid, JSON)
  - Dependency relationship visualization
  - Integration with Terragrunt CLI redesign `find` command
  - Automatic resource hierarchy detection

### Technical Implementation
- Leverages Terragrunt CLI redesign `find` command with `--dependencies` and `--dag` flags
- Intelligent parsing of Terragrunt output for resource discovery
- Hierarchical tree building with configurable depth limits
- ASCII art generation for terminal-friendly visualization
- DOT format generation for Graphviz compatibility
- Mermaid format generation for web-based diagram visualization
- JSON output for programmatic consumption

### Usage Examples
```bash
# Basic tree visualization
python3 -m terragrunt_gcp_mcp.cli draw-tree

# Environment-specific tree with depth limit
python3 -m terragrunt_gcp_mcp.cli draw-tree --environment dev-99 --max-depth 4

# Dependency graph in Mermaid format
python3 -m terragrunt_gcp_mcp.cli dependency-graph --format mermaid

# Comprehensive visualization
python3 -m terragrunt_gcp_mcp.cli visualize --type tree --format ascii
```

## [0.3.0] - 2025-05-29

### 🧪 Added - Experimental Features Support
- **Terragrunt Stacks**: Full support for Terragrunt experimental stacks feature
  - Enhanced dependency management and resolution
  - Parallel execution of units within stacks
  - Stack-level operations and outputs
  - Intelligent execution ordering based on dependencies
- **New MCP Tools for Stacks**:
  - `list_stacks` - List all Terragrunt stacks with filtering
  - `get_stack_details` - Get detailed stack information including units and execution order
  - `execute_stack_command` - Execute commands on stacks with parallel execution
  - `get_stack_outputs` - Get aggregated outputs from stack-level operations
  - `get_enhanced_infrastructure_status` - Comprehensive status including stacks
- **New CLI Commands for Stacks**:
  - `list-stacks` - List stacks with environment filtering
  - `get-stack-details` - Get detailed stack information
  - `execute-stack-command` - Execute commands on stacks with dry-run support
  - `get-stack-outputs` - Get stack outputs in table or JSON format
- **Enhanced Configuration**:
  - `experimental` section in configuration for feature toggles
  - Stack-specific settings (timeouts, parallel limits, retry logic)
  - Environment variable support for experimental features
- **Stack Manager**: New component for managing Terragrunt stacks
  - Automatic stack discovery and dependency analysis
  - Parallel execution with configurable limits
  - Enhanced error handling and retry mechanisms
  - Stack-level output aggregation

### Enhanced
- **Configuration System**: Added experimental features configuration section
- **Environment Variables**: Added `TG_STACKS_ENABLED`, `TG_EXPERIMENT_MODE` support
- **Documentation**: Comprehensive documentation for experimental features
- **Testing**: Added experimental features test suite

### Technical Details
- Implemented `StackManager` class for stack operations
- Added new models for stacks, units, and execution tracking
- Enhanced configuration validation for experimental features
- Added stack discovery and dependency resolution algorithms
- Implemented parallel execution with dependency ordering

## [0.2.0] - 2025-05-28

### Added - Terragrunt CLI Redesign Support
- **New Command Structure**: Support for Terragrunt CLI redesign with `run` commands
  - `terragrunt run plan` instead of `terragrunt plan`
  - `terragrunt run apply` instead of `terragrunt apply`
  - `terragrunt run validate` instead of `terragrunt validate`
- **Environment Variables**: Updated to use `TG_` prefixed variables
  - `TG_NON_INTERACTIVE` instead of `TERRAGRUNT_NON_INTERACTIVE`
  - `TG_BACKEND_BOOTSTRAP` for automatic backend provisioning
  - `TG_PARALLELISM` for parallel execution control
- **Backend Bootstrap**: Automatic backend resource provisioning with `--backend-bootstrap`
- **New CLI Commands**:
  - `find` - Replaces `output-module-groups` with `--dag`, `--json`, `--dependencies` options
  - `list-units` - Replaces `graph-dependencies` with `--dag`, `--tree` visualization
  - `dag-graph` - New dependency visualization in DOT/JSON formats
  - `run-all` - Uses `run --all` internally for cross-unit operations

### Enhanced
- **Configuration**: Added new Terragrunt config options
  - `backend_bootstrap`, `non_interactive`, `use_run_command`
  - `max_retries`, `retry_delay` for improved reliability
- **All Operations**: Updated to use new CLI structure
  - Validation: `terragrunt run validate`
  - Planning: `terragrunt run plan --backend-bootstrap`
  - Deployment: `terragrunt run apply --backend-bootstrap`
  - State operations: `terragrunt run state list/show`

### Migration
- **Backward Compatibility**: Maintains support for legacy CLI commands
- **Migration Guide**: Created comprehensive migration documentation
- **Configuration Migration**: Automatic detection and migration of old settings

## [0.1.1] - 2025-05-27

### Fixed
- **AsyncIO Runtime Error**: Fixed "Already running asyncio in this thread" error when starting the MCP server
  - Changed `TerragruntGCPMCPServer.run()` from async to sync method
  - Removed `asyncio.run()` wrapper in main entry point
  - Updated CLI server command to use sync call
  - Server now starts correctly without event loop conflicts

### Changed
- Updated all documentation to use `python3` instead of `python` for consistency
- Updated Claude Desktop configuration examples
- Added `test_startup.py` script for verifying server initialization

### Technical Details
The issue was caused by FastMCP's internal event loop management conflicting with our asyncio.run() wrapper. FastMCP handles its own event loop internally, so we only need to call the synchronous `app.run()` method.

## [0.1.0] - 2025-05-27

### Added
- Initial release of Terragrunt GCP MCP Tool
- **Resource Management**:
  - `list_resources` - List all infrastructure resources
  - `get_resource_details` - Get comprehensive resource information
  - `create_resource` - Create new infrastructure resources
  - `update_resource` - Update existing resource configurations
  - `delete_resource` - Delete resources with dependency checking
- **Deployment Operations**:
  - `validate_resource_config` - Validate Terragrunt configurations
  - `plan_resource_deployment` - Generate deployment plans
  - `apply_resource_deployment` - Apply infrastructure changes
  - `check_deployment_status` - Monitor deployment progress
  - `rollback_deployment` - Rollback failed deployments
- **Monitoring & Analysis**:
  - `get_infrastructure_status` - Overall infrastructure health
  - `analyze_dependencies` - Resource dependency analysis
  - `get_cost_analysis` - Infrastructure cost breakdown
  - `check_drift` - Configuration drift detection
- **Team Collaboration**:
  - `send_slack_notification` - Team notifications
  - `create_deployment_summary` - Deployment reports
  - `get_audit_log` - Operation audit logs

### Features
- **MCP Server**: FastMCP-based server for Claude integration
- **CLI Interface**: Comprehensive command-line interface
- **Configuration Management**: YAML-based configuration system
- **GCP Integration**: Full Google Cloud Platform support
- **Terragrunt Integration**: Native Terragrunt command execution
- **Safety Features**: Dry-run mode, dependency checking, validation
- **Monitoring**: Infrastructure status monitoring and alerting
- **Notifications**: Slack integration for team updates

### Technical
- **Architecture**: Modular design with separate managers for different concerns
- **Error Handling**: Comprehensive error handling and logging
- **Testing**: Test suite for core functionality
- **Documentation**: Complete documentation and examples 