#!/usr/bin/env python3
"""
Test script to verify the nonce generator works across multiple processes.

This simulates the Docker scenario where ttslo.py and dashboard.py run as
separate processes and both make API calls to Kraken.
"""
import multiprocessing
import time
import os
import sys
import tempfile

# Add current directory to path so we can import kraken_api
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kraken_api import NonceGenerator


def generate_nonces_in_process(process_id, count, nonce_file, result_queue):
    """Generate nonces in a separate process."""
    generator = NonceGenerator(nonce_file=nonce_file)
    nonces = []
    
    print(f"Process {process_id}: Starting to generate {count} nonces")
    
    for i in range(count):
        nonce = generator.generate()
        nonces.append(int(nonce))
        # NO DELAY - test for race conditions by generating as fast as possible
    
    print(f"Process {process_id}: Generated {count} nonces, range {min(nonces)} to {max(nonces)}")
    result_queue.put((process_id, nonces))


def test_multiprocess_nonces():
    """Test that nonces are unique across multiple processes."""
    print("=" * 60)
    print("Multi-Process Nonce Generator Test")
    print("=" * 60)
    
    # Create a temporary nonce file that all processes will share
    nonce_file = os.path.join(tempfile.gettempdir(), f'test_kraken_nonce_{os.getpid()}.txt')
    
    # Clean up any existing file
    if os.path.exists(nonce_file):
        os.remove(nonce_file)
    
    print(f"Using shared nonce file: {nonce_file}\n")
    
    # Create a queue to collect results from processes
    result_queue = multiprocessing.Queue()
    
    # Spawn multiple processes (simulating ttslo.py and dashboard.py)
    num_processes = 3
    nonces_per_process = 50  # Increased to stress test more thoroughly
    
    print(f"Spawning {num_processes} processes, each generating {nonces_per_process} nonces...")
    print("This simulates ttslo.py and dashboard.py running simultaneously")
    print("NO delays between nonce generation to test race conditions\n")
    
    processes = []
    start_time = time.time()
    
    for i in range(num_processes):
        p = multiprocessing.Process(
            target=generate_nonces_in_process,
            args=(i, nonces_per_process, nonce_file, result_queue)
        )
        processes.append(p)
        p.start()
        # NO stagger - start all at once to maximize contention
    
    # Wait for all processes to complete
    for p in processes:
        p.join()
    
    elapsed = time.time() - start_time
    
    # Collect all nonces from all processes
    all_nonces = []
    process_results = {}
    
    while not result_queue.empty():
        process_id, nonces = result_queue.get()
        process_results[process_id] = nonces
        all_nonces.extend(nonces)
    
    # Analyze results
    print("\n" + "=" * 60)
    print("Results:")
    print("=" * 60)
    
    total_nonces = len(all_nonces)
    unique_nonces = len(set(all_nonces))
    duplicates = total_nonces - unique_nonces
    
    print(f"Total nonces generated: {total_nonces}")
    print(f"Unique nonces: {unique_nonces}")
    print(f"Duplicates: {duplicates}")
    print(f"Time elapsed: {elapsed:.3f}s")
    
    # Check monotonic increase
    sorted_nonces = sorted(all_nonces)
    is_monotonic = all(sorted_nonces[i] < sorted_nonces[i+1] 
                       for i in range(len(sorted_nonces)-1))
    
    print(f"Monotonically increasing: {is_monotonic}")
    print(f"Nonce range: {min(all_nonces)} to {max(all_nonces)}")
    print(f"Nonce spread: {max(all_nonces) - min(all_nonces):,}")
    
    # Show per-process statistics
    print("\nPer-Process Results:")
    for process_id in sorted(process_results.keys()):
        nonces = process_results[process_id]
        print(f"  Process {process_id}: {len(nonces)} nonces, "
              f"range {min(nonces):,} to {max(nonces):,}")
    
    # Check for duplicates
    if duplicates > 0:
        print("\n✗ FAILURE: Found duplicate nonces!")
        from collections import Counter
        counts = Counter(all_nonces)
        duplicate_nonces = {n: count for n, count in counts.items() if count > 1}
        print(f"  Duplicate nonces: {list(duplicate_nonces.items())[:5]}")
        success = False
    else:
        print("\n✓ SUCCESS: All nonces are unique across processes!")
        success = True
    
    # Clean up
    try:
        os.remove(nonce_file)
        print(f"\nCleaned up temporary nonce file: {nonce_file}")
    except OSError:
        pass
    
    return success


if __name__ == "__main__":
    success = test_multiprocess_nonces()
    sys.exit(0 if success else 1)
