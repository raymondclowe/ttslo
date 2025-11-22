- be consise; less prose, more bullet points. 
- Sacrafice grammer and politeness of briefness and clarity.
- Save important learnings into LEARNINGS.md to avoid reinventing the wheel or making same mistakes repeatedly
- Check LEARNINGS.md before asking for help or searching online
- For Docker image rebuild issues, see DOCKER_REBUILD_GUIDE.md first

## Environment Setup

The repository uses `.github/workflows/copilot-setup-steps.yml` to automatically:
- Install `uv` package manager (via `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Add `uv` to PATH: `$HOME/.local/bin`
- Run `uv sync` to install all dependencies (including pytest)
- Verify pytest works with `uv run pytest --version`

Always use 'uv run <command>' for Python commands:
- `uv run ttslo.py` instead of `python3 ttslo.py`
- `uv run pytest` instead of `pytest`

Kraken API Balance Handling:
1. Kraken returns balances with multiple potential key formats:
   - Spot wallet: 'XXBT', 'XETH', etc.
   - Funding wallet: 'XBT.F', 'ETH.F', etc.
   - Some assets have both spot and funding balances
   - Example: A user with 0.01069 BTC in their funding wallet shows as:
     ```
     {
       'XXBT': '0.0000000000',  # spot wallet
       'XBT.F': '0.0106906064'  # funding wallet
     }
     ```

2. When checking balances, you must:
   - Consider both spot and funding wallet balances
   - Remove '.F' suffix when matching asset keys
   - Strip 'X' prefixes for normalization
   - Sum up all matching balances for total available
   - Example: For BTC balance, check both 'XXBT' and 'XBT.F'

3. Asset Key Variations:
   - Bitcoin: 'XXBT', 'XBT.F'
   - Ethereum: 'XETH', 'ETH.F'
   - Others may follow similar patterns

4. Best Practices:
   - Always normalize asset keys before comparing
   - Sum balances across all matching keys
   - Print found keys in warnings/errors for debugging
   - Don't assume balance is only under the canonical key
   - Consider the funding wallet ('.F' suffix) as equally valid

5. Debugging Tips:
   - Print raw API response to see all key variations
   - Try multiple key formats when searching
   - Log which keys contributed to total balance
   - Create separate debug tools for API testing

   UV / venv / pytest notes
   ------------------------
   When working in this repository use the project's `uv`-managed virtual environment so tests and runtime imports match what developers expect.

   Quick rules:
   - Use `uv run <command>` to execute any Python command inside the project's virtual environment (this ensures installed packages like `textual` are available).
      - Example: `uv run ttslo.py --validate-config`
      - Example: `uv run pytest -q`

   - If you need to run a Python one-liner to check imports, use:
      - `uv run python -c "import textual; print(textual.__version__)"`
      This runs the `python` from the `uv` venv and verifies packages are importable.

   - To install runtime or dev dependencies into the `uv` venv, use `uv add` and then `uv sync` as needed:
      - `uv add textual` (install textual for the CSV TUI)
      - `uv add pytest` (install pytest into the venv for running tests)
      - `uv sync` (resolve and install packages declared by the project manager)

   - If you prefer to call the venv Python directly, `uv` creates a venv at `.venv` by default; the interpreter is:
      - `/workspaces/ttslo/.venv/bin/python3`
      - After installing `pytest` into the venv you can run tests with:
         - `/workspaces/ttslo/.venv/bin/python3 -m pytest -q`

   Troubleshooting tips:
   - If `uv run pytest` or `uv run python` reports a ModuleNotFoundError (e.g., `textual`), make sure you've installed the package into the project venv with `uv add textual` and re-run `uv sync`.
   - If pytest isn't installed in the venv, `uv run pytest` may still fail. Install pytest into the venv with `uv add pytest` and then run `uv run pytest -q`.
   - Using `uv run` is preferred over system `python` or using the container's `python` directly; it ensures the same environment used during development and CI.

   Why this matters
   - Tests and the TUI depend on packages that are not in the base system Python. Running under the `uv` venv guarantees correct imports and reproduces developer expectations.

# Testing in copilot agent workspace
- creds.py should look for a github environment secret called `COPILOT_KRAKEN_API_KEY` and `COPILOT_KRAKEN_API_SECRET` to be able to do read only tests to get our live data from production but read only to test things like checking open orders.
