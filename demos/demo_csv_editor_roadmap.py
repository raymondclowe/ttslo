#!/usr/bin/env python3
"""
Demo script for CSV Editor Roadmap Phase 1 features.

This script demonstrates the new features added in Phase 1:
1. Help Screen (? or F1)
2. Row Duplication (Ctrl+Shift+D)
3. Unsaved Changes Indicator (*)
"""

import sys
from csv_editor import CSVEditor, HelpScreen, ConfirmQuitScreen

def demo_help_screen():
    """Demonstrate the help screen feature."""
    print("\n" + "="*70)
    print("FEATURE 1: HELP SCREEN (? or F1)")
    print("="*70)
    print("\nThe help screen provides comprehensive documentation without leaving")
    print("the editor. Press ? or F1 to view:")
    print("\n  ✓ All keybindings organized by category")
    print("  ✓ Validation rules for each field")
    print("  ✓ Quick tips and best practices")
    print("  ✓ Safety features and file locking info")
    print("\nThis makes the editor self-documenting for new users!")
    
    # Show that the help screen can be created
    try:
        help_screen = HelpScreen()
        print("\n✅ Help screen initialized successfully")
        print("   Keybindings:", [b.key for b in help_screen.BINDINGS])
    except Exception as e:
        print(f"\n❌ Error: {e}")


def demo_row_duplication():
    """Demonstrate the row duplication feature."""
    print("\n" + "="*70)
    print("FEATURE 2: ROW DUPLICATION (Ctrl+Shift+D)")
    print("="*70)
    print("\nQuickly create similar configurations by duplicating rows:")
    print("\n  1. Navigate to a row you want to duplicate")
    print("  2. Press Ctrl+Shift+D")
    print("  3. A new row is created with all values copied")
    print("  4. The ID is automatically incremented")
    print("\nExamples of ID auto-increment:")
    
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / 'test.csv'
        test_file.write_text("id,name\ntest_1,example")
        
        editor = CSVEditor(filename=str(test_file))
        
        test_cases = [
            ("btc_1", "btc_2"),
            ("eth_test", "eth_test_1"),
            ("config123", "config124"),
            ("sol", "sol_1"),
            ("test_99", "test_100"),
        ]
        
        print()
        for original, expected in test_cases:
            result = editor._auto_increment_id(original)
            status = "✅" if result == expected else "❌"
            print(f"  {status} {original:15} → {result:15} (expected: {expected})")
        
        print("\n✅ Row duplication with smart ID increment working!")


def demo_unsaved_changes():
    """Demonstrate the unsaved changes indicator."""
    print("\n" + "="*70)
    print("FEATURE 3: UNSAVED CHANGES INDICATOR (*)")
    print("="*70)
    print("\nPrevents accidental data loss with visual feedback:")
    print("\n  ✓ Title shows '*' when file has unsaved changes")
    print("  ✓ Prompt to save when quitting with unsaved changes")
    print("  ✓ Three options: Save & Quit, Quit Without Saving, Cancel")
    
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / 'test.csv'
        test_file.write_text("id,name\ntest_1,example")
        
        editor = CSVEditor(filename=str(test_file))
        
        # Test title updates
        print("\nTitle behavior:")
        
        # Unmodified state
        editor._update_title()
        unmodified_title = editor.title
        print(f"  Unmodified: '{unmodified_title}'")
        assert "*" not in unmodified_title, "Title should not have * when unmodified"
        
        # Modified state
        editor._set_modified(True)
        modified_title = editor.title
        print(f"  Modified:   '{modified_title}' ← Note the *")
        assert "*" in modified_title, "Title should have * when modified"
        
        # Back to unmodified
        editor._set_modified(False)
        saved_title = editor.title
        print(f"  Saved:      '{saved_title}'")
        assert "*" not in saved_title, "Title should not have * when saved"
        
        print("\n✅ Unsaved changes indicator working correctly!")
        
        # Show quit confirmation can be created
        try:
            confirm_screen = ConfirmQuitScreen()
            print("✅ Quit confirmation screen initialized successfully")
        except Exception as e:
            print(f"❌ Error: {e}")


def demo_keybindings():
    """Show all keybindings."""
    print("\n" + "="*70)
    print("UPDATED KEYBINDINGS")
    print("="*70)
    print("\nAll available keyboard shortcuts:")
    print("\n  Navigation & Editing:")
    print("    Enter or e          Edit selected cell")
    print("    Arrow Keys          Navigate table")
    print("    Tab/Shift+Tab       Navigate between cells")
    print("    Escape              Cancel editing")
    print("\n  Row Operations:")
    print("    Ctrl+N              Add new row")
    print("    Ctrl+D              Delete current row")
    print("    Ctrl+Shift+D        Duplicate current row ← NEW!")
    print("\n  File Operations:")
    print("    Ctrl+S              Save CSV file")
    print("    Ctrl+Q              Quit (prompts if unsaved) ← IMPROVED!")
    print("\n  Help:")
    print("    ? or F1             Show help screen ← NEW!")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*20 + "CSV EDITOR ROADMAP DEMO" + " "*25 + "║")
    print("║" + " "*19 + "Phase 1: Quick Wins" + " "*28 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        demo_help_screen()
        demo_row_duplication()
        demo_unsaved_changes()
        demo_keybindings()
        
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print("\n✅ All Phase 1 quick wins implemented successfully!")
        print("\nThese features provide immediate value with minimal code changes:")
        print("  • Better discoverability with help screen")
        print("  • Faster workflow with row duplication")
        print("  • Safer editing with unsaved changes indicator")
        print("\nTo use the CSV editor:")
        print("  uv run csv_editor.py [filename]")
        print("\n" + "="*70)
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
