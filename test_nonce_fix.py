#!/usr/bin/env python3
"""
Test script to verify the nonce generator fix works correctly.

This simulates concurrent API calls to ensure no nonce collisions occur.
"""
import threading
import time
from kraken_api import NonceGenerator


def test_nonce_uniqueness():
    """Test that nonces are unique even under concurrent access."""
    print("Testing nonce uniqueness under concurrent access...")
    
    generator = NonceGenerator()
    nonces = []
    lock = threading.Lock()
    
    def generate_nonces(count=100):
        """Generate nonces in a thread."""
        local_nonces = []
        for _ in range(count):
            nonce = generator.generate()
            local_nonces.append(nonce)
            # Simulate some processing time
            time.sleep(0.0001)
        
        with lock:
            nonces.extend(local_nonces)
    
    # Spawn multiple threads to simulate concurrent API calls
    threads = []
    num_threads = 10
    nonces_per_thread = 50
    
    print(f"Spawning {num_threads} threads, each generating {nonces_per_thread} nonces...")
    start = time.time()
    
    for _ in range(num_threads):
        thread = threading.Thread(target=generate_nonces, args=(nonces_per_thread,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    elapsed = time.time() - start
    
    # Check results
    total_nonces = len(nonces)
    unique_nonces = len(set(nonces))
    
    print(f"\nResults:")
    print(f"  Total nonces generated: {total_nonces}")
    print(f"  Unique nonces: {unique_nonces}")
    print(f"  Duplicates: {total_nonces - unique_nonces}")
    print(f"  Time elapsed: {elapsed:.3f}s")
    
    # Verify monotonic increase
    sorted_nonces = [int(n) for n in nonces]
    sorted_nonces.sort()
    is_monotonic = all(sorted_nonces[i] < sorted_nonces[i+1] 
                       for i in range(len(sorted_nonces)-1))
    
    print(f"  Monotonically increasing: {is_monotonic}")
    print(f"  First nonce: {sorted_nonces[0]}")
    print(f"  Last nonce: {sorted_nonces[-1]}")
    
    if unique_nonces == total_nonces:
        print("\n✓ SUCCESS: All nonces are unique!")
        return True
    else:
        print("\n✗ FAILURE: Found duplicate nonces!")
        # Find and display duplicates
        from collections import Counter
        counts = Counter(nonces)
        duplicates = {n: count for n, count in counts.items() if count > 1}
        print(f"  Duplicate nonces: {duplicates}")
        return False


def test_nonce_format():
    """Test that nonces are in the correct format for Kraken API."""
    print("\nTesting nonce format...")
    
    generator = NonceGenerator()
    nonce = generator.generate()
    
    print(f"  Generated nonce: {nonce}")
    print(f"  Type: {type(nonce)}")
    print(f"  Length: {len(nonce)} characters")
    
    # Verify it's a string of digits
    is_valid = nonce.isdigit() and len(nonce) >= 10
    
    if is_valid:
        print("\n✓ SUCCESS: Nonce format is valid!")
        return True
    else:
        print("\n✗ FAILURE: Invalid nonce format!")
        return False


def test_rapid_generation():
    """Test rapid nonce generation without any delays."""
    print("\nTesting rapid nonce generation...")
    
    generator = NonceGenerator()
    nonces = []
    count = 1000
    
    start = time.time()
    for _ in range(count):
        nonces.append(generator.generate())
    elapsed = time.time() - start
    
    unique_nonces = len(set(nonces))
    
    print(f"  Generated {count} nonces in {elapsed:.3f}s")
    print(f"  Rate: {count/elapsed:.0f} nonces/sec")
    print(f"  Unique: {unique_nonces}/{count}")
    
    if unique_nonces == count:
        print("\n✓ SUCCESS: All rapid nonces are unique!")
        return True
    else:
        print("\n✗ FAILURE: Found duplicate nonces in rapid generation!")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Nonce Generator Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Format Test", test_nonce_format()))
    results.append(("Rapid Generation Test", test_rapid_generation()))
    results.append(("Concurrent Access Test", test_nonce_uniqueness()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        exit(0)
    else:
        print("\n✗ Some tests failed!")
        exit(1)
