#!/usr/bin/env python3
"""
CSV Editor - A Textual TUI application for editing CSV files.

This is a standalone application that provides an interactive text-based
user interface for viewing and editing CSV files, specifically designed
for editing the TTSLO configuration files.

Usage:
    python csv_editor.py [filename]
    
If no filename is provided, it automatically detects the config file location:
1. Checks TTSLO_CONFIG_FILE environment variable
2. If running as 'ttslo' user, uses /var/lib/ttslo/config.csv
3. Otherwise defaults to 'config.csv' in current directory

The editor uses file locking to prevent concurrent edits and conflicts
with the running TTSLO service.

Key Bindings:
    Ctrl+S: Save the CSV file
    Ctrl+Q: Quit the application
    Ctrl+N: Add a new row
    Ctrl+D: Delete the current row
    Enter: Edit the selected cell
    Tab/Shift+Tab: Navigate between cells
    Arrow keys: Navigate the table
"""

import csv
import sys
import os
import fcntl
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header
from textual.containers import Container, Vertical
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Button
from textual import events, log, work
from pair_matcher import find_pair_match, validate_pair_exists


def get_default_config_path() -> str:
    """
    Determine the default config file path.
    
    Priority order:
    1. TTSLO_CONFIG_FILE environment variable (same as ttslo.py)
    2. If running as 'ttslo' user, use /var/lib/ttslo/config.csv
    3. Otherwise, use config.csv in current directory
    
    Returns:
        str: Path to the default config file
    """
    # First, check environment variable (same as ttslo.py does)
    env_config = os.getenv('TTSLO_CONFIG_FILE')
    if env_config:
        return env_config
    
    # Check if we're running as the ttslo service user
    try:
        import pwd
        current_user = pwd.getpwuid(os.getuid()).pw_name
        if current_user == 'ttslo':
            # Running as service user, use service directory
            return '/var/lib/ttslo/config.csv'
    except (ImportError, KeyError):
        # pwd module not available (Windows) or user not found
        pass
    
    # Default to config.csv in current directory (backwards compatible)
    return 'config.csv'


class EditCellScreen(ModalScreen[str]):
    """Modal screen for editing a cell value."""
    
    CSS = """
    EditCellScreen {
        align: center middle;
    }
    
    #edit-dialog {
        width: 60;
        height: 15;
        border: thick $background 80%;
        background: $surface;
        padding: 1;
    }
    
    #edit-dialog Label {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }
    
    #edit-dialog Input {
        width: 100%;
        margin-bottom: 1;
    }
    
    #edit-dialog Button {
        width: 50%;
    }
    
    #validation-message {
        width: 100%;
        color: $error;
        margin-bottom: 1;
        text-align: center;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, current_value: str, column_name: str = "", row_data: dict = None, 
                 all_ids: set = None, **kwargs):
        super().__init__(**kwargs)
        self.current_value = current_value
        self.column_name = column_name
        self.row_data = row_data or {}
        self.all_ids = all_ids or set()
        self.validation_message = ""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="edit-dialog"):
            yield Label(f"Edit Cell Value: {self.column_name}")
            yield Input(value=self.current_value, id="cell-input")
            yield Label("", id="validation-message")
            with Container():
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")
    
    def on_mount(self) -> None:
        """Focus the input when the screen is mounted."""
        self.query_one(Input).focus()
    
    def validate_value(self, value: str) -> Tuple[bool, str]:
        """
        Validate the cell value based on column name.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.column_name:
            return (True, "")
        
        column_lower = self.column_name.lower()
        
        # Validate id uniqueness
        if column_lower == "id":
            if value in self.all_ids and value != self.current_value:
                return (False, f"ID '{value}' already exists. Each ID must be unique.")
        
        # Validate threshold_type
        if column_lower == "threshold_type":
            valid_types = ["above", "below"]
            if value.lower() not in valid_types:
                return (False, f"Must be 'above' or 'below'")
            # Check for financially responsible order when threshold_type changes
            if self.row_data:
                result = self._validate_financial_responsibility(value)
                if result:
                    return result
        
        # Validate direction
        elif column_lower == "direction":
            valid_directions = ["buy", "sell"]
            if value.lower() not in valid_directions:
                return (False, f"Must be 'buy' or 'sell'")
            # Check for financially responsible order when direction changes
            if self.row_data:
                result = self._validate_financial_responsibility(None, value)
                if result:
                    return result
        
        # Validate enabled
        elif column_lower == "enabled":
            valid_enabled = ["true", "false", "yes", "no", "1", "0"]
            if value.lower() not in valid_enabled:
                return (False, f"Must be true/false, yes/no, or 1/0")
        
        # Validate pair - now with intelligent matching
        elif column_lower == "pair":
            # First, try to match the input to a Kraken pair
            match_result = find_pair_match(value)
            
            if match_result:
                # We found a match!
                if match_result.is_exact():
                    # Exact match - value is already correct
                    return (True, "")
                elif match_result.is_high_confidence():
                    # High confidence normalized match
                    # Return the official pair code as the formatted value
                    # The calling code will use this to update the cell
                    return (True, match_result.pair_code)
                else:
                    # Fuzzy match - warn the user
                    warning_msg = (
                        f"⚠️ Fuzzy match: '{value}' → '{match_result.pair_code}' "
                        f"(confidence: {match_result.confidence:.0%}). "
                        f"Verify this is correct!"
                    )
                    return (True, match_result.pair_code + "|" + warning_msg)
            else:
                # No match found - check if it's a valid Kraken pair code anyway
                if validate_pair_exists(value):
                    return (True, "")
                else:
                    return (False, f"Unknown trading pair: '{value}'. Try formats like BTC/USD, ETH/USDT, or use official Kraken codes.")
        
        # Validate volume - ensure it's a valid number and format to 8 decimal places
        elif column_lower == "volume":
            try:
                volume_float = float(value)
                if volume_float <= 0:
                    return (False, "Volume must be greater than 0")
                # Format to 8 decimal places
                formatted_value = f"{volume_float:.8f}"
                # Return success with the formatted value as the validation message
                # The calling code will need to be updated to use this formatted value
                return (True, formatted_value)
            except ValueError:
                return (False, "Volume must be a valid number")
        
        return (True, "")
    
    def _validate_financial_responsibility(self, new_threshold_type: str = None, 
                                          new_direction: str = None) -> Optional[Tuple[bool, str]]:
        """
        Validate that the order configuration is financially responsible.
        
        Returns None if valid, or (False, error_message) if invalid.
        """
        # Get current values from row_data
        pair = self.row_data.get('pair', '').strip().upper()
        threshold_type = (new_threshold_type or self.row_data.get('threshold_type', '')).strip().lower()
        direction = (new_direction or self.row_data.get('direction', '')).strip().lower()
        
        # Need all three values to validate
        if not all([pair, threshold_type, direction]):
            return None  # Can't validate without complete data
        
        # Lazily initialize validator on the screen instance to avoid re-creation
        if not hasattr(self, '_validator'):
            from validator import ConfigValidator
            self._validator = ConfigValidator()
        
        # Check if this is a stablecoin or BTC pair
        is_stable_pair = self._validator._is_stablecoin_pair(pair) or self._validator._is_btc_pair(pair)
        
        if not is_stable_pair:
            # For non-stablecoin pairs, we don't enforce this validation
            return None
        
        # Check for financially irresponsible combinations
        if threshold_type == 'above' and direction == 'buy':
            # Buying when price goes up = buying high
            return (False, 
                   f"❌ Financially irresponsible: Buying HIGH is not allowed. "
                   f"Buy orders should use threshold_type='below' to buy when price goes DOWN (buy low).")
        
        if threshold_type == 'below' and direction == 'sell':
            # Selling when price goes down = selling low
            return (False,
                   f"❌ Financially irresponsible: Selling LOW is not allowed. "
                   f"Sell orders should use threshold_type='above' to sell when price goes UP (sell high).")
        
        return None  # Valid combination
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            input_widget = self.query_one(Input)
            value = input_widget.value
            
            # Validate the value
            is_valid, message = self.validate_value(value)
            
            if not is_valid:
                # Show validation error
                validation_label = self.query_one("#validation-message", Label)
                validation_label.update(message)
                return
            
            # For volume field, message contains the formatted value
            final_value = value
            validation_label = self.query_one("#validation-message", Label)
            
            if self.column_name and self.column_name.lower() == "volume" and message:
                final_value = message
                # Clear any validation message for volume formatting
                validation_label.update("")
            elif self.column_name and self.column_name.lower() == "pair" and message:
                # For pair field, check if message contains a warning
                if "|" in message:
                    # Format: "PAIR_CODE|warning message"
                    final_value, warning = message.split("|", 1)
                    validation_label.update(warning)
                else:
                    # Just the resolved pair code
                    final_value = message
                    validation_label.update(f"✓ Resolved to: {message}")
            elif message:  # Warning message for other fields
                # Show warning but allow save
                validation_label.update(message)
            
            self.dismiss(final_value)
        else:
            self.dismiss(None)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the input."""
        # Validate before dismissing
        is_valid, message = self.validate_value(event.value)
        
        if not is_valid:
            # Show validation error
            validation_label = self.query_one("#validation-message", Label)
            validation_label.update(message)
            return
        
        # For volume field, message contains the formatted value
        final_value = event.value
        if self.column_name and self.column_name.lower() == "volume" and message:
            final_value = message
        elif self.column_name and self.column_name.lower() == "pair" and message:
            # For pair field, extract the resolved pair code
            if "|" in message:
                # Format: "PAIR_CODE|warning message"
                final_value = message.split("|", 1)[0]
            else:
                # Just the resolved pair code
                final_value = message
        
        self.dismiss(final_value)


class CSVEditor(App):
    """A Textual app to edit CSV files."""

    CSS = """
    Screen {
        layout: vertical;
    }
    
    #main-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    DataTable {
        width: 100%;
        height: 100%;
    }
    
    Footer {
        background: $panel;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+s", "save_csv", "Save CSV"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+n", "add_row", "Add Row"),
        Binding("ctrl+d", "delete_row", "Delete Row"),
        Binding("enter", "edit_cell", "Edit Cell"),
        Binding("e", "edit_cell", "Edit Cell (Alt)", show=True),
    ]
    
    def __init__(self, filename: str, **kwargs):
        super().__init__(**kwargs)
        self.filename = Path(filename)
        self.data: List[List[str]] = []
        self.modified = False
        self.lock_file = None  # File object for advisory lock

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        with Container(id="main-container"):
            yield DataTable(id="csv_table", zebra_stripes=True, cursor_type="cell")
        yield Footer()

    def on_mount(self) -> None:
        """Called after the application is mounted."""
        self.title = f"CSV Editor - {self.filename.name}"
        self.sub_title = f"Path: {self.filename.absolute()}"
        
        # Implement coordination protocol to safely acquire lock
        try:
            # Open the file for reading/writing to acquire lock
            # Create if doesn't exist
            if not self.filename.exists():
                self.filename.parent.mkdir(parents=True, exist_ok=True)
                self.filename.touch()
            
            # Step 1: Signal intent to edit by creating coordination file
            intent_file = Path(str(self.filename) + '.editor_wants_lock')
            intent_file.touch()
            self.notify(
                "Requesting exclusive access from service...",
                title="Coordination",
                severity="information"
            )
            
            # Step 2: Wait for service to signal it's idle (or timeout after 5 seconds)
            idle_file = Path(str(self.filename) + '.service_idle')
            max_wait = 5.0  # seconds
            wait_interval = 0.1  # seconds
            elapsed = 0.0
            
            import time
            while elapsed < max_wait:
                if idle_file.exists() or not self._service_is_running():
                    break
                time.sleep(wait_interval)
                elapsed += wait_interval
            
            # Step 3: Try to acquire exclusive lock
            self.lock_file = open(self.filename, 'r+')
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.notify(
                    "File locked for editing (service is paused)",
                    title="Lock Acquired",
                    severity="information"
                )
            except IOError:
                # File is already locked by another process
                self.notify(
                    "Warning: Another process may be using this file. Proceeding with caution.",
                    title="Lock Warning",
                    severity="warning",
                    timeout=10
                )
                # Close the file as we couldn't get exclusive lock
                self.lock_file.close()
                self.lock_file = None
                # Clean up coordination file
                try:
                    intent_file.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception as e:
            self.notify(
                f"Warning: Could not acquire file lock: {e}",
                title="Lock Error",
                severity="warning"
            )
            self.lock_file = None
            # Clean up coordination file
            try:
                intent_file = Path(str(self.filename) + '.editor_wants_lock')
                intent_file.unlink(missing_ok=True)
            except Exception:
                pass
        
        self.read_csv_to_table()
    
    def _service_is_running(self) -> bool:
        """Check if the TTSLO service is running."""
        try:
            import subprocess
            result = subprocess.run(
                ['systemctl', 'is-active', 'ttslo'],
                capture_output=True,
                text=True,
                timeout=1
            )
            return result.returncode == 0
        except Exception:
            # If we can't check, assume service might be running
            return True
    
    def on_unmount(self) -> None:
        """Called when the application is about to be unmounted."""
        # Release file lock if we have it
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Clean up coordination files
        try:
            intent_file = Path(str(self.filename) + '.editor_wants_lock')
            intent_file.unlink(missing_ok=True)
        except Exception:
            pass
        
        try:
            idle_file = Path(str(self.filename) + '.service_idle')
            idle_file.unlink(missing_ok=True)
        except Exception:
            pass

    def read_csv_to_table(self) -> None:
        """Read the CSV file and populate the DataTable."""
        if not self.filename.exists():
            self.notify(
                f"File not found: {self.filename}",
                title="Error",
                severity="error"
            )
            # Create an empty table with default headers
            table = self.query_one(DataTable)
            table.add_columns("Column1", "Column2", "Column3")
            self.data = [["Column1", "Column2", "Column3"]]
            return
            
        try:
            with open(self.filename, 'r', newline='') as f:
                reader = csv.reader(f)
                self.data = list(reader)
        except Exception as e:
            self.notify(
                f"Error reading file: {e}",
                title="Error",
                severity="error"
            )
            return

        table = self.query_one(DataTable)
        table.clear(columns=True)
        
        if not self.data:
            # Empty file - add default headers
            table.add_columns("Column1", "Column2", "Column3")
            self.data = [["Column1", "Column2", "Column3"]]
            return
            
        # First row is headers
        headers = self.data[0]
        rows = self.data[1:]
        
        # Add columns
        for header in headers:
            table.add_column(str(header), key=str(header))
        
        # Add rows
        for row in rows:
            # Ensure row has the same number of columns as headers
            while len(row) < len(headers):
                row.append("")
            row = row[:len(headers)]  # Trim if too long
            table.add_row(*row)
        
        self.notify(
            f"Loaded {len(rows)} rows from {self.filename.name}",
            title="File Loaded",
            severity="information"
        )

    @work(exclusive=True, group="file_ops", thread=True)
    def action_save_csv(self) -> None:
        """Save the DataTable content back to the CSV file."""
        table = self.query_one(DataTable)
        
        # Get data from the table
        headers = [str(col.label.plain) for col in table.columns.values()]
        
        # Get all rows
        rows = []
        for row_key in table.rows:
            row_data = []
            for col_key in table.columns:
                cell_value = table.get_cell(row_key, col_key)
                row_data.append(str(cell_value))
            rows.append(row_data)
        
        updated_data = [headers] + rows
        
        # Write to the CSV file
        try:
            with open(self.filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(updated_data)
            
            self.data = updated_data
            self.modified = False
            self.notify(
                f"File saved: {self.filename}",
                title="Saved",
                severity="information"
            )
        except Exception as e:
            self.notify(
                f"Failed to save: {e}",
                title="Error",
                severity="error"
            )
    
    def action_add_row(self) -> None:
        """Add a new empty row to the table."""
        table = self.query_one(DataTable)
        num_columns = len(table.columns)
        
        if num_columns == 0:
            self.notify(
                "Cannot add row: No columns defined",
                title="Error",
                severity="warning"
            )
            return
        
        # Create empty row with correct number of columns
        empty_row = [""] * num_columns
        table.add_row(*empty_row)
        self.modified = True
        
        self.notify(
            "New row added",
            title="Row Added",
            severity="information"
        )
    
    def action_delete_row(self) -> None:
        """Delete the currently selected row."""
        table = self.query_one(DataTable)
        
        if table.cursor_row is None:
            self.notify(
                "No row selected",
                title="Error",
                severity="warning"
            )
            return
        
        # Get the row key
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        
        # Check if this is the last row
        if len(table.rows) <= 1:
            self.notify(
                "Cannot delete the last row",
                title="Error",
                severity="warning"
            )
            return
        
        try:
            table.remove_row(row_key)
            self.modified = True
            self.notify(
                "Row deleted",
                title="Row Deleted",
                severity="information"
            )
        except Exception as e:
            self.notify(
                f"Failed to delete row: {e}",
                title="Error",
                severity="error"
            )
    
    def action_edit_cell(self) -> None:
        """Edit the currently selected cell."""
        table = self.query_one(DataTable)
        
        if table.cursor_coordinate is None:
            self.notify(
                "No cell selected",
                title="Error",
                severity="warning"
            )
            return
        
        # Get current cell value and column name
        try:
            cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
            current_value = str(table.get_cell_at(table.cursor_coordinate))
            
            # Get column name
            col_index = table.cursor_coordinate.column
            column_keys = list(table.columns.keys())
            if col_index < len(column_keys):
                column_key = column_keys[col_index]
                column_name = str(table.columns[column_key].label.plain)
            else:
                column_name = ""
            
            # Get row data for validation context
            row_key = cell_key.row_key
            row_data = {}
            for col_key in table.columns:
                col_name = str(table.columns[col_key].label.plain)
                row_data[col_name] = str(table.get_cell(row_key, col_key))
            
            # Get all IDs from the table for uniqueness check
            all_ids = set()
            id_column_key = None
            for col_key in table.columns:
                col_name = str(table.columns[col_key].label.plain)
                if col_name.lower() == 'id':
                    id_column_key = col_key
                    break
            
            if id_column_key:
                for row_key_iter in table.rows:
                    id_value = str(table.get_cell(row_key_iter, id_column_key))
                    if id_value:
                        all_ids.add(id_value)
                
        except Exception as e:
            log(f"Error getting cell value: {e}")
            current_value = ""
            column_name = ""
            row_data = {}
            all_ids = set()
        
        # Show edit screen
        def handle_edit_result(new_value: str | None) -> None:
            if new_value is not None:
                try:
                    table.update_cell_at(table.cursor_coordinate, new_value)
                    self.modified = True
                    self.notify(
                        "Cell updated",
                        title="Updated",
                        severity="information"
                    )
                except Exception as e:
                    self.notify(
                        f"Failed to update cell: {e}",
                        title="Error",
                        severity="error"
                    )
        
        self.push_screen(EditCellScreen(current_value, column_name, row_data, all_ids), handle_edit_result)


def main():
    """Main entry point for the CSV editor."""
    # Get filename from command line arguments or use smart default
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        # Use smart default that respects environment and service location
        filename = get_default_config_path()
        print(f"No file specified. Using default: {filename}")
        print(f"  (Set TTSLO_CONFIG_FILE environment variable to override)")
        print()
    
    # Check if file exists, if not, offer to create sample
    filepath = Path(filename)
    if not filepath.exists():
        print(f"File '{filename}' not found.")
        response = input("Would you like to create a sample config file? (y/n): ")
        if response.lower() == 'y':
            # Create parent directories if needed
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Create a sample config file
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                               'direction', 'volume', 'trailing_offset_percent', 'enabled'])
                writer.writerow(['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01000000', '5.0', 'true'])
                writer.writerow(['eth_1', 'XETHZUSD', '3000', 'above', 'sell', '0.10000000', '3.5', 'true'])
            print(f"Sample file created: {filepath}")
        else:
            print("Exiting without creating file.")
            sys.exit(0)
    
    # Run the app
    app = CSVEditor(filename=str(filepath))
    app.run()


if __name__ == "__main__":
    main()
