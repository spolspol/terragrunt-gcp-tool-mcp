"""Terragrunt GCP MCP Tool

A Model Context Protocol server for managing GCP infrastructure with Terragrunt.
Compatible with Terragrunt CLI Redesign.
"""

__version__ = "0.2.0"
__author__ = "Infrastructure Team"
__email__ = "infra@example.com"

from .server import TerragruntGCPMCPServer

__all__ = ["TerragruntGCPMCPServer"] 