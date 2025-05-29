# 🧪 Experimental Features Documentation

This document provides comprehensive information about the Terragrunt experimental features support in the Terragrunt GCP MCP Tool.

## Overview

The Terragrunt GCP MCP Tool now supports Terragrunt's experimental features as documented in the [Terragrunt Experiments documentation](https://terragrunt.gruntwork.io/docs/reference/experiments/). These features provide enhanced dependency management, parallel execution, and stack-level operations.

## Supported Experimental Features

### 1. Terragrunt Stacks

The **Stacks** experimental feature is the primary focus of this implementation. It provides:

- **Enhanced Dependency Management**: Automatic dependency resolution and execution ordering
- **Parallel Execution**: Run multiple units in parallel within stacks
- **Stack-Level Operations**: Execute commands across entire stacks
- **Improved Error Handling**: Better error reporting and recovery
- **Stack Outputs**: Aggregate outputs at the stack level

#### Key Benefits

1. **Faster Deployments**: Parallel execution of independent units reduces deployment time
2. **Better Dependency Management**: Automatic dependency resolution prevents ordering issues
3. **Improved Reliability**: Enhanced error handling and retry mechanisms
4. **Stack-Level Visibility**: Aggregate status and outputs for better monitoring
5. **Simplified Operations**: Single commands for complex multi-unit deployments

### 2. Enhanced Dependency Resolution

Improved dependency analysis that provides:
- Better detection of circular dependencies
- More accurate dependency ordering
- Enhanced error messages for dependency issues

### 3. Parallel Execution

Configurable parallel execution with:
- Maximum parallel unit limits
- Intelligent scheduling based on dependencies
- Resource-aware execution planning

### 4. Stack Outputs

Stack-level output aggregation that provides:
- Consolidated outputs from all units in a stack
- Cross-unit output references
- Simplified output management

## Configuration

### Basic Configuration

Enable experimental features in your `config.yaml`:

```yaml
terragrunt:
  experimental:
    # Core stacks feature
    stacks_enabled: true                    # Enable Terragrunt stacks experimental feature
    enhanced_dependency_resolution: true    # Use enhanced dependency resolution
    parallel_execution: true                # Enable parallel execution within stacks
    stack_outputs: true                     # Enable stack-level outputs
    
    # Advanced settings
    recursive_stacks: false                 # Enable recursive stacks (not yet stable)
    max_parallel_units: 10                  # Maximum number of units to execute in parallel
    stack_timeout: 7200                     # Timeout for stack operations in seconds (2 hours)
    continue_on_error: false                # Continue stack execution on unit errors
    
    # Retry and reliability
    auto_retry: true                        # Automatically retry failed units
    max_retries: 3                          # Maximum number of retries for failed units
    retry_delay: 30                         # Delay between retries in seconds
```

### Environment Variables

The following environment variables are automatically set when experimental features are enabled:

- `TG_STACKS_ENABLED=true` - Enables stacks feature in Terragrunt
- `TG_EXPERIMENT_MODE=true` - Enables experimental mode
- `TG_NON_INTERACTIVE=true` - Non-interactive mode
- `TG_BACKEND_BOOTSTRAP=true` - Automatic backend provisioning
- `TG_PARALLELISM=<value>` - Parallel execution limit

## Stack Structure

### Directory Layout

Stacks are organized in a hierarchical directory structure:

```
live/
├── dev-account/
│   └── test-dev/
│       └── dev-99/                    # Stack root
│           ├── stack.hcl              # Stack definition (optional)
│           ├── project/
│           │   └── terragrunt.hcl     # Unit 1
│           ├── vpc/
│           │   └── terragrunt.hcl     # Unit 2
│           ├── compute/
│           │   └── terragrunt.hcl     # Unit 3 (depends on vpc)
│           └── secrets/
│               └── terragrunt.hcl     # Unit 4
```

### Stack Definition

While not required, you can define stack-specific configuration in `stack.hcl`:

```hcl
# stack.hcl
stack {
  name = "dev-99-infrastructure"
  description = "Development environment infrastructure"
  
  # Stack-level configuration
  max_parallel_units = 5
  timeout = 3600
  
  # Stack-level variables
  vars = {
    environment = "dev-99"
    region = "europe-west2"
  }
}
```

### Unit Dependencies

Units within a stack can declare dependencies using standard Terragrunt dependency blocks:

```hcl
# compute/terragrunt.hcl
dependency "vpc" {
  config_path = "../vpc"
}

dependency "project" {
  config_path = "../project"
}

inputs = {
  vpc_id = dependency.vpc.outputs.vpc_id
  project_id = dependency.project.outputs.project_id
}
```

## MCP Tools for Stacks

### 1. `list_stacks`

List all Terragrunt stacks with filtering options.

**Parameters:**
- `environment` (optional): Filter by environment
- `format` (optional): Output format ("table" or "json")

**Example:**
```python
result = list_stacks(environment="dev-99", format="table")
```

### 2. `get_stack_details`

Get detailed information about a specific stack including units and execution order.

**Parameters:**
- `stack_path`: Path to the stack
- `format` (optional): Output format ("table" or "json")

**Example:**
```python
result = get_stack_details(
    stack_path="live/dev-account/test-dev/dev-99",
    format="json"
)
```

### 3. `execute_stack_command`

Execute commands on stacks with parallel execution and dependency management.

**Parameters:**
- `stack_path`: Path to the stack
- `command`: Command to execute ("plan", "apply", "validate", etc.)
- `dry_run` (optional): Run in dry-run mode

**Example:**
```python
result = execute_stack_command(
    stack_path="live/dev-account/test-dev/dev-99",
    command="plan",
    dry_run=True
)
```

### 4. `get_stack_outputs`

Get aggregated outputs from stack-level operations.

**Parameters:**
- `stack_path`: Path to the stack
- `format` (optional): Output format ("table" or "json")

**Example:**
```python
result = get_stack_outputs(
    stack_path="live/dev-account/test-dev/dev-99",
    format="json"
)
```

### 5. `get_enhanced_infrastructure_status`

Get comprehensive status including both traditional resources and stacks.

**Parameters:**
- `environment` (optional): Filter by environment
- `include_stacks` (optional): Include stack information
- `include_costs` (optional): Include cost analysis

**Example:**
```python
result = get_enhanced_infrastructure_status(
    environment="dev-99",
    include_stacks=True,
    include_costs=False
)
```

## CLI Commands for Stacks

### 1. `list-stacks`

```bash
# List all stacks
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml list-stacks

# Filter by environment
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml list-stacks --environment dev-99

# JSON output
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml list-stacks --format json
```

### 2. `get-stack-details`

```bash
# Get stack details
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml get-stack-details "live/dev-account/test-dev/dev-99"

# JSON output
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml get-stack-details "dev-99" --format json
```

### 3. `execute-stack-command`

```bash
# Plan a stack (dry-run)
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml execute-stack-command "dev-99" plan --dry-run

# Apply a stack
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml execute-stack-command "dev-99" apply

# Validate a stack
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml execute-stack-command "dev-99" validate --dry-run
```

### 4. `get-stack-outputs`

```bash
# Get stack outputs
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml get-stack-outputs "dev-99"

# JSON output
python3 -m terragrunt_gcp_mcp.cli --config config/config.yaml get-stack-outputs "dev-99" --format json
```

## Execution Flow

### Stack Discovery

1. **Scan Directory Structure**: The stack manager scans the Terragrunt root directory
2. **Identify Stacks**: Directories containing multiple `terragrunt.hcl` files are identified as stacks
3. **Parse Dependencies**: Dependencies between units are analyzed
4. **Create Execution Order**: Units are organized into parallel execution groups

### Parallel Execution

1. **Dependency Analysis**: Units are analyzed for dependencies
2. **Group Creation**: Independent units are grouped for parallel execution
3. **Execution Planning**: Execution order is determined based on dependencies
4. **Parallel Execution**: Units within each group are executed in parallel
5. **Progress Monitoring**: Execution progress is tracked and reported

### Error Handling

1. **Unit Failures**: Failed units are retried based on configuration
2. **Dependency Failures**: Dependent units are skipped if dependencies fail
3. **Stack Failures**: Stack execution can continue or stop based on configuration
4. **Recovery**: Failed stacks can be resumed from the last successful point

## Best Practices

### 1. Stack Organization

- **Logical Grouping**: Group related infrastructure components into stacks
- **Environment Separation**: Use separate stacks for different environments
- **Dependency Management**: Minimize cross-stack dependencies
- **Size Management**: Keep stacks to a reasonable size (5-15 units)

### 2. Configuration

- **Parallel Limits**: Set appropriate parallel execution limits based on resources
- **Timeouts**: Configure reasonable timeouts for stack operations
- **Retry Logic**: Enable auto-retry for transient failures
- **Error Handling**: Configure appropriate error handling behavior

### 3. Monitoring

