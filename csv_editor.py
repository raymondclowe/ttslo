#!/usr/bin/env python3
"""
CSV Editor - A Textual TUI application for editing CSV files.

This is a standalone application that provides an interactive text-based
user interface for viewing and editing CSV files, specifically designed
for editing the TTSLO configuration files.

Usage:
    python csv_editor.py [filename]
    
If no filename is provided, it defaults to 'config.csv'.

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
        
        # Validate direction
        elif column_lower == "direction":
            valid_directions = ["buy", "sell"]
            if value.lower() not in valid_directions:
                return (False, f"Must be 'buy' or 'sell'")
        
        # Validate enabled
        elif column_lower == "enabled":
            valid_enabled = ["true", "false", "yes", "no", "1", "0"]
            if value.lower() not in valid_enabled:
                return (False, f"Must be true/false, yes/no, or 1/0")
        
        # Validate pair
        elif column_lower == "pair":
            known_pairs = {
                'XXBTZUSD', 'XBTCUSD', 'XXBTZEUR', 'XXBTZGBP', 'XXBTZJPY',
                'XETHZUSD', 'ETHCUSD', 'XETHZEUR', 'XETHZGBP', 'XETHZJPY',
                'SOLUSD', 'SOLEUR', 'SOLGBP',
                'ADAUSD', 'ADAEUR', 'ADAGBP',
                'DOTUSD', 'DOTEUR', 'DOTGBP',
                'AVAXUSD', 'AVAXEUR',
                'LINKUSD', 'LINKEUR',
                'USDTUSD', 'USDCUSD', 'DAIUSD',
                'XBTCZUSD', 'ETHZUSD',
            }
            if value.upper() not in known_pairs:
                # Treat unknown trading pair as invalid input to prevent accidental bad configs
                return (False, f"Invalid trading pair: '{value}'. Use Kraken pair codes like XXBTZUSD or XETHZUSD")
        
        
        return (True, "")
    
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
            elif message:  # Warning message
                # Show warning but allow save
                validation_label = self.query_one("#validation-message", Label)
                validation_label.update(message)
            
            self.dismiss(value)
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
        
        self.dismiss(event.value)


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
        self.read_csv_to_table()

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
    # Get filename from command line arguments
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "config.csv"
    
    # Check if file exists, if not, offer to create sample
    filepath = Path(filename)
    if not filepath.exists():
        print(f"File '{filename}' not found.")
        response = input("Would you like to create a sample config file? (y/n): ")
        if response.lower() == 'y':
            # Create a sample config file
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                               'direction', 'volume', 'trailing_offset_percent', 'enabled'])
                writer.writerow(['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
                writer.writerow(['eth_1', 'XETHZUSD', '3000', 'above', 'sell', '0.1', '3.5', 'true'])
            print(f"Sample file created: {filepath}")
        else:
            print("Exiting without creating file.")
            sys.exit(0)
    
    # Run the app
    app = CSVEditor(filename=str(filepath))
    app.run()


if __name__ == "__main__":
    main()
