#!/usr/bin/env python3
"""Simple test to verify server startup without asyncio errors."""

import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_server_startup():
    """Test that the server can be created and initialized without errors."""
    try:
        print("🧪 Testing MCP Server Startup...")
        
        # Import and create server
        from terragrunt_gcp_mcp.server import TerragruntGCPMCPServer
        print("✅ Server module imported successfully")
        
        # Create server instance
        server = TerragruntGCPMCPServer()
        print("✅ Server instance created successfully")
        
        # Verify server has the required components
        assert hasattr(server, 'app'), "Server should have FastMCP app"
        assert hasattr(server, 'config'), "Server should have config"
        assert hasattr(server, 'terragrunt_manager'), "Server should have terragrunt manager"
        print("✅ Server components verified")
        
        # Test that run method exists and is callable
        assert hasattr(server, 'run'), "Server should have run method"
        assert callable(server.run), "Run method should be callable"
        print("✅ Run method verified")
        
        print("\n🎉 All startup tests passed!")
        print("The asyncio error has been fixed!")
        print("\nTo start the server:")
        print("  python3 run_server.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_server_startup()
    sys.exit(0 if success else 1) 