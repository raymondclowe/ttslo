#!/usr/bin/env python3
"""
Tests for TTL-based stale editor intent file handling.
"""
import os
import time
import tempfile
import csv
from pathlib import Path
import sys

# Add repo to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ConfigManager


def test_primary_intent_file_ttl_cleanup():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        # create config file
        with open(config_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id'])

        cm = ConfigManager(config_file=config_file)
        # set small TTL
        cm.editor_intent_ttl = 1  # 1 second

        intent_file = config_file + '.editor_wants_lock'
        Path(intent_file).touch()
        # make mtime old
        old_time = time.time() - 10
        os.utime(intent_file, (old_time, old_time))

        # check coordination: should remove stale file and return False
        assert not cm.check_editor_coordination(), "Stale primary intent file should be cleaned up"
        assert not os.path.exists(intent_file), "Primary intent file should be removed by TTL cleanup"


def test_fallback_intent_file_ttl_cleanup():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        # create config file
        with open(config_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id'])

        cm = ConfigManager(config_file=config_file)
        cm.editor_intent_ttl = 1

        # Create fallback file in tmp
        tmpdir_sys = tempfile.gettempdir()
        fallback = os.path.join(tmpdir_sys, f'ttslo_editor_wants_lock.testttl.{os.getuid()}.config')
        with open(fallback, 'w') as f:
            f.write(config_file)
        # make it stale
        old_time = time.time() - 10
        os.utime(fallback, (old_time, old_time))

        # Now call check; it should remove the fallback file and return False
        assert not cm.check_editor_coordination(), "Stale fallback file should be cleaned up"
        assert not os.path.exists(fallback), "Fallback intent file should be removed by TTL cleanup"


if __name__ == '__main__':
    test_primary_intent_file_ttl_cleanup()
    test_fallback_intent_file_ttl_cleanup()
    print('TTL coordination tests passed')