- **Progress Tracking**: Monitor stack execution progress
- **Error Monitoring**: Track and alert on stack failures
- **Performance Monitoring**: Monitor execution times and resource usage
- **Cost Monitoring**: Track infrastructure costs at the stack level

### 4. Testing

- **Dry-Run Testing**: Always test with dry-run before applying changes
- **Environment Testing**: Test in development environments first
- **Dependency Testing**: Verify dependency resolution works correctly
- **Rollback Testing**: Test rollback procedures for failed deployments

## Troubleshooting

### Common Issues

#### 1. Stack Discovery Issues

**Problem**: Stacks not being discovered
**Solution**: 
- Verify directory structure contains `terragrunt.hcl` files
- Check that experimental features are enabled
- Verify Terragrunt root path is correct

#### 2. Dependency Resolution Issues

**Problem**: Circular dependencies or incorrect ordering
**Solution**:
- Review dependency declarations in `terragrunt.hcl` files
- Use dependency visualization tools
- Simplify dependency structure

#### 3. Parallel Execution Issues

**Problem**: Units failing in parallel execution
**Solution**:
- Reduce parallel execution limits
- Check for resource conflicts
- Review unit dependencies

#### 4. Timeout Issues

**Problem**: Stack operations timing out
**Solution**:
- Increase stack timeout configuration
- Optimize unit execution time
- Review resource provisioning time

### Debugging

#### Enable Debug Logging

```yaml
logging:
  level: "DEBUG"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

#### Stack Execution Debugging

```bash
# Enable debug mode for stack execution
TG_LOG_LEVEL=debug python3 -m terragrunt_gcp_mcp.cli execute-stack-command "dev-99" plan --dry-run
```

#### Dependency Analysis

```bash
# Analyze stack dependencies
python3 -m terragrunt_gcp_mcp.cli get-stack-details "dev-99" --format json | jq '.execution_order'
```

## Migration from Traditional Resources

### 1. Assessment

- **Identify Groupings**: Identify logical groupings of existing resources
- **Analyze Dependencies**: Map existing dependencies between resources
- **Plan Migration**: Create migration plan for converting to stacks

### 2. Conversion

- **Create Stack Structure**: Organize resources into stack directories
- **Update Dependencies**: Convert resource dependencies to stack dependencies
- **Test Migration**: Test stack operations in development environment

### 3. Validation

- **Verify Functionality**: Ensure all operations work with stacks
- **Performance Testing**: Verify performance improvements with parallel execution
- **Rollback Planning**: Ensure rollback procedures are in place

## Performance Considerations

### 1. Parallel Execution

- **Resource Limits**: Consider GCP API rate limits and quotas
- **Network Bandwidth**: Consider network bandwidth for large deployments
- **Local Resources**: Consider local CPU and memory usage

### 2. Stack Size

- **Optimal Size**: 5-15 units per stack for optimal performance
- **Dependency Complexity**: Minimize complex dependency chains
- **Execution Time**: Balance parallel execution with total execution time

### 3. Monitoring

- **Execution Metrics**: Monitor execution times and resource usage
- **Error Rates**: Track error rates and retry patterns
- **Cost Impact**: Monitor cost impact of parallel execution

## Future Enhancements

### Planned Features

1. **Recursive Stacks**: Support for nested stack structures
2. **Cross-Stack Dependencies**: Enhanced support for dependencies between stacks
3. **Stack Templates**: Templates for common stack patterns
4. **Advanced Monitoring**: Enhanced monitoring and alerting for stacks
5. **Cost Optimization**: Automatic cost optimization recommendations

### Experimental Features Roadmap

- **Stack Versioning**: Version management for stack configurations
- **Stack Rollback**: Enhanced rollback capabilities for stacks
- **Stack Cloning**: Clone stacks for different environments
- **Stack Validation**: Enhanced validation for stack configurations

## Support and Resources

### Documentation

- [Terragrunt Experiments Documentation](https://terragrunt.gruntwork.io/docs/reference/experiments/)
- [Terragrunt Stacks Documentation](https://terragrunt.gruntwork.io/docs/features/stacks/)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)

### Community

- [Terragrunt GitHub Issues](https://github.com/gruntwork-io/terragrunt/issues)
- [Terragrunt Discussions](https://github.com/gruntwork-io/terragrunt/discussions)
- [MCP Community](https://github.com/modelcontextprotocol)

### Getting Help

1. **Check Documentation**: Review this documentation and Terragrunt docs
2. **Search Issues**: Search existing GitHub issues for similar problems
3. **Create Issue**: Create a new issue with detailed information
4. **Community Support**: Ask questions in community forums 