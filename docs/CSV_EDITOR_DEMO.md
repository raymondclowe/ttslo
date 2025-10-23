# CSV Editor TUI - Visual Demo

This document provides a visual walkthrough of the CSV Editor's features and interface.

## Application Layout

```
┌─ CSV Editor - config.csv ─────────────────────────────────────────────────────┐
│ Path: /home/user/ttslo/config.csv                                             │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Main Table ──────────────────────────────────────────────────────────┐   │
│  │ id     │ pair      │ threshold_price │ threshold_type │ direction │...│   │
│  │────────┼───────────┼─────────────────┼────────────────┼───────────┼───│   │
│  │ btc_1  │ XXBTZUSD  │ 50000          │ above          │ sell      │...│   │
│  │ eth_1  │ XETHZUSD  │ 3000           │ above          │ sell      │...│   │
│  │ ...                                                                    │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
├────────────────────────────────────────────────────────────────────────────────┤
│ ^S Save CSV │ ^Q Quit │ ^N Add Row │ ^D Delete Row │ ⏎ Edit Cell            │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Features Demonstration

### 1. Table View with Navigation

When you start the CSV Editor, you see a formatted table with:
- **Header row** with column names
- **Data rows** with zebra striping (alternating colors) for readability
- **Cell cursor** showing which cell is selected
- **Footer** with keyboard shortcuts

**Navigation:**
- Use **Arrow Keys** to move between cells
- Use **Tab** to move to the next cell
- Use **Shift+Tab** to move to the previous cell
- Use **Page Up/Page Down** for faster scrolling (if available)

### 2. Cell Editing

**To edit a cell:**

1. Navigate to the cell you want to edit using arrow keys
2. Press **Enter** to open the edit dialog

```
┌────────────────────────────────────────┐
│          Edit Cell Value               │
│                                        │
│  ┌────────────────────────────────┐   │
│  │ 50000                          │   │
│  └────────────────────────────────┘   │
│                                        │
│  ┌──────────┐  ┌──────────┐          │
│  │   Save   │  │  Cancel  │          │
│  └──────────┘  └──────────┘          │
└────────────────────────────────────────┘
```

3. Type the new value
4. Press **Enter** or click **Save** to confirm
5. Press **Escape** or click **Cancel** to abort

**Result:**
- The cell updates with the new value
- A notification appears: "Cell updated"
- The cursor remains on the edited cell

### 3. Adding New Rows

**To add a new row:**

1. Press **Ctrl+N** anywhere in the table
2. A new empty row appears at the bottom of the table
3. A notification appears: "New row added"
4. Navigate to the new row and edit cells as needed

**Example:**

Before:
```
┌──────┬──────────┬─────────────────┬────────────────┐
│ id   │ pair     │ threshold_price │ threshold_type │
├──────┼──────────┼─────────────────┼────────────────┤
│ btc_1│ XXBTZUSD │ 50000          │ above          │
│ eth_1│ XETHZUSD │ 3000           │ above          │
└──────┴──────────┴─────────────────┴────────────────┘
```

After pressing Ctrl+N:
```
┌──────┬──────────┬─────────────────┬────────────────┐
│ id   │ pair     │ threshold_price │ threshold_type │
├──────┼──────────┼─────────────────┼────────────────┤
│ btc_1│ XXBTZUSD │ 50000          │ above          │
│ eth_1│ XETHZUSD │ 3000           │ above          │
│      │          │                 │                │ ← New row
└──────┴──────────┴─────────────────┴────────────────┘
```

### 4. Deleting Rows

**To delete a row:**

1. Navigate to any cell in the row you want to delete
2. Press **Ctrl+D**
3. The row is removed from the table
4. A notification appears: "Row deleted"

**Note:** You cannot delete the last remaining row.

**Example:**

Before (cursor on second row):
```
┌──────┬──────────┬─────────────────┬────────────────┐
│ id   │ pair     │ threshold_price │ threshold_type │
├──────┼──────────┼─────────────────┼────────────────┤
│ btc_1│ XXBTZUSD │ 50000          │ above          │
│►eth_1│ XETHZUSD │ 3000           │ above          │ ← Current row
│ ltc_1│ XLTCZUSD │ 100            │ above          │
└──────┴──────────┴─────────────────┴────────────────┘
```

After pressing Ctrl+D:
```
┌──────┬──────────┬─────────────────┬────────────────┐
│ id   │ pair     │ threshold_price │ threshold_type │
├──────┼──────────┼─────────────────┼────────────────┤
│ btc_1│ XXBTZUSD │ 50000          │ above          │
│►ltc_1│ XLTCZUSD │ 100            │ above          │
└──────┴──────────┴─────────────────┴────────────────┘
```

### 5. Saving Changes

**To save your changes:**

1. Press **Ctrl+S** at any time
2. The file is saved to disk (overwrites the original)
3. A notification appears: "File saved: config.csv"

**Status indicators:**
- Green notification: Save successful
- Red notification: Save failed (with error message)

### 6. Quitting the Application

**To exit:**

1. Press **Ctrl+Q** at any time
2. The application closes immediately

**Important:** Changes are **not** auto-saved. Make sure to press **Ctrl+S** before quitting if you want to keep your changes.

## Notifications

The CSV Editor provides visual feedback for all operations:

```
┌─ Success ─────────────────────────────────┐
│ ✓ File saved: config.csv                  │
└────────────────────────────────────────────┘

┌─ Information ─────────────────────────────┐
│ ℹ Loaded 2 rows from config.csv          │
└────────────────────────────────────────────┘

┌─ Warning ─────────────────────────────────┐
│ ⚠ No row selected                        │
└────────────────────────────────────────────┘

┌─ Error ───────────────────────────────────┐
│ ✗ File not found: missing.csv            │
└────────────────────────────────────────────┘
```

## Keyboard Shortcuts Summary

| Key           | Action                    | Context    |
|---------------|---------------------------|------------|
| Arrow Keys    | Navigate cells            | Table      |
| Tab           | Next cell                 | Table      |
| Shift+Tab     | Previous cell             | Table      |
| Enter         | Edit selected cell        | Table      |
| Ctrl+S        | Save CSV file             | Anywhere   |
| Ctrl+Q        | Quit application          | Anywhere   |
| Ctrl+N        | Add new row               | Table      |
| Ctrl+D        | Delete current row        | Table      |
| Escape        | Cancel editing            | Edit Modal |

## Example Workflow: Editing a TTSLO Config

**Scenario:** Add a new trading strategy for Litecoin

1. **Start the editor:**
   ```bash
   python csv_editor.py config.csv
   ```

2. **Add a new row:**
   - Press `Ctrl+N`
   - A new empty row appears at the bottom

3. **Fill in the details:**
   - Navigate to the new row's first cell (id)
   - Press `Enter`, type `ltc_1`, press `Enter`
   - Move to the next cell (pair)
   - Press `Enter`, type `XLTCZUSD`, press `Enter`
   - Continue for all fields:
     - threshold_price: `100`
     - threshold_type: `above`
     - direction: `sell`
     - volume: `1.0`
     - trailing_offset_percent: `5.0`
     - enabled: `true`

4. **Save the file:**
   - Press `Ctrl+S`
   - See confirmation: "File saved: config.csv"

5. **Validate your changes:**
   - Press `Ctrl+Q` to exit
   - Run: `python ttslo.py --validate-config`

## Tips and Best Practices

### 1. Regular Saves
Save frequently (Ctrl+S) to avoid losing work, especially when making multiple changes.

### 2. Backup Important Files
Before editing critical configurations:
```bash
cp config.csv config.csv.backup
python csv_editor.py config.csv
```

### 3. Test After Editing
Always validate your configuration after editing:
```bash
python csv_editor.py config.csv
# ... make changes ...
# ... Ctrl+S to save ...
# ... Ctrl+Q to quit ...
python ttslo.py --validate-config
```

### 4. Use the Sample File for Practice
Practice with the sample file before editing your live config:
```bash
python csv_editor.py config_sample.csv
```

### 5. Watch for Notifications
Pay attention to the notifications that appear after each operation. They provide important feedback about success or errors.

## Troubleshooting

### The editor won't start
**Symptom:** Error when running `python csv_editor.py`

**Solution:** Make sure textual is installed:
```bash
pip install textual
# or with uv
uv add textual
```

### Can't edit cells
**Symptom:** Typing doesn't work

**Solution:** You must press `Enter` first to open the edit dialog. The table itself is not directly editable.

### Changes aren't saved
**Symptom:** After editing and quitting, the file hasn't changed

**Solution:** Remember to press `Ctrl+S` to save before `Ctrl+Q` to quit. The editor doesn't auto-save.

### Cell values look wrong
**Symptom:** CSV data appears corrupted

**Solution:** Make sure the CSV file is properly formatted with consistent column counts. The editor will try to pad or trim rows to match the header.

## Advanced Usage

### Editing Multiple Files in Sequence
```bash
# Edit config
python csv_editor.py config.csv

# Edit state (if needed)
python csv_editor.py state.csv

# Edit logs (for review)
python csv_editor.py logs.csv
```

### Using with Different Terminal Themes
The CSV Editor adapts to your terminal theme. For best results:
- Use a terminal with 256 colors or true color support
- Ensure your terminal is at least 80 columns wide
- Use a readable font size (12pt or larger recommended)

### Keyboard Navigation Speed
For faster navigation with large files:
- Use `Tab` to jump between cells quickly
- Use `Ctrl+N` to add rows at the end (faster than scrolling)
- Keep your file organized (enabled configs at top, disabled at bottom)

---

## Summary

The CSV Editor TUI provides a user-friendly way to edit TTSLO configuration files with:
- ✓ Visual table view with color coding
- ✓ Safe editing with modal dialogs
- ✓ Row management (add/delete)
- ✓ Keyboard-driven workflow
- ✓ Clear visual feedback
- ✓ No risk of format corruption

For more details, see [CSV_EDITOR_README.md](CSV_EDITOR_README.md).
