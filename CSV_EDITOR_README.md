# CSV Editor - TUI for Editing Configuration Files

The CSV Editor is a standalone text-based user interface (TUI) application built with [Textual](https://textual.textualize.io/) for viewing and editing CSV files. It's specifically designed for editing TTSLO configuration files but can be used with any CSV file.

## Features

- **Interactive Table View**: View CSV data in a formatted, easy-to-read table
- **Cell Editing**: Edit individual cells with a modal dialog and real-time validation
- **Validation Rules**: Built-in validation for TTSLO configuration fields:
  - `threshold_type`: must be "above" or "below"
  - `direction`: must be "buy" or "sell"
  - `enabled`: must be true/false, yes/no, or 1/0
  - `pair`: validates against known Kraken trading pairs (warning if unknown)
  - `id`: prevents duplicate IDs across all rows
- **Row Management**: Add new rows or delete existing rows
- **Save Functionality**: Save changes back to the CSV file
- **Keyboard Navigation**: Full keyboard support for efficient editing
- **Visual Feedback**: Color-coded notifications and zebra-striped rows for better readability

## Installation

The CSV editor is part of the TTSLO project. Make sure you have installed the dependencies:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install textual
```

## Usage

### Basic Usage

To edit a CSV file, run:

```bash
python csv_editor.py [filename]
```

If no filename is provided, the editor automatically detects the correct config file:

1. **First Priority**: Checks the `TTSLO_CONFIG_FILE` environment variable (same as the service)
2. **Second Priority**: If running as the `ttslo` user, uses `/var/lib/ttslo/config.csv`
3. **Default**: Otherwise, uses `config.csv` in the current directory

This means when you run the editor as the same user as the service, it will automatically edit the same config file the service is using!

### Examples

**Edit the service's active config** (when running as ttslo user or with TTSLO_CONFIG_FILE set):
```bash
python csv_editor.py
# Automatically uses the same config as the service
```

**Edit a specific config file**:
```bash
python csv_editor.py config.csv
```

**Edit with environment override**:
```bash
TTSLO_CONFIG_FILE=/var/lib/ttslo/config.csv python csv_editor.py
# Edits the service's config file
```

**Edit the sample configuration**:
```bash
python csv_editor.py config_sample.csv
```

**Edit any other CSV file**:
```bash
python csv_editor.py my_data.csv
```

### Using with uv

If you're using uv for the project:

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Edit the service's config (auto-detected)
python csv_editor.py

# Or specify a file
python csv_editor.py config.csv
```

## File Locking and Conflict Prevention

The CSV editor implements a sophisticated coordination protocol to prevent conflicts:

### Coordination Handshake Protocol

When you open the CSV editor, it doesn't immediately lock the file. Instead, it follows a handshake protocol with the service:

1. **Editor Signals Intent**: Creates `.editor_wants_lock` file to request exclusive access
2. **Service Detects Request**: On next check cycle, service sees the intent file
3. **Service Pauses**: Service pauses all I/O operations (config reads, state writes, logging)
4. **Service Confirms**: Service creates `.service_idle` file to signal it's safe
5. **Editor Locks**: Editor waits for confirmation, then acquires exclusive lock
6. **User Edits**: You can now safely edit with no risk of conflicts
7. **Editor Releases**: When you save and exit, editor releases lock and removes coordination files
8. **Service Resumes**: Service detects release and automatically resumes normal operations

This handshake eliminates race conditions where the service might be in the middle of writing when the editor tries to lock the file.

### What This Means for You

- **Exclusive Lock**: When you open a file for editing, the editor acquires an exclusive lock
- **Service Coordination**: Service automatically pauses operations and confirms when it's safe
- **Conflict Prevention**: No data corruption or race conditions possible
- **Visual Feedback**: The editor shows notifications for each step of the coordination

**Best Practice**: Always use the CSV editor rather than manually editing files with other tools to ensure proper coordination is used.

## Key Bindings

| Key Combination | Action |
|----------------|--------|
| `Ctrl+S` | Save the CSV file |
| `Ctrl+Q` | Quit the application (prompts if unsaved) |
| `Ctrl+N` | Add a new row |
| `Ctrl+D` | Delete the current row |
| `Ctrl+Shift+D` | Duplicate the current row |
| `Enter` | Edit the selected cell |
| `e` | Edit the selected cell (alternative) |
| `?` or `F1` | Show help screen |
| `Tab` / `Shift+Tab` | Navigate between cells |
| `Arrow Keys` | Navigate the table |
| `Escape` | Cancel cell editing |

## New Features

### Help Screen (`?` or `F1`)
Press `?` or `F1` at any time to view a comprehensive help screen showing:
- All available keybindings organized by category
- Validation rules for each field
- Quick tips and best practices
- Safety features and file locking information

The help screen provides quick reference without leaving the editor, making it easier for new users to discover features.

### Row Duplication (`Ctrl+Shift+D`)
Quickly create a similar configuration by duplicating an existing row:
1. Navigate to the row you want to duplicate
2. Press `Ctrl+Shift+D`
3. A new row is created with all values copied
4. The `id` field is automatically incremented (e.g., `btc_1` → `btc_2`)
5. Edit the duplicated row as needed and save with `Ctrl+S`

This feature is especially useful when creating multiple similar trading configurations.

### Unsaved Changes Indicator
The editor now shows visual feedback for unsaved changes:
- **Title Bar**: An asterisk (`*`) appears in the title when you have unsaved changes
- **Quit Confirmation**: When quitting with unsaved changes, you'll be prompted to:
  - Save and quit
  - Quit without saving
  - Cancel and continue editing

This helps prevent accidental data loss by making it clear when changes need to be saved.

## Editing Workflow

1. **Navigate**: Use arrow keys to move to the cell you want to edit
2. **Edit**: Press `Enter` to open the edit dialog
3. **Change**: Type the new value
4. **Confirm**: Press `Enter` or click "Save" to apply changes, or `Escape` or "Cancel" to discard
5. **Save**: Press `Ctrl+S` to save all changes to the file
6. **Exit**: Press `Ctrl+Q` to quit

## Adding and Deleting Rows

### Add a New Row
1. Press `Ctrl+N` to add a new empty row at the bottom of the table
2. Navigate to the new row and use `Enter` to edit each cell
3. Press `Ctrl+S` to save your changes

### Delete a Row
1. Navigate to the row you want to delete
2. Press `Ctrl+D` to delete the current row
3. Confirm by pressing `Ctrl+S` to save changes

**Note**: You cannot delete the last remaining row in the table.

## File Creation

If you try to open a non-existent file, the CSV editor will prompt you to create a sample configuration file with TTSLO-specific headers and example data.

## Configuration File Format

When editing TTSLO configuration files, the expected columns are:

- `id`: Unique identifier for the configuration (must be unique across all rows)
  - `pair`: Kraken trading pair (e.g., `XBTUSDT`, `ETHUSDT`). Unknown trading pairs are rejected by the editor to prevent invalid configurations; use Kraken pair codes exactly.
- `threshold_price`: Price threshold that triggers the order
- `threshold_type`: "above" or "below"
- `direction`: "buy" or "sell"
- `volume`: Amount to trade
- `trailing_offset_percent`: Trailing stop offset percentage
- `enabled`: "true" or "false"

## Validation

The CSV Editor includes built-in validation to help prevent configuration errors:

### Real-time Validation
When editing a cell, the editor validates your input before allowing you to save:

- **Invalid values are rejected**: You'll see an error message and cannot save until fixed
- **Warnings are shown**: Some validations (like unknown trading pairs) show warnings but allow saving
- **Immediate feedback**: Validation happens as soon as you try to save a cell

### Validated Fields

| Field | Validation Rule | Example Valid Values |
|-------|----------------|---------------------|
| `threshold_type` | Must be "above" or "below" | `above`, `below` |
| `direction` | Must be "buy" or "sell" | `buy`, `sell` |
| `enabled` | Must be boolean-like | `true`, `false`, `yes`, `no`, `1`, `0` |
| `pair` | Validated against known Kraken pairs | `XBTUSDT`, `ETHUSDT`, `SOLUSD` |
| `id` | Must be unique across all rows | `btc_1`, `eth_trigger_2` |

### Known Trading Pairs

The editor validates pairs against a list of common Kraken trading pairs including:
- Bitcoin: `XBTUSDT`, `XBTCUSD`, `XXBTZEUR`, `XXBTZGBP`, `XXBTZJPY`
- Ethereum: `ETHUSDT`, `ETHCUSD`, `XETHZEUR`, `XETHZGBP`, `XETHZJPY`
- Solana: `SOLUSD`, `SOLEUR`, `SOLGBP`
- Cardano: `ADAUSD`, `ADAEUR`, `ADAGBP`
- Polkadot: `DOTUSD`, `DOTEUR`, `DOTGBP`
- Avalanche: `AVAXUSD`, `AVAXEUR`
- Chainlink: `LINKUSD`, `LINKEUR`
- Stablecoins: `USDTUSD`, `USDCUSD`, `DAIUSD`

If you use a pair not in this list, the editor will reject the value and you must enter a valid Kraken pair code (for example, `XBTUSDT` or `ETHUSDT`). This prevents accidental invalid pair formats such as `BTC/USD` or `BTCUSD`.

## Tips

- **Always save your work**: Remember to press `Ctrl+S` after making changes
- **Backup important files**: Make a copy of critical configuration files before editing
- **Use validation**: After editing, run `python ttslo.py --validate-config` to verify your changes
- **Check for errors**: The editor will show notifications for any errors during save operations

## Troubleshooting

### "File not found" Error
If the file doesn't exist, the editor will offer to create a sample file for you.

### Cannot Edit Cells
Make sure you press `Enter` to open the edit dialog. Direct typing in the table is not supported.

### Changes Not Saved
Remember to press `Ctrl+S` to save changes. The editor doesn't auto-save.

### Application Won't Start
Ensure you have installed the textual library:
```bash
uv add textual
# or
pip install textual
```

## Technical Details

The CSV editor is built with:
- **Textual**: Modern TUI framework for Python
- **Python CSV Module**: For reliable CSV file handling
- **Async Operations**: File operations run in background threads to keep the UI responsive

## Integration with TTSLO

The CSV editor is designed to work seamlessly with TTSLO configuration files:

1. Edit your configuration: `python csv_editor.py config.csv`
2. Validate your changes: `python ttslo.py --validate-config`
3. Test with dry-run: `python ttslo.py --dry-run --once`
4. Run for real: `python ttslo.py`

## Source Code

The CSV editor is implemented in `csv_editor.py` as a standalone module. It can be used independently of TTSLO for editing any CSV files.

## License

Part of the TTSLO project. See the main README for license information.
