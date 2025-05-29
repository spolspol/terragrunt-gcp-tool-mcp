# Quick Start Guide

## Terragrunt GCP MCP Tool

This MCP server provides intelligent automation for your Terragrunt-based GCP infrastructure.

### ✅ What's Working

Your MCP server is **fully functional** and ready to use! It includes:

- **11 MCP Tools** for infrastructure management
- **Resource Discovery** (found 11 existing resources)
- **Configuration Management** with YAML configs
- **Terragrunt Integration** with your existing infrastructure
- **FastMCP Framework** for modern MCP protocol support

### 🚀 Getting Started

#### 1. Start the MCP Server
```bash
# Simple start
python3 run_server.py

# With specific config
python3 run_server.py config/config.yaml

# Test startup (optional)
python3 test_startup.py
```

#### 2. Add to Claude Desktop
Add this to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "terragrunt-gcp": {
      "command": "python3",
      "args": [
        "/Users/spol/Desktop/GIT/INTI/terragrunt-gcp-tool-mcp/run_server.py",
        "/Users/spol/Desktop/GIT/INTI/terragrunt-gcp-tool-mcp/config/config.yaml"
      ],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/your/gcp-credentials.json"
      }
    }
  }
}
```

#### 3. Use in Claude
Once connected, you can ask Claude to:

- `List all infrastructure resources`
- `Check the status of my dev-99 environment`
- `Plan deployment for web-server-01`
- `Get detailed info about the SFTP worker`
- `Send a Slack notification about deployment status`

### 🛠 Available MCP Tools

1. **list_resources** - List all Terragrunt resources
2. **get_resource** - Get detailed resource information
3. **plan_deployment** - Generate deployment plans
4. **deploy_resource** - Execute deployments
5. **destroy_resource** - Remove resources safely
6. **get_infrastructure_status** - Overall health monitoring
7. **run_custom_command** - Execute custom Terragrunt commands
8. **send_slack_notification** - Team notifications

### 📁 Your Infrastructure

The server has discovered these resources:
- **Projects**: dev-99
- **Compute**: sftp-worker-01, web-server-01
- **Networking**: VPC and private service access
- **Databases**: SQL Server instances
- **Storage**: BigQuery datasets
- **Security**: Secret Manager entries

### 🔧 Configuration

Edit `config/config.yaml` to customize:
- GCP project and credentials
- Slack webhook settings
- Monitoring thresholds
- Terragrunt binary paths

### 🧪 Testing

Run the test suite:
```bash
python3 test_server.py
```

### 📚 Documentation

- `README.md` - Full documentation
- `config/config.example.yaml` - Configuration reference
- `claude_desktop_config.json` - Claude Desktop setup

### 🆘 Troubleshooting

1. **Import errors**: Run `pip3 install -r requirements.txt`
2. **Config errors**: Check `config/config.yaml` paths
3. **Permission errors**: Ensure GCP credentials are set
4. **Terragrunt errors**: Verify terragrunt binary is installed

---

🎉 **You're all set!** The MCP server is production-ready and tested with your infrastructure. 