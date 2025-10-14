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
  - `activate_on`: validates ISO datetime format (YYYY-MM-DDTHH:MM:SS)
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

If no filename is provided, it defaults to `config.csv`.

### Examples

Edit the TTSLO configuration file:
```bash
python csv_editor.py config.csv
```

Edit the sample configuration:
```bash
python csv_editor.py config_sample.csv
```

Edit any other CSV file:
```bash
python csv_editor.py my_data.csv
```

### Using with uv

If you're using uv for the project:

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Then run the editor
python csv_editor.py config.csv
```

## Key Bindings

| Key Combination | Action |
|----------------|--------|
| `Ctrl+S` | Save the CSV file |
| `Ctrl+Q` | Quit the application |
| `Ctrl+N` | Add a new row |
| `Ctrl+D` | Delete the current row |
| `Enter` | Edit the selected cell |
| `Tab` / `Shift+Tab` | Navigate between cells |
| `Arrow Keys` | Navigate the table |
| `Escape` | Cancel cell editing |

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
- `pair`: Kraken trading pair (e.g., XXBTZUSD, XETHZUSD)
- `threshold_price`: Price threshold that triggers the order
- `threshold_type`: "above" or "below"
- `direction`: "buy" or "sell"
- `volume`: Amount to trade
- `trailing_offset_percent`: Trailing stop offset percentage
- `enabled`: "true" or "false"
- `activate_on`: Optional ISO datetime (YYYY-MM-DDTHH:MM:SS) - leave empty for immediate activation

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
| `pair` | Validated against known Kraken pairs | `XXBTZUSD`, `XETHZUSD`, `SOLUSD` |
| `activate_on` | Must be ISO datetime format or empty | `2025-12-31T23:59:59`, `` (empty) |
| `id` | Must be unique across all rows | `btc_1`, `eth_trigger_2` |

### Known Trading Pairs

The editor validates pairs against a list of common Kraken trading pairs including:
- Bitcoin: `XXBTZUSD`, `XBTCUSD`, `XXBTZEUR`, `XXBTZGBP`, `XXBTZJPY`
- Ethereum: `XETHZUSD`, `ETHCUSD`, `XETHZEUR`, `XETHZGBP`, `XETHZJPY`
- Solana: `SOLUSD`, `SOLEUR`, `SOLGBP`
- Cardano: `ADAUSD`, `ADAEUR`, `ADAGBP`
- Polkadot: `DOTUSD`, `DOTEUR`, `DOTGBP`
- Avalanche: `AVAXUSD`, `AVAXEUR`
- Chainlink: `LINKUSD`, `LINKEUR`
- Stablecoins: `USDTUSD`, `USDCUSD`, `DAIUSD`

If you use a pair not in this list, you'll see a warning but can still save. Make sure to verify it's a valid Kraken pair before running TTSLO.

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
