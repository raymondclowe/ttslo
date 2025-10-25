#!/bin/bash
# Validation script to test that the Copilot setup environment is working correctly
# This simulates what the copilot-setup-steps workflow does

set -e  # Exit on error

echo "=== Copilot Setup Validation ==="
echo ""

# Check Python version
echo "1. Checking Python version..."
python3 --version
echo "✓ Python available"
echo ""

# Check uv installation
echo "2. Checking uv installation..."
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found - installing now..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "✓ uv already installed"
fi
uv --version
echo ""

# Sync dependencies
echo "3. Syncing dependencies with uv..."
uv sync
echo "✓ Dependencies synced"
echo ""

# Verify pytest
echo "4. Verifying pytest availability..."
uv run pytest --version
echo "✓ pytest available"
echo ""

# Run a quick test
echo "5. Running quick test validation..."
uv run pytest tests/ -k "test_load_config" -q
echo "✓ Tests can run successfully"
echo ""

echo "=== All validation checks passed! ==="
echo ""
echo "You can now use:"
echo "  - uv run ttslo.py --validate-config"
echo "  - uv run pytest -q"
echo "  - uv run python -c 'import textual; print(textual.__version__)'"
