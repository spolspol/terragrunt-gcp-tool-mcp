# Semantic Versioning & Release Automation

This project uses automated semantic versioning and release management based on [Conventional Commits](https://www.conventionalcommits.org/) and [Semantic Release](https://semantic-release.gitbook.io/).

## 🚀 Overview

Our release automation system:
- **Automatically determines version bumps** based on commit messages
- **Generates changelogs** with categorized changes
- **Creates GitHub releases** with proper tags
- **Publishes to PyPI** and Docker registries
- **Validates commits** in pull requests
- **Provides release previews** in PRs

## 📝 Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Description | Version Bump | Example |
|------|-------------|--------------|---------|
| `feat` | New feature | **Minor** | `feat: add cost optimization recommendations` |
| `fix` | Bug fix | **Patch** | `fix: resolve memory leak in stack manager` |
| `perf` | Performance improvement | **Patch** | `perf: optimize dependency graph calculation` |
| `docs` | Documentation changes | **Patch** | `docs: update API documentation` |
| `refactor` | Code refactoring | **Patch** | `refactor: simplify configuration loading` |
| `build` | Build system changes | **Patch** | `build: update Docker base image` |
| `chore` | Maintenance tasks | **No release** | `chore: update dependencies` |
| `ci` | CI/CD changes | **No release** | `ci: add security scanning` |
| `style` | Code style changes | **No release** | `style: fix formatting` |
| `test` | Test changes | **No release** | `test: add unit tests for cost manager` |

### Breaking Changes

For **major** version bumps, use one of these patterns:

```bash
# Method 1: Exclamation mark
feat!: remove deprecated API endpoints

# Method 2: BREAKING CHANGE footer
feat: redesign configuration system

BREAKING CHANGE: Configuration file format has changed from YAML to TOML
```

### Examples

```bash
# Minor version bump (new feature)
feat(cost): add budget threshold alerts

# Patch version bump (bug fix)
fix(auth): handle expired GCP credentials gracefully

# Patch version bump (performance)
perf(stacks): implement parallel execution for large stacks

# Major version bump (breaking change)
feat!: migrate to new Terragrunt CLI redesign

BREAKING CHANGE: This version requires Terragrunt >= 0.53.0 and uses the new 'run' command structure
```

## 🔄 Release Workflows

### 1. Automatic Releases (Recommended)

**Trigger**: Push to `main` branch with conventional commits

**Workflow**: `.github/workflows/semantic-release.yml`

**Process**:
1. Analyzes commit messages since last release
2. Determines version bump type
3. Runs tests and linting
4. Updates version files
5. Generates changelog
6. Creates GitHub release
7. Publishes to PyPI and Docker registry
8. Sends notifications

### 2. Manual Releases

**Trigger**: Manual workflow dispatch

**Workflow**: `.github/workflows/manual-release.yml`

**Options**:
- **Release Type**: patch, minor, major, prerelease, etc.
- **Custom Version**: Override automatic calculation
- **Prerelease Identifier**: alpha, beta, rc
- **Skip Tests**: For emergency releases
- **Dry Run**: Preview without releasing

**Usage**:
1. Go to Actions → Manual Release
2. Click "Run workflow"
3. Select options and run

### 3. Pull Request Validation

**Trigger**: Pull request creation/updates

**Workflow**: `.github/workflows/pr-validation.yml`

**Features**:
- Validates conventional commit format
- Runs comprehensive tests
- Performs security scans
- Shows release preview
- Provides feedback on version impact

## 📋 Version Management

### Current Version Locations

The version is maintained in multiple files:
- `pyproject.toml` - Python package version
- `src/terragrunt_gcp_mcp/__init__.py` - Module version
- `package.json` - Node.js dependencies version

### Version Update Script

Use the included script to update versions manually:

```bash
# Update to specific version
python scripts/update_version.py 1.2.3

# Dry run (preview changes)
python scripts/update_version.py 1.2.3 --dry-run
```

## 🏷️ Release Types

### Production Releases

- **Branch**: `main`
- **Tags**: `v1.0.0`, `v1.1.0`, etc.
- **PyPI**: Published to main PyPI
- **Docker**: Tagged as `latest` and version

### Pre-releases

- **Branches**: `beta`, `alpha`
- **Tags**: `v1.0.0-beta.1`, `v1.0.0-alpha.1`
- **PyPI**: Published to Test PyPI
- **Docker**: Tagged with pre-release version

### Development

- **Branch**: `develop` (if used)
- **No automatic releases**
- **Manual releases only**

## 🛠️ Setup & Configuration

### Required Secrets

Configure these in your GitHub repository settings:

```bash
# PyPI publishing
PYPI_API_TOKEN=pypi-...

# Test PyPI (for pre-releases)
TEST_PYPI_API_TOKEN=pypi-...

# Slack notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Local Development

Install commit tools for better developer experience:

```bash
# Install Node.js dependencies
npm install

# Install commitizen for interactive commits
npm install -g commitizen

# Use commitizen for commits
git cz
# or
npm run commit
```

### Commit Linting

Commits are automatically validated using commitlint:

```bash
# Install commitlint
npm install -g @commitlint/cli @commitlint/config-conventional

# Test commit message
echo "feat: add new feature" | commitlint
```

## 📊 Release Analytics

### Changelog Generation

Changelogs are automatically generated with:
- **🚀 Features** - New functionality
- **🐛 Bug Fixes** - Issue resolutions
- **⚡ Performance** - Performance improvements
- **📚 Documentation** - Documentation updates
- **♻️ Refactoring** - Code improvements
- **🔧 Build System** - Build/deployment changes

### Release Notes

Each release includes:
- Version number and type
- Categorized changes
- Breaking changes (if any)
- Installation instructions
- Docker image information
- Contributor acknowledgments

## 🔍 Troubleshooting

### Common Issues

**No release triggered**:
- Check commit message format
- Ensure commits follow conventional format
- Verify branch is `main` or configured release branch

**Version conflicts**:
- Ensure all version files are in sync
- Check for manual version changes
- Verify semantic-release configuration

**Build failures**:
- Check test results in Actions
- Verify all dependencies are available
- Review security scan results

**PyPI publishing errors**:
- Verify API token is valid
- Check package name availability
- Ensure version doesn't already exist

### Debug Commands

```bash
# Test semantic-release locally
npx semantic-release --dry-run

# Validate commit messages
npx commitlint --from HEAD~1 --to HEAD --verbose

# Check next version
npx semantic-release --dry-run --no-ci

# Test version update script
python scripts/update_version.py 1.0.0 --dry-run
```

## 📚 Best Practices

### Commit Guidelines

1. **Use descriptive subjects** (50 chars max)
2. **Include scope when relevant** (`feat(auth):`, `fix(api):`)
3. **Write in imperative mood** ("add feature" not "added feature")
4. **Reference issues** (`fixes #123`, `closes #456`)
5. **Explain why, not what** in commit body

### Release Strategy

1. **Feature branches** → `main` for releases
2. **Hotfix branches** → `main` for urgent fixes
3. **Pre-release branches** for testing (`beta`, `alpha`)
4. **Tag protection** to prevent manual tag creation
5. **Branch protection** to enforce PR reviews

### Version Planning

1. **Plan breaking changes** for major versions
2. **Group related features** in minor versions
3. **Release frequently** with small changes
4. **Use pre-releases** for testing
5. **Communicate changes** clearly in release notes

## 🔗 References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Semantic Release](https://semantic-release.gitbook.io/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Actions](https://docs.github.com/en/actions) 