"""Setup script for Terragrunt GCP MCP Tool."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="terragrunt-gcp-mcp",
    version="0.2.0",
    description="MCP server tool for managing GCP infrastructure with Terragrunt (CLI Redesign Compatible)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Infrastructure Team",
    author_email="infra@example.com",
    url="https://github.com/your-org/terragrunt-gcp-tool-mcp",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "terragrunt-gcp-mcp=terragrunt_gcp_mcp.cli:main",
            "terragrunt-mcp-server=terragrunt_gcp_mcp.server:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Systems Administration",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="terragrunt terraform gcp mcp infrastructure automation",
    project_urls={
        "Bug Reports": "https://github.com/your-org/terragrunt-gcp-tool-mcp/issues",
        "Source": "https://github.com/your-org/terragrunt-gcp-tool-mcp",
        "Documentation": "https://github.com/your-org/terragrunt-gcp-tool-mcp/blob/main/README.md",
    },
) 