# Changelog

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