# Copilot Workspace Environment Setup

## Overview

This repository uses GitHub Actions to automatically set up the Copilot agent workspace with all required tools and dependencies. No manual installation is needed.

## What Gets Installed

When a GitHub Copilot agent starts, the following happens automatically:

1. **Python 3.12** - Set up via `actions/setup-python@v5`
2. **uv package manager** - Installed via official script from astral.sh
3. **All project dependencies** - Installed via `uv sync` from `pyproject.toml`
4. **pytest** - Available as part of project dependencies

## How It Works

### The Workflow

File: `.github/workflows/copilot-setup-steps.yml`

This workflow uses the special job name `copilot-setup-steps` which GitHub Copilot recognizes and runs automatically before the agent initializes.

### Workflow Steps

```yaml
1. Checkout repository     → Gets latest code
2. Set up Python           → Ensures Python 3.12
3. Install uv              → curl -LsSf https://astral.sh/uv/install.sh | sh
4. Verify uv installation  → uv --version
5. Sync dependencies       → uv sync
6. Verify pytest           → uv run pytest --version
7. Run test suite          → uv run pytest -q --tb=short
```

### Why This Approach

- **Automatic**: No manual steps required per session
- **Consistent**: Same environment every time
- **Fast**: Cached dependencies make subsequent runs quick
- **Reliable**: Uses official installation methods
- **Testable**: Can be triggered manually for validation

## Usage for Copilot Agents

Once the workflow completes, agents can immediately use:

```bash
# Run the main application
uv run ttslo.py --validate-config

# Run all tests
uv run pytest -q

# Run specific tests
uv run pytest tests/test_dashboard.py -v

# Run Python commands
uv run python -c "import textual; print(textual.__version__)"

# Use any Python package from pyproject.toml
uv run python -c "import requests; print(requests.__version__)"
```

## Local Development

Developers can use the same setup locally:

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Sync dependencies (run in project root)
uv sync

# Now you can use the same commands as agents
uv run pytest -q
uv run ttslo.py --help
```

## Validation

### Automatic Validation

The workflow automatically validates the setup by:
- Checking uv version
- Checking pytest version  
- Running the test suite

### Manual Validation

You can validate the setup locally:

```bash
# Run the validation script
./.github/workflows/validate-setup.sh

# Or manually check each component
uv --version
uv run pytest --version
uv run pytest -q
```

## Troubleshooting

### uv not found

If you see "uv: command not found":

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to current session PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Dependencies not installed

If you see "ModuleNotFoundError":

```bash
# Sync dependencies
uv sync

# Verify installation
uv run python -c "import textual"
```

### Tests fail

Some tests may fail due to missing credentials. This is expected:
- Tests that need Kraken API credentials will be skipped
- Core functionality tests should pass
- Pre-existing failures are not your responsibility to fix

## Workflow Maintenance

### Updating Dependencies

Dependencies are managed in `pyproject.toml`. To add a new dependency:

```bash
# Add runtime dependency
uv add package-name

# Add dev dependency  
uv add --dev package-name

# Sync to install
uv sync
```

### Updating Python Version

To update the Python version:

1. Edit `.github/workflows/copilot-setup-steps.yml`
2. Change `python-version: '3.12'` to desired version
3. Update `requires-python` in `pyproject.toml` if needed

### Testing Workflow Changes

Trigger the workflow manually from GitHub:

1. Go to **Actions** tab
2. Select **Copilot Setup Steps**
3. Click **Run workflow**
4. Review logs to ensure it completes successfully

## Related Documentation

- **AGENTS.md** - Instructions for Copilot agents
- **LEARNINGS.md** - Project learnings including setup patterns
- **pyproject.toml** - Dependency definitions
- **.github/workflows/README.md** - Workflow-specific docs
- **.github/workflows/validate-setup.sh** - Validation script

## Key Points for Future Reference

1. The workflow name `copilot-setup-steps` is **special** and recognized by GitHub Copilot
2. The job must be named `copilot-setup-steps` (exact match)
3. The workflow runs in GitHub Actions before the agent workspace initializes
4. Changes to this workflow affect all future Copilot sessions
5. Use `uv run` prefix for all Python commands to ensure correct environment
6. Dependencies from `pyproject.toml` are automatically available
7. The `.venv` directory is created automatically by `uv sync`

## Success Indicators

You know the setup is working when:

- ✅ `uv --version` shows version 0.9.x or higher
- ✅ `uv run pytest --version` shows pytest version
- ✅ `uv run pytest -q` runs tests successfully
- ✅ No manual installation steps needed
- ✅ All agents have consistent environment

---

**Last Updated**: 2025-10-25  
**Maintained By**: Repository maintainers via PR review process
