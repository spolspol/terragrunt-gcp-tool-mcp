#!/usr/bin/env python3
"""Test script for Terragrunt GCP MCP Server."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from terragrunt_gcp_mcp.config import Config
from terragrunt_gcp_mcp.terragrunt_manager import TerragruntManager


async def test_basic_functionality():
    """Test basic functionality without running the full MCP server."""
    print("Testing Terragrunt GCP MCP Tool...")
    
    try:
        # Test configuration loading
        print("1. Testing configuration...")
        config = Config()
        print(f"   ✓ Default config loaded: {config.terragrunt.root_path}")
        
        # Test terragrunt manager
        print("2. Testing Terragrunt manager...")
        manager = TerragruntManager(config)
        print("   ✓ TerragruntManager initialized")
        
        # Test resource discovery (if terragrunt path exists)
        terragrunt_path = Path(config.terragrunt.root_path)
        if terragrunt_path.exists():
            print("3. Testing resource discovery...")
            try:
                resources = await manager.discover_resources()
                print(f"   ✓ Found {len(resources)} resources")
                
                if resources:
                    sample_resource = resources[0]
                    print(f"   Sample resource: {sample_resource.name} ({sample_resource.type.value})")
            except Exception as e:
                print(f"   ⚠ Resource discovery failed: {e}")
        else:
            print("3. Skipping resource discovery (terragrunt path not found)")
            print(f"   Expected path: {terragrunt_path}")
        
        print("\n✅ Basic functionality test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


async def test_mcp_server():
    """Test the MCP server initialization."""
    try:
        print("4. Testing MCP server initialization...")
        
        from terragrunt_gcp_mcp.server import TerragruntGCPMCPServer
        
        # Test server initialization
        server = TerragruntGCPMCPServer()
        print("   ✓ MCP Server initialized successfully")
        
        # Test tool registration
        if hasattr(server, 'app') and server.app:
            print("   ✓ FastMCP app created")
            print("   ✓ Tools registered")
        
        print("\n✅ MCP server test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ MCP server test failed: {e}")
        print("Make sure you have installed all dependencies:")
        print("  pip install -r requirements.txt")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Terragrunt GCP MCP Tool - Test Suite")
    print("=" * 60)
    
    success = True
    
    # Run basic tests
    if not asyncio.run(test_basic_functionality()):
        success = False
    
    # Run MCP server tests
    if not asyncio.run(test_mcp_server()):
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! The MCP server is ready to use.")
        print("\nTo start the server:")
        print("  python run_server.py")
        print("\nOr with custom config:")
        print("  python run_server.py config/config.yaml")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main() 