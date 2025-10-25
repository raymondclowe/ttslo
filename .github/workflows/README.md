# Copilot Setup Steps Workflow

This workflow automatically sets up the GitHub Copilot agent environment with all required tools and dependencies.

## What it does

The `copilot-setup-steps.yml` workflow runs **before** the Copilot agent starts and:

1. **Checks out the repository** - Gets latest code
2. **Sets up Python 3.12** - Ensures correct Python version
3. **Installs uv package manager** - Uses official installation script
4. **Adds uv to PATH** - Makes it available to the agent
5. **Syncs dependencies** - Installs all packages from `pyproject.toml`
6. **Verifies pytest** - Confirms test framework is ready
7. **Runs test suite** - Validates environment setup (errors allowed)

## How it works

GitHub Copilot recognizes the special job name `copilot-setup-steps` and runs it automatically before initializing the agent workspace. This ensures:

- ✅ No manual installation steps needed
- ✅ Consistent environment every session  
- ✅ All dependencies available immediately
- ✅ Agent can run tests with `uv run pytest`

## Validation

You can validate the setup locally by running:

```bash
./.github/workflows/validate-setup.sh
```

This script tests all the key components that the workflow sets up.

## Manual trigger

You can manually trigger this workflow from GitHub Actions UI:

1. Go to **Actions** tab
2. Select **Copilot Setup Steps** workflow
3. Click **Run workflow** button

This is useful for testing workflow changes.

## Key commands for Copilot agents

After this workflow runs, agents can use:

```bash
# Run the main application
uv run ttslo.py --validate-config

# Run tests
uv run pytest -q

# Run specific test file
uv run pytest tests/test_dashboard.py -v

# Run Python one-liners
uv run python -c "import textual; print(textual.__version__)"
```

## Related documentation

- `AGENTS.md` - Agent instructions including environment setup
- `LEARNINGS.md` - Lessons learned about Copilot workspace setup
- `pyproject.toml` - Source of truth for dependencies
- `validate-setup.sh` - Script to validate the setup locally
