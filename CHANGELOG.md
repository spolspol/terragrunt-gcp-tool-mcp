# Changelog

## [0.2.0] - 2025-05-29

### Added
- **Terragrunt CLI Redesign Support**: Complete refactoring to support the new Terragrunt CLI redesign
  - Updated all commands to use `run` prefix (e.g., `terragrunt run plan`, `terragrunt run apply`)
  - Added support for new `TG_` prefixed environment variables (replaces `TERRAGRUNT_` prefix)
  - Implemented `--backend-bootstrap` flag for automatic backend resource provisioning
  - Added `TG_NON_INTERACTIVE=true` for non-interactive operations
  - Added `TG_BACKEND_BOOTSTRAP=true` for automatic backend provisioning

### New CLI Commands
- **`find`**: Discover Terragrunt configurations with dependency information (replaces `output-module-groups`)
  - `--dag`: Show dependency graph information
  - `--json`: Output in JSON format
  - `--dependencies`: Include dependency information
- **`list-units`**: List Terragrunt units with dependency visualization (replaces `graph-dependencies`)
  - `--dag`: Show dependency graph
  - `--tree`: Show tree format visualization
  - `--environment`: Filter by environment
- **`dag-graph`**: Generate dependency graphs in DOT or JSON format
  - `--format`: Choose between 'dot' and 'json' output formats
  - `--environment`: Filter by environment
- **`run-all`**: Execute commands across all units using `run --all` internally
  - `--environment`: Filter by environment
  - `--dry-run`: Show what would be executed
  - `--parallelism`: Control parallel execution

### Enhanced Configuration
- Added new Terragrunt configuration options:
  - `backend_bootstrap`: Enable automatic backend resource provisioning
  - `non_interactive`: Run in non-interactive mode
  - `use_run_command`: Use 'run' command prefix for operations
  - `max_retries`: Maximum retries for failed operations
  - `retry_delay`: Delay between retries

### Updated Commands
- All Terragrunt operations now use the new CLI structure:
  - `validate` → `run validate`
  - `plan` → `run plan --backend-bootstrap`
  - `apply` → `run apply --backend-bootstrap`
  - `destroy` → `run destroy --backend-bootstrap`
  - `init` → `run init --backend-bootstrap`
  - `state list` → `run state list`
  - `state show` → `run state show`

### Migration Notes
- Environment variables updated from `TERRAGRUNT_*` to `TG_*` format
- Backend resources are now automatically provisioned with `--backend-bootstrap` flag
- All commands use the new `run` command structure for better compatibility
- Dependency discovery enhanced with new `find` and `list-units` commands

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
- 8 MCP tools for infrastructure management
- Resource discovery and validation
- Deployment planning and execution
- Infrastructure status monitoring
- Slack notifications (placeholder)
- Comprehensive CLI interface
- Configuration management with YAML
- Integration with existing Terragrunt infrastructure 