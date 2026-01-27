# Multi-Process Nonce Collision Fix

## Problem
The `EAPI:Invalid nonce` errors persisted after issue #216's fix because that fix only addressed **thread safety within a single process**. 

In your Docker setup, **two separate Python processes** run simultaneously:
1. `ttslo.py` - The monitoring service that checks and triggers orders
2. `dashboard.py` - The Flask web dashboard

Each process creates its own `KrakenAPI` instance with its own `NonceGenerator`. Since Python's `threading.Lock()` only works within a single process, nonces could still collide when both processes made API calls at the same time.

## Solution
Enhanced the `NonceGenerator` class to use **file-based synchronization** that works across processes:

### How It Works
1. **Shared nonce file**: `/tmp/kraken_nonce.txt` 
   - Both processes read from and write to this same file
   - Located in /tmp (usually tmpfs on Linux, so it's fast)

2. **File locking**: Uses `fcntl.flock(LOCK_EX)` for atomic operations
   - When a process wants to generate a nonce, it:
     - Acquires exclusive lock on the file
     - Reads the last nonce
     - Calculates new nonce = max(current_time, memory_nonce, file_nonce) + 1
     - Writes new nonce to file
     - Releases lock (automatic on file close)

3. **Thread safety maintained**: Still uses `threading.Lock()` for in-process synchronization

### Key Features
- ✅ Works across multiple processes
- ✅ Maintains thread safety within each process
- ✅ Monotonically increasing nonces guaranteed
- ✅ Fallback to in-memory if file operations fail
- ✅ No configuration needed - works automatically
- ✅ No external dependencies (uses standard fcntl module)

## Testing Results
All tests pass:
- **Multi-process test**: 3 processes generating 60 nonces - all unique ✅
- **Threading test**: 10 threads generating 500 nonces - all unique ✅
- **API tests**: All 25 kraken_api tests pass ✅
- **Security scan**: CodeQL found 0 vulnerabilities ✅

## Performance Impact
- **Before**: ~1.3M nonces/sec (in-memory only)
- **After**: ~2.6K nonces/sec (with file I/O)
- **Verdict**: Still more than sufficient since Kraken API is rate-limited

## What Changed
### Files Modified
- `kraken_api.py`: Enhanced NonceGenerator with file-based synchronization
- `test_multiprocess_nonce.py`: New test for multi-process scenarios
- `LEARNINGS.md`: Detailed documentation of the fix

### Deployment
No changes needed! The fix:
- Works automatically in your existing Docker setup
- Creates the nonce file on first use
- Doesn't require any environment variables or configuration
- Is backward compatible with existing code

## Why This Fixes Your Issue
Your error logs showed:
```
Exception: Kraken API error: ['EAPI:Invalid nonce']
```

This happened when:
1. Dashboard refreshed data → generated nonce X
2. At same moment, ttslo.py checked triggers → also generated nonce X (collision!)
3. Both sent to Kraken → one succeeds, one gets "Invalid nonce" error

Now with the file-based nonce coordination:
1. Dashboard wants nonce → locks file, reads last = X, generates X+1, saves, unlocks
2. ttslo.py wants nonce → waits for lock, locks file, reads last = X+1, generates X+2, saves, unlocks
3. Both get unique nonces → both succeed! ✅

## Next Steps
The fix is ready to deploy. When you rebuild your Docker container, the enhanced nonce generator will be active and should eliminate the `EAPI:Invalid nonce` errors.
