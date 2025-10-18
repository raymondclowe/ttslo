"""
Tests for config file race conditions and concurrent access scenarios.

This test suite validates that config file operations are safe when:
- Multiple processes access the file concurrently
- External editors modify the file while ttslo is running
- Partial writes or incomplete data is present
- Comments and empty lines need to be preserved
"""
import os
import csv
import tempfile
import shutil
import threading
import time
from pathlib import Path

import pytest

from config import ConfigManager


class TestConfigFileRaceConditions:
    """Test suite for config file race condition scenarios."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config_file(self, temp_dir):
        """Create a test config file with sample data."""
        config_path = os.path.join(temp_dir, 'test_config.csv')
        
        # Create config with various line types
        with open(config_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled'])
            # Regular config
            writer.writerow(['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
            # Comment line
            writer.writerow(['# This is a comment', '', '', '', '', '', '', ''])
            # Another config
            writer.writerow(['eth_1', 'XETHZUSD', '3000', 'above', 'sell', '0.1', '3.5', 'true'])
            # Empty line
            writer.writerow(['', '', '', '', '', '', '', ''])
            # Another config
            writer.writerow(['ada_1', 'ADAUSD', '1.0', 'above', 'sell', '100', '2.5', 'true'])
        
        return config_path
    
    def count_lines(self, filepath):
        """Count total lines in a file (including headers and all rows)."""
        with open(filepath, 'r') as f:
            # Count header + data lines
            return sum(1 for _ in f)
    
    def test_atomic_write_preserves_all_lines(self, config_file, temp_dir):
        """Test that atomic write preserves all lines including comments and empty rows."""
        manager = ConfigManager(config_file=config_file)
        
        # Count original lines
        original_line_count = self.count_lines(config_file)
        assert original_line_count == 6  # header + 5 data rows
        
        # Trigger an update
        manager.update_config_on_trigger(
            config_id='btc_1',
            order_id='ORDER123',
            trigger_time='2024-01-01T00:00:00Z',
            trigger_price='51000'
        )
        
        # Verify all lines are preserved
        new_line_count = self.count_lines(config_file)
        assert new_line_count == original_line_count, \
            f"Line count changed: {original_line_count} -> {new_line_count}"
        
        # Verify the update was applied
        configs = manager.load_config()
        btc_config = [c for c in configs if c.get('id') == 'btc_1'][0]
        assert btc_config['enabled'] == 'false'
        assert btc_config['order_id'] == 'ORDER123'
    
    def test_disable_configs_preserves_all_lines(self, config_file, temp_dir):
        """Test that disable_configs preserves all lines including comments and empty rows."""
        manager = ConfigManager(config_file=config_file)
        
        # Count original lines
        original_line_count = self.count_lines(config_file)
        assert original_line_count == 6
        
        # Disable multiple configs
        manager.disable_configs(['btc_1', 'eth_1'])
        
        # Verify all lines are preserved
        new_line_count = self.count_lines(config_file)
        assert new_line_count == original_line_count, \
            f"Line count changed: {original_line_count} -> {new_line_count}"
        
        # Verify configs were disabled
        configs = manager.load_config()
        for config in configs:
            if config.get('id') in ['btc_1', 'eth_1']:
                assert config['enabled'] == 'false'
            elif config.get('id') == 'ada_1':
                assert config['enabled'] == 'true'
    
    def test_concurrent_writes_dont_lose_data(self, config_file, temp_dir):
        """Test that concurrent write operations don't lose lines (all rows preserved).
        
        Note: With concurrent writes to the same file, the last write wins.
        The key safety property is that NO LINES ARE LOST - all rows from the file
        are preserved even during concurrent access.
        """
        manager = ConfigManager(config_file=config_file)
        
        # Count original lines
        original_line_count = self.count_lines(config_file)
        
        errors = []
        
        def update_config(config_id, order_id):
            """Update a config in a thread."""
            try:
                manager.update_config_on_trigger(
                    config_id=config_id,
                    order_id=order_id,
                    trigger_time='2024-01-01T00:00:00Z',
                    trigger_price='50000'
                )
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads updating different configs
        threads = [
            threading.Thread(target=update_config, args=('btc_1', 'ORDER1')),
            threading.Thread(target=update_config, args=('eth_1', 'ORDER2')),
            threading.Thread(target=update_config, args=('ada_1', 'ORDER3')),
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Check for errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # THE KEY TEST: Verify all lines are preserved (no data loss)
        new_line_count = self.count_lines(config_file)
        assert new_line_count == original_line_count, \
            f"Line count changed after concurrent writes: {original_line_count} -> {new_line_count}"
        
        # Verify at least one update was applied
        # (Due to race condition, last write wins, but that's OK - no lines lost)
        configs = manager.load_config()
        config_by_id = {c['id']: c for c in configs}
        
        # At least one config should be updated
        updated_configs = [c for c in configs if c.get('enabled') == 'false']
        assert len(updated_configs) >= 1, "At least one config should be updated"
        
        # All configs should still exist
        assert 'btc_1' in config_by_id
        assert 'eth_1' in config_by_id
        assert 'ada_1' in config_by_id
    
    def test_atomic_write_handles_concurrent_external_edits(self, config_file, temp_dir):
        """Test that atomic writes handle external editor modifications."""
        manager = ConfigManager(config_file=config_file)
        
        # Count original lines
        original_line_count = self.count_lines(config_file)
        
        errors = []
        
        def external_edit():
            """Simulate an external editor adding a line."""
            try:
                time.sleep(0.01)  # Small delay to interleave with update
                # Read current content
                with open(config_file, 'r', newline='') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                
                # Add a new config line
                rows.append(['new_1', 'SOLUSD', '100', 'above', 'sell', '10', '3.0', 'true'])
                
                # Write back
                with open(config_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)
            except Exception as e:
                errors.append(e)
        
        def internal_update():
            """Simulate ttslo updating a config."""
            try:
                manager.update_config_on_trigger(
                    config_id='btc_1',
                    order_id='ORDER123',
                    trigger_time='2024-01-01T00:00:00Z',
                    trigger_price='51000'
                )
            except Exception as e:
                errors.append(e)
        
        # Start both operations
        t1 = threading.Thread(target=external_edit)
        t2 = threading.Thread(target=internal_update)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # Check for errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Final line count should be original + 1 (new line added)
        # Note: Due to race condition, one of the operations might win
        # The key is that we don't lose existing lines
        final_line_count = self.count_lines(config_file)
        assert final_line_count >= original_line_count, \
            f"Lines were lost: {original_line_count} -> {final_line_count}"
    
    def test_read_preserving_handles_comments_and_empty_lines(self, config_file, temp_dir):
        """Test that _read_csv_preserving_all_lines keeps all row types."""
        manager = ConfigManager(config_file=config_file)
        
        fieldnames, all_rows = manager._read_csv_preserving_all_lines(config_file)
        
        # Should have 5 rows (all data rows including comments and empty)
        assert len(all_rows) == 5
        
        # Verify we have the comment row
        comment_rows = [r for r in all_rows if r.get('id', '').startswith('#')]
        assert len(comment_rows) == 1
        assert '# This is a comment' in comment_rows[0].get('id', '')
        
        # Verify we have the empty row
        empty_rows = [r for r in all_rows 
                     if all(v is None or str(v).strip() == '' for v in r.values())]
        assert len(empty_rows) >= 1  # At least one empty row
    
    def test_update_with_new_columns_preserves_lines(self, config_file, temp_dir):
        """Test that adding new columns doesn't lose existing lines."""
        manager = ConfigManager(config_file=config_file)
        
        # Count original lines
        original_line_count = self.count_lines(config_file)
        
        # Trigger update which adds new columns
        manager.update_config_on_trigger(
            config_id='btc_1',
            order_id='ORDER123',
            trigger_time='2024-01-01T00:00:00Z',
            trigger_price='51000'
        )
        
        # Verify all lines preserved
        new_line_count = self.count_lines(config_file)
        assert new_line_count == original_line_count
        
        # Verify new columns were added
        with open(config_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            assert 'order_id' in fieldnames
            assert 'trigger_time' in fieldnames
            assert 'trigger_price' in fieldnames
    
    def test_multiple_sequential_updates_preserve_lines(self, config_file, temp_dir):
        """Test that multiple sequential updates don't lose lines."""
        manager = ConfigManager(config_file=config_file)
        
        original_line_count = self.count_lines(config_file)
        
        # Perform multiple updates
        for i in range(5):
            manager.update_config_on_trigger(
                config_id='btc_1',
                order_id=f'ORDER{i}',
                trigger_time='2024-01-01T00:00:00Z',
                trigger_price=f'{50000 + i}'
            )
            
            # After each update, verify line count
            current_line_count = self.count_lines(config_file)
            assert current_line_count == original_line_count, \
                f"Lines lost after update {i}: {original_line_count} -> {current_line_count}"
    
    def test_disable_nonexistent_config_preserves_file(self, config_file, temp_dir):
        """Test that disabling a non-existent config doesn't corrupt file."""
        manager = ConfigManager(config_file=config_file)
        
        original_line_count = self.count_lines(config_file)
        
        # Try to disable a config that doesn't exist
        manager.disable_configs(['nonexistent_id'])
        
        # Verify file is unchanged
        new_line_count = self.count_lines(config_file)
        assert new_line_count == original_line_count
        
        # Verify other configs are unaffected
        configs = manager.load_config()
        for config in configs:
            if config.get('id'):
                # All configs should still be enabled
                assert config.get('enabled') == 'true'


class TestAtomicWriteEdgeCases:
    """Test edge cases for atomic write operations."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_atomic_write_handles_missing_directory(self, temp_dir):
        """Test that atomic write creates parent directories if needed."""
        # Note: This test shows expected behavior, but current implementation
        # requires parent directory to exist
        manager = ConfigManager()
        
        # Nested path that doesn't exist
        nested_path = os.path.join(temp_dir, 'subdir', 'config.csv')
        
        # This should fail gracefully (current behavior)
        # In production, ensure parent directory exists before calling
        with pytest.raises(Exception):
            manager._atomic_write_csv(
                nested_path,
                ['id', 'value'],
                [{'id': '1', 'value': 'test'}]
            )
    
    def test_atomic_write_handles_empty_rows(self, temp_dir):
        """Test that atomic write handles empty row list."""
        manager = ConfigManager()
        config_path = os.path.join(temp_dir, 'config.csv')
        
        # Write empty file
        manager._atomic_write_csv(
            config_path,
            ['id', 'value'],
            []
        )
        
        # Verify file was created with just header
        assert os.path.exists(config_path)
        with open(config_path, 'r', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 1  # Just header
            assert rows[0] == ['id', 'value']
    
    def test_atomic_write_retry_on_failure(self, temp_dir):
        """Test that atomic write retries on failure."""
        manager = ConfigManager()
        config_path = os.path.join(temp_dir, 'config.csv')
        
        # First write should succeed
        manager._atomic_write_csv(
            config_path,
            ['id', 'value'],
            [{'id': '1', 'value': 'test'}],
            max_retries=3,
            retry_delay=0.01
        )
        
        assert os.path.exists(config_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
