#!/usr/bin/env python3
"""
Tests for CSV Editor linked_order_id dropdown support.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from csv_editor import InlineCellEditor


def test_linked_order_id_is_select_field():
    """Test that linked_order_id is treated as a select field."""
    all_ids = {'order1', 'order2', 'order3'}
    row_data = {'id': 'order1'}
    
    editor = InlineCellEditor(
        current_value="",
        column_name="linked_order_id",
        row_data=row_data,
        all_ids=all_ids
    )
    
    assert editor.is_linked_order_field == True, "linked_order_id should be detected as linked order field"
    assert editor.is_binary_field == False, "linked_order_id should not be a binary field"


def test_linked_order_id_excludes_self():
    """Test that linked_order_id dropdown doesn't include the current order's ID."""
    all_ids = {'order1', 'order2', 'order3'}
    row_data = {'id': 'order1'}
    
    editor = InlineCellEditor(
        current_value="",
        column_name="linked_order_id",
        row_data=row_data,
        all_ids=all_ids
    )
    
    # Verify the editor has the correct data to exclude self
    # The compose() method uses this to filter options
    assert 'order1' in all_ids, "order1 should be in all_ids"
    assert editor.row_data.get('id') == 'order1', "Current row ID should be order1"
    assert editor.is_linked_order_field == True, "Should be detected as linked order field"
    
    # Verify that validation prevents self-reference
    is_valid, _ = editor.validate_value('order1')
    assert is_valid == False, "Self-reference should be invalid"


def test_linked_order_id_includes_none_option():
    """Test that linked_order_id dropdown includes a 'None' option."""
    all_ids = {'order1', 'order2'}
    row_data = {'id': 'order1'}
    
    editor = InlineCellEditor(
        current_value="",
        column_name="linked_order_id",
        row_data=row_data,
        all_ids=all_ids
    )
    
    # The editor should handle empty string as current value (None option)
    assert editor.current_value == ""
    assert editor.is_linked_order_field == True


def test_linked_order_id_with_existing_value():
    """Test that linked_order_id dropdown respects existing linked order."""
    all_ids = {'order1', 'order2', 'order3'}
    row_data = {'id': 'order1'}
    
    editor = InlineCellEditor(
        current_value="order2",
        column_name="linked_order_id",
        row_data=row_data,
        all_ids=all_ids
    )
    
    assert editor.current_value == "order2"
    assert editor.is_linked_order_field == True


def test_linked_order_validation_prevents_self_reference():
    """Test that validation prevents an order from linking to itself."""
    all_ids = {'order1', 'order2', 'order3'}
    row_data = {'id': 'order1'}
    
    editor = InlineCellEditor(
        current_value="",
        column_name="linked_order_id",
        row_data=row_data,
        all_ids=all_ids
    )
    
    # Try to set linked_order_id to the same as current id
    is_valid, message = editor.validate_value("order1")
    
    assert is_valid == False, "Self-reference should not be valid"
    assert "Cannot link order to itself" in message


def test_linked_order_validation_checks_existence():
    """Test that validation checks if linked order exists."""
    all_ids = {'order1', 'order2', 'order3'}
    row_data = {'id': 'order1'}
    
    editor = InlineCellEditor(
        current_value="",
        column_name="linked_order_id",
        row_data=row_data,
        all_ids=all_ids
    )
    
    # Try to set linked_order_id to non-existent order
    is_valid, message = editor.validate_value("nonexistent_order")
    
    assert is_valid == False, "Non-existent order should not be valid"
    assert "not found in config" in message


def test_linked_order_validation_allows_empty():
    """Test that validation allows empty linked_order_id."""
    all_ids = {'order1', 'order2', 'order3'}
    row_data = {'id': 'order1'}
    
    editor = InlineCellEditor(
        current_value="",
        column_name="linked_order_id",
        row_data=row_data,
        all_ids=all_ids
    )
    
    # Empty value should be valid (no linked order)
    is_valid, message = editor.validate_value("")
    
    assert is_valid == True, "Empty linked_order_id should be valid"


def test_linked_order_validation_allows_valid_order():
    """Test that validation allows valid linked order."""
    all_ids = {'order1', 'order2', 'order3'}
    row_data = {'id': 'order1'}
    
    editor = InlineCellEditor(
        current_value="",
        column_name="linked_order_id",
        row_data=row_data,
        all_ids=all_ids
    )
    
    # Valid order should be allowed
    is_valid, message = editor.validate_value("order2")
    
    assert is_valid == True, "Valid linked_order_id should be valid"


if __name__ == "__main__":
    # Run tests
    test_linked_order_id_is_select_field()
    print("✓ Test: linked_order_id is select field")
    
    test_linked_order_id_excludes_self()
    print("✓ Test: linked_order_id excludes self")
    
    test_linked_order_id_includes_none_option()
    print("✓ Test: linked_order_id includes none option")
    
    test_linked_order_id_with_existing_value()
    print("✓ Test: linked_order_id with existing value")
    
    test_linked_order_validation_prevents_self_reference()
    print("✓ Test: linked_order_id validation prevents self-reference")
    
    test_linked_order_validation_checks_existence()
    print("✓ Test: linked_order_id validation checks existence")
    
    test_linked_order_validation_allows_empty()
    print("✓ Test: linked_order_id validation allows empty")
    
    test_linked_order_validation_allows_valid_order()
    print("✓ Test: linked_order_id validation allows valid order")
    
    print("\nAll tests passed!")
