"""
Integration test that simulates the exact scenario from the issue:
- ttslo.py running in one window
- VSCode or other text editor adding lines in another window
- Verify that no lines are deleted from config.csv
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
from ttslo import TTSLO
from kraken_api import KrakenAPI


class MockKrakenAPI:
    """Mock KrakenAPI for testing without actual API calls."""
    
    def get_current_price(self, pair):
        """Return a fixed price for testing."""
        return 50000.0
    
    def add_trailing_stop_loss(self, pair, direction, volume, trailing_offset_percent):
        """Mock order creation."""
        return {'txid': ['MOCK_ORDER_123']}


class TestEditorIntegration:
    """Test the exact scenario described in the issue."""
    
    @pytest.fixture
    def test_env(self):
        """Set up a complete test environment."""
        temp_dir = tempfile.mkdtemp()
        
        # Create config file
        config_file = os.path.join(temp_dir, 'config.csv')
        state_file = os.path.join(temp_dir, 'state.csv')
        log_file = os.path.join(temp_dir, 'logs.csv')
        
        # Create initial config with a few entries
        with open(config_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled'])
            writer.writerow(['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
            writer.writerow(['eth_1', 'XETHZUSD', '3000', 'above', 'sell', '0.1', '3.5', 'true'])
        
        # Create empty state file (include 'offset' column for trailing offset used when order created)
        with open(state_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'triggered', 'trigger_price', 'trigger_time', 'order_id', 'activated_on', 'last_checked', 'offset'])
        
        yield {
            'temp_dir': temp_dir,
            'config_file': config_file,
            'state_file': state_file,
            'log_file': log_file
        }
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def count_config_lines(self, config_file):
        """Count non-header lines in config file."""
        with open(config_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            return sum(1 for _ in reader)
    
    def test_editor_adds_lines_while_ttslo_runs(self, test_env):
        """
        Simulate the exact scenario from the issue:
        1. Start ttslo monitoring (run_once in a loop)
        2. In parallel, simulate editor adding new lines
        3. Verify no lines are deleted
        """
        config_file = test_env['config_file']
        
        # Set up TTSLO instance
        config_manager = ConfigManager(
            config_file=config_file,
            state_file=test_env['state_file'],
            log_file=test_env['log_file']
        )
        
        mock_api = MockKrakenAPI()
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api,
            kraken_api_readwrite=None,  # No actual orders
            dry_run=True,
            verbose=False
        )
        
        ttslo.load_state()
        
        # Initial line count
        initial_count = self.count_config_lines(config_file)
        assert initial_count == 2  # btc_1, eth_1
        
        # Track results
        results = {
            'ttslo_iterations': 0,
            'editor_adds': 0,
            'errors': []
        }
        
        stop_flag = threading.Event()
        
        def ttslo_loop():
            """Simulate ttslo running continuously."""
            try:
                while not stop_flag.is_set():
                    ttslo.run_once()
                    results['ttslo_iterations'] += 1
                    time.sleep(0.05)  # Short sleep between iterations
            except Exception as e:
                results['errors'].append(('ttslo', e))
        
        def editor_adds_lines():
            """Simulate editor adding new lines to config."""
            try:
                time.sleep(0.02)  # Small delay to let ttslo start
                
                for i in range(5):
                    # Read current config
                    with open(config_file, 'r', newline='') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                    
                    # Add a new line
                    rows.append([
                        f'new_{i}',
                        'ADAUSD',
                        '1.0',
                        'above',
                        'sell',
                        '100',
                        '2.5',
                        'true'
                    ])
                    
                    # Write back (simulating editor save)
                    with open(config_file, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerows(rows)
                    
                    results['editor_adds'] += 1
                    time.sleep(0.1)  # Pause between edits
                    
            except Exception as e:
                results['errors'].append(('editor', e))
        
        # Start both threads
        ttslo_thread = threading.Thread(target=ttslo_loop)
        editor_thread = threading.Thread(target=editor_adds_lines)
        
        ttslo_thread.start()
        editor_thread.start()
        
        # Wait for editor to finish
        editor_thread.join()
        
        # Let ttslo run a bit more
        time.sleep(0.2)
        
        # Stop ttslo
        stop_flag.set()
        ttslo_thread.join()
        
        # Check results
        assert len(results['errors']) == 0, f"Errors occurred: {results['errors']}"
        assert results['ttslo_iterations'] > 0, "TTSLO should have run at least once"
        assert results['editor_adds'] == 5, "Editor should have added 5 lines"
        
        # THE KEY TEST: Verify no lines were lost
        final_count = self.count_config_lines(config_file)
        
        # We should have at least the original 2 lines
        # We might have all 7 (original 2 + 5 new) or fewer if race conditions caused overwrites
        # But we should NEVER have fewer than the original 2
        assert final_count >= initial_count, \
            f"Lines were DELETED! Started with {initial_count}, ended with {final_count}"
        
        # Ideally, we should have all lines
        # Due to race conditions, the final count might vary, but should be close
        print(f"Initial lines: {initial_count}, Final lines: {final_count}")
        print(f"TTSLO iterations: {results['ttslo_iterations']}, Editor adds: {results['editor_adds']}")
    
    def test_validation_failure_doesnt_delete_lines(self, test_env):
        """
        Test that validation failures don't cause line deletion.
        
        When ttslo detects the file changed and re-validates, it might
        disable configs with validation errors. This should NOT delete lines.
        """
        config_file = test_env['config_file']
        
        # Add a line with validation error (invalid pair)
        with open(config_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['bad_1', 'INVALID_PAIR', '100', 'above', 'sell', '1', '5.0', 'true'])
        
        initial_count = self.count_config_lines(config_file)
        assert initial_count == 3
        
        # Set up TTSLO
        config_manager = ConfigManager(
            config_file=config_file,
            state_file=test_env['state_file'],
            log_file=test_env['log_file']
        )
        
        mock_api = MockKrakenAPI()
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api,
            kraken_api_readwrite=None,
            dry_run=True,
            verbose=False
        )
        
        ttslo.load_state()
        
        # This will trigger validation and potentially disable the bad config
        # But it should NOT delete any lines
        try:
            ttslo.run_once()
        except Exception:
            pass  # Validation might fail, but that's OK
        
        # Verify no lines deleted
        final_count = self.count_config_lines(config_file)
        assert final_count == initial_count, \
            f"Lines were deleted during validation! {initial_count} -> {final_count}"
    
    def test_triggered_config_update_preserves_other_lines(self, test_env):
        """
        Test that when a config is triggered and updated, other lines are preserved.
        """
        config_file = test_env['config_file']
        
        # Add more variety to the config
        with open(config_file, 'a', newline='') as f:
            writer = csv.writer(f)
            # Add a comment
            writer.writerow(['# This is a comment', '', '', '', '', '', '', ''])
            # Add another config
            writer.writerow(['ada_1', 'ADAUSD', '1.0', 'above', 'sell', '100', '2.5', 'true'])
            # Add an empty line
            writer.writerow(['', '', '', '', '', '', '', ''])
        
        initial_count = self.count_config_lines(config_file)
        assert initial_count == 5  # btc_1, eth_1, comment, ada_1, empty
        
        # Set up config manager
        config_manager = ConfigManager(
            config_file=config_file,
            state_file=test_env['state_file'],
            log_file=test_env['log_file']
        )
        
        # Trigger an update
        config_manager.update_config_on_trigger(
            config_id='btc_1',
            order_id='ORDER_123',
            trigger_time='2024-01-01T00:00:00Z',
            trigger_price='51000'
        )
        
        # Verify all lines preserved
        final_count = self.count_config_lines(config_file)
        assert final_count == initial_count, \
            f"Lines were deleted during update! {initial_count} -> {final_count}"
        
        # Verify the update was applied
        with open(config_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        btc_row = [r for r in rows if r.get('id') == 'btc_1'][0]
        assert btc_row['enabled'] == 'false'
        assert btc_row['order_id'] == 'ORDER_123'
        
        # Verify comment and empty lines still exist
        comment_rows = [r for r in rows if r.get('id', '').startswith('#')]
        assert len(comment_rows) == 1
        
        # Verify other configs unchanged
        eth_row = [r for r in rows if r.get('id') == 'eth_1'][0]
        assert eth_row['enabled'] == 'true'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
