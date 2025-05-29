# Migration Guide: Terragrunt CLI Redesign

This guide helps you migrate from the legacy Terragrunt CLI to the new CLI redesign supported in version 0.2.0 of the Terragrunt GCP MCP Tool.

## Overview

The Terragrunt CLI Redesign introduces significant changes to command structure and environment variables. This tool has been updated to fully support the new CLI while maintaining backward compatibility where possible.

## Key Changes

### 1. Command Structure

**Before (Legacy CLI):**
```bash
terragrunt plan
terragrunt apply
terragrunt destroy
terragrunt validate
```

**After (CLI Redesign):**
```bash
terragrunt run plan
terragrunt run apply  
terragrunt run destroy
terragrunt run validate
```

### 2. Environment Variables

**Before:**
```bash
export TERRAGRUNT_NON_INTERACTIVE=true
export TERRAGRUNT_DEBUG=true
```

**After:**
```bash
export TG_NON_INTERACTIVE=true
export TG_INPUTS_DEBUG=true
```

### 3. Backend Bootstrap

**Before:**
Backend resources were automatically provisioned without explicit configuration.

**After:**
Use the `--backend-bootstrap` flag or set `TG_BACKEND_BOOTSTRAP=true`:
```bash
terragrunt run plan --backend-bootstrap
```

## Configuration Updates

### Update your `config.yaml`

Add the new CLI redesign settings to your configuration:

```yaml
terragrunt:
  # Existing settings
  root_path: "../terragrunt-gcp-org-automation"
  binary_path: "terragrunt"
  terraform_binary: "tofu"
  
  # New CLI redesign settings
  backend_bootstrap: true     # Enable automatic backend provisioning
  non_interactive: true       # Run in non-interactive mode
  use_run_command: true       # Use 'run' command prefix
  max_retries: 3              # Retry failed operations
  retry_delay: 5              # Delay between retries
```

## New CLI Commands

The tool now includes new commands that align with the CLI redesign:

### 1. Find Command (replaces `output-module-groups`)

**Before:**
```bash
terragrunt output-module-groups
```

**After:**
```bash
python3 -m terragrunt_gcp_mcp.cli find --dag --json --dependencies
```

### 2. List Units (replaces `graph-dependencies`)

**Before:**
```bash
terragrunt graph-dependencies
```

**After:**
```bash
python3 -m terragrunt_gcp_mcp.cli list-units --dag --tree
```

### 3. DAG Graph

**New command for dependency visualization:**
```bash
python3 -m terragrunt_gcp_mcp.cli dag-graph --format json
python3 -m terragrunt_gcp_mcp.cli dag-graph --format dot
```

### 4. Run All (replaces `run-all`)

**Before:**
```bash
terragrunt run-all plan
```

**After:**
```bash
python3 -m terragrunt_gcp_mcp.cli run-all plan
# Or directly with terragrunt:
terragrunt run --all plan
```

## MCP Tool Updates

All MCP tools have been updated to use the new CLI structure:

### Validation
- Now uses `terragrunt run validate`
- Includes `--backend-bootstrap` flag
- Uses `TG_NON_INTERACTIVE=true`

### Planning
- Now uses `terragrunt run plan --backend-bootstrap`
- Enhanced error handling
- Better dependency checking

### Deployment
- Now uses `terragrunt run apply --backend-bootstrap`
- Improved safety checks
- Automatic backend provisioning

## Environment Variables Reference

| Legacy Variable | New Variable | Purpose |
|----------------|--------------|---------|
| `TERRAGRUNT_NON_INTERACTIVE` | `TG_NON_INTERACTIVE` | Non-interactive mode |
| `TERRAGRUNT_DEBUG` | `TG_INPUTS_DEBUG` | Debug inputs |
| N/A | `TG_BACKEND_BOOTSTRAP` | Backend provisioning |
| N/A | `TG_PARALLELISM` | Parallel execution |

## Backward Compatibility

The tool maintains backward compatibility by:

1. **Automatic Command Translation**: Old command patterns are automatically converted to new `run` commands
2. **Environment Variable Mapping**: Legacy environment variables are mapped to new `TG_` prefixed ones
3. **Configuration Migration**: Old configuration files continue to work with sensible defaults

## Testing Your Migration

1. **Update Configuration**:
   ```bash
   # Update your config.yaml with new settings
   cp config/config.example.yaml config/config.yaml
   # Edit with your specific settings
   ```

2. **Test Resource Discovery**:
   ```bash
   python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml list-resources
   ```

3. **Test New Commands**:
   ```bash
   # Test find command
   python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml find --json
   
   # Test dependency visualization
   python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml list-units --tree
   ```

4. **Test Validation**:
   ```bash
   python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml validate-resource "your-resource"
   ```

## Troubleshooting

### Common Issues

1. **Command Not Found**:
   - Ensure you're using Terragrunt v1.0+ with CLI redesign support
   - Check that `terragrunt run --help` works

2. **Backend Bootstrap Errors**:
   - Verify GCP credentials are properly configured
   - Ensure the service account has necessary permissions
   - Check that `TG_BACKEND_BOOTSTRAP=true` is set

3. **Environment Variable Issues**:
   - Update scripts to use `TG_` prefixed variables
   - Check that old `TERRAGRUNT_` variables are removed

### Getting Help

1. **Check Logs**:
   ```bash
   # Enable debug logging
   export TG_INPUTS_DEBUG=true
   python3 -m terragrunt_gcp_mcp.cli --verbose --config config/config.yaml list-resources
   ```

2. **Validate Configuration**:
   ```bash
   python3 test_server.py
   ```

3. **Test MCP Server**:
   ```bash
   python3 test_startup.py
   ```

## Benefits of Migration

After migrating to the CLI redesign, you'll benefit from:

1. **Improved Performance**: Better caching and parallel execution
2. **Enhanced Safety**: Explicit backend bootstrap and validation
3. **Better Debugging**: Improved error messages and logging
4. **Future Compatibility**: Alignment with Terragrunt's roadmap
5. **New Features**: Access to advanced dependency analysis and visualization

## Next Steps

1. Update your configuration files
2. Test the new commands in a development environment
3. Update any automation scripts to use new environment variables
4. Train your team on the new command structure
5. Gradually migrate production workflows

For more information, see the [Terragrunt CLI Redesign documentation](https://terragrunt.gruntwork.io/docs/migrate/cli-redesign/). 