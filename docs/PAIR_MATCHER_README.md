# Pair Matcher - Human-Readable Trading Pair Names

## Overview

The Pair Matcher feature allows you to use human-readable trading pair names (like `BTC/USD`, `ETH/USDT`) in the CSV editor instead of having to remember Kraken's confusing internal pair codes (like `XXBTZUSD`, `ETHUSDT`).

## Problem Statement

Kraken uses non-intuitive trading pair codes that are difficult for humans to remember:
- Bitcoin/USD is `XXBTZUSD` (not `BTCUSD`)
- Ethereum/USD is `XETHZUSD` (not `ETHUSD`)
- Bitcoin/USDT is `XBTUSDT` (note: XBT not BTC)

This makes it challenging to fill in CSV configuration files, especially when editing manually or using the CSV TUI editor.

## Solution

The Pair Matcher automatically resolves human-readable pair names to official Kraken pair codes using:

1. **Exact Matching**: If you enter an official Kraken pair code, it's accepted as-is
2. **Normalized Matching**: Common formats like `BTC/USD`, `btc/usd`, `BTCUSD` are automatically converted to `XXBTZUSD`
3. **Fuzzy Matching**: Similar pairs are suggested with confidence scores when exact matches aren't found

## Usage

### In the CSV Editor

When editing the "pair" field in the CSV editor:

1. **Enter any common format:**
   - `BTC/USD` - with slash separator
   - `btc/usd` - lowercase
   - `BTCUSD` - no separator
   - `BTC-USD` - with hyphen
   - `btc usd` - with space

2. **The editor will:**
   - Automatically resolve it to the official Kraken code (`XXBTZUSD`)
   - Display a confirmation message: `✓ Resolved to: XXBTZUSD`
   - Save the official code to the CSV file

3. **For exact matches:**
   - If you enter `XXBTZUSD` directly, it's accepted without any conversion

4. **For fuzzy matches:**
   - If the input is ambiguous, you'll see: `⚠️ Fuzzy match: 'input' → 'XBTUSDT' (confidence: 75%). Verify this is correct!`
   - The confidence score indicates how certain the match is
   - Always verify fuzzy matches before saving

### Common Pair Examples

| Human Input | Resolves To | Kraken wsname |
|-------------|-------------|---------------|
| `BTC/USD` | `XXBTZUSD` | `XBT/USD` |
| `btc/usd` | `XXBTZUSD` | `XBT/USD` |
| `ETH/USD` | `XETHZUSD` | `ETH/USD` |
| `ETH/USDT` | `ETHUSDT` | `ETH/USDT` |
| `BTC/USDT` | `XBTUSDT` | `XBT/USDT` |
| `SOL/USD` | `SOLUSD` | `SOL/USD` |
| `ADA/USD` | `ADAUSD` | `ADA/USD` |
| `DOT/EUR` | `DOTEUR` | `DOT/EUR` |

### Programmatic Usage

You can also use the pair matcher module directly in Python scripts:

```python
from pair_matcher import find_pair_match

# Find a pair match
result = find_pair_match('BTC/USD')
if result:
    print(f"Pair code: {result.pair_code}")  # XXBTZUSD
    print(f"Confidence: {result.confidence}")  # 1.0
    print(f"Match type: {result.match_type}")  # normalized
    print(f"Kraken wsname: {result.kraken_wsname}")  # XBT/USD
```

#### API Functions

**`find_pair_match(human_input: str) -> Optional[PairMatchResult]`**
- Finds the best matching Kraken pair code for human input
- Returns a `PairMatchResult` with the match details
- Returns `None` if no reasonable match is found

**`validate_pair_exists(pair_code: str) -> bool`**
- Checks if a pair code exists in Kraken's trading pairs
- Useful for validating direct pair code inputs

**`find_similar_pairs(human_input: str, limit: int = 5) -> List[PairMatchResult]`**
- Finds multiple similar pairs for suggestions
- Returns a list sorted by confidence (highest first)
- Useful for showing alternatives to the user

**`normalize_pair_input(human_input: str) -> str`**
- Normalizes input for matching (uppercase, remove separators, BTC→XBT)
- Useful for preprocessing user input

## Match Types and Confidence

### Match Types

1. **Exact Match** (`exact`)
   - Input is already a valid Kraken pair code
   - Confidence: 1.0 (100%)
   - Example: `XXBTZUSD` → `XXBTZUSD`

2. **Normalized Match** (`normalized`)
   - Input is converted using standard rules
   - Confidence: 0.95-1.0 (95-100%)
   - Example: `BTC/USD` → `XXBTZUSD`

3. **Fuzzy Match** (`fuzzy`)
   - Input is matched using similarity scoring
   - Confidence: 0.7-0.95 (70-95%)
   - Example: Ambiguous or partial matches
   - **⚠️ Always verify fuzzy matches!**

### Confidence Thresholds

- **1.0 (100%)**: Exact or perfect match - use with full confidence
- **≥0.9 (90%+)**: High confidence - very likely correct
- **0.7-0.9 (70-90%)**: Moderate confidence - verify before using
- **<0.7 (<70%)**: Low confidence - not returned to avoid errors

## Special Cases

### Bitcoin (BTC vs XBT)

Kraken uses `XBT` as the currency code for Bitcoin (ISO 4217 standard for non-national currencies), not `BTC`. The pair matcher automatically handles this:

- `BTC/USD` → `XXBTZUSD` (base: `XXBT`, quote: `ZUSD`)
- `BTC/USDT` → `XBTUSDT` (base: `XXBT`, quote: `USDT`)

### USD Variations

Kraken has multiple USD-related assets:
- `ZUSD` - Regular USD (fiat)
- `USDT` - Tether USD (stablecoin)
- `USDC` - USD Coin (stablecoin)
- `USD1` - Another USD variant

The pair matcher distinguishes between these based on your input:
- `BTC/USD` → Uses `ZUSD` (regular USD)
- `BTC/USDT` → Uses `USDT` (Tether)
- `BTC/USDC` → Uses `USDC` (USD Coin)

## Implementation Details

### Caching

The pair matcher caches Kraken's asset pairs data to improve performance:
- Cache file: `.kraken_pairs_cache.json`
- Cache duration: 24 hours
- Automatically refreshed when stale
- Falls back to stale cache if API is unavailable

### Matching Algorithm

The matcher uses a multi-strategy approach:

1. **Strategy 1**: Exact match against pair codes
2. **Strategy 2**: Exact match against altnames
3. **Strategy 3**: Normalized match against wsnames
   - Remove separators (/, -, _, space)
   - Convert to uppercase
   - Replace BTC with XBT
4. **Strategy 4**: Fuzzy matching with similarity scoring
   - Uses `difflib.SequenceMatcher` for similarity
   - Compares against wsname, altname, and pair code
   - Returns best match with confidence score

### Error Handling

- Invalid inputs return `None` or error messages
- Network errors fall back to cached data
- Unknown pairs show helpful error messages with suggestions

## Testing

Comprehensive tests are available:

```bash
# Run pair matcher tests
uv run pytest tests/test_pair_matcher.py -v

# Run CSV editor integration tests
uv run pytest tests/test_csv_editor.py -v

# Run all tests
uv run pytest tests/test_pair_matcher.py test_csv_editor.py -v
```

Test coverage includes:
- ✅ Exact matching
- ✅ Normalized matching (various formats)
- ✅ Fuzzy matching with confidence scores
- ✅ Case insensitivity
- ✅ Separator handling (/, -, _, space)
- ✅ BTC to XBT conversion
- ✅ Integration with CSV editor validation
- ✅ Empty and invalid input handling

## Examples

### Example 1: Basic Usage in CSV Editor

1. Open CSV editor: `uv run python3 csv_editor.py config.csv`
2. Navigate to a "pair" field
3. Press Enter or 'e' to edit
4. Type: `btc/usd`
5. Press Enter
6. See confirmation: `✓ Resolved to: XXBTZUSD`
7. The official code `XXBTZUSD` is saved to the CSV

### Example 2: Handling Multiple Formats

All these inputs resolve to the same pair code:
- `BTC/USD` → `XXBTZUSD`
- `btc/usd` → `XXBTZUSD`
- `BTCUSD` → `XXBTZUSD`
- `BTC-USD` → `XXBTZUSD`
- `btc usd` → `XXBTZUSD`

### Example 3: Using in Python Script

```python
from pair_matcher import find_pair_match

# User input from a form or CLI
user_input = input("Enter trading pair: ")  # User types "BTC/USD"

# Resolve to Kraken code
result = find_pair_match(user_input)

if result:
    if result.is_exact():
        print(f"Using pair code: {result.pair_code}")
    elif result.is_high_confidence():
        print(f"Resolved '{user_input}' to '{result.pair_code}'")
    else:
        print(f"⚠️ Fuzzy match: {result.pair_code} (confidence: {result.confidence:.0%})")
        confirm = input("Is this correct? (y/n): ")
        if confirm.lower() != 'y':
            print("Please enter a more specific pair name")
else:
    print(f"Could not match '{user_input}' to a Kraken trading pair")
```

## Troubleshooting

### Issue: "Unknown trading pair" error

**Solution:** 
- Ensure you're using a valid base and quote asset
- Check spelling of asset names
- Try different formats (with/without separator)
- Use official Kraken pair codes if unsure

### Issue: Cache is stale or corrupted

**Solution:**
```bash
# Delete cache file to force refresh
rm .kraken_pairs_cache.json

# Run the matcher again to rebuild cache
uv run python3 pair_matcher.py
```

### Issue: Fuzzy match has low confidence

**Solution:**
- Be more specific in your input
- Use the exact Kraken pair code
- Check Kraken's API for available pairs: https://api.kraken.com/0/public/AssetPairs

### Issue: Network error when fetching pairs

**Solution:**
- Check your internet connection
- The matcher will use cached data if available
- If no cache exists, you'll need network access to build it

## Future Enhancements

Potential improvements for future versions:
- Interactive selection when multiple high-confidence matches exist
- Support for custom pair aliases (user-defined shortcuts)
- Integration with Kraken WebSocket for real-time pair updates
- Visual preview of matched pair in the CSV editor
- Bulk pair resolution for entire CSV files

## Contributing

To add new features or fix bugs:

1. Update `pair_matcher.py` with your changes
2. Add tests to `tests/test_pair_matcher.py`
3. Run tests: `uv run pytest tests/test_pair_matcher.py -v`
4. Update this README with new functionality

## License

Part of the TTSLO project. See main repository for license information.
