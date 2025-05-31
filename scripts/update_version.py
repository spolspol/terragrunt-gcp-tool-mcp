#!/usr/bin/env python3
"""
Version update script for semantic-release.
Updates version numbers in pyproject.toml and __init__.py files.
"""

import argparse
import re
import sys
from pathlib import Path


def update_pyproject_toml(version: str, file_path: Path) -> bool:
    """Update version in pyproject.toml file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Pattern to match version = "x.y.z"
        pattern = r'version\s*=\s*"[^"]*"'
        replacement = f'version = "{version}"'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            print(f"✅ Updated version to {version} in {file_path}")
            return True
        else:
            print(f"⚠️  No version found to update in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def update_init_py(version: str, file_path: Path) -> bool:
    """Update version in __init__.py file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Pattern to match __version__ = "x.y.z"
        pattern = r'__version__\s*=\s*"[^"]*"'
        replacement = f'__version__ = "{version}"'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            print(f"✅ Updated __version__ to {version} in {file_path}")
            return True
        else:
            print(f"⚠️  No __version__ found to update in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def update_package_json(version: str, file_path: Path) -> bool:
    """Update version in package.json file if it exists."""
    if not file_path.exists():
        return True  # Not an error if file doesn't exist
        
    try:
        import json
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data['version'] = version
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Add trailing newline
        
        print(f"✅ Updated version to {version} in {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def validate_version(version: str) -> bool:
    """Validate that the version follows semantic versioning."""
    # Basic semver pattern: major.minor.patch with optional pre-release and build metadata
    pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    
    if re.match(pattern, version):
        return True
    else:
        print(f"❌ Invalid semantic version format: {version}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Update version numbers in project files"
    )
    parser.add_argument(
        "version",
        help="New version number (semantic versioning format)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    
    args = parser.parse_args()
    
    # Validate version format
    if not validate_version(args.version):
        sys.exit(1)
    
    print(f"🔄 Updating version to {args.version}")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    
    # Define file paths
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"
    init_py_path = project_root / "src" / "terragrunt_gcp_mcp" / "__init__.py"
    package_json_path = project_root / "package.json"
    
    success = True
    
    # Update pyproject.toml
    if pyproject_path.exists():
        if not args.dry_run:
            success &= update_pyproject_toml(args.version, pyproject_path)
        else:
            print(f"📝 Would update version in {pyproject_path}")
    else:
        print(f"⚠️  pyproject.toml not found at {pyproject_path}")
        success = False
    
    # Update __init__.py
    if init_py_path.exists():
        if not args.dry_run:
            success &= update_init_py(args.version, init_py_path)
        else:
            print(f"📝 Would update __version__ in {init_py_path}")
    else:
        print(f"⚠️  __init__.py not found at {init_py_path}")
        success = False
    
    # Update package.json (optional)
    if not args.dry_run:
        success &= update_package_json(args.version, package_json_path)
    else:
        if package_json_path.exists():
            print(f"📝 Would update version in {package_json_path}")
    
    if success:
        print(f"🎉 Successfully updated version to {args.version}")
        sys.exit(0)
    else:
        print("❌ Some updates failed")
        sys.exit(1)


if __name__ == "__main__":
    main() 