# Profit-Based Config Generation - Implementation Summary

## Overview

Enhanced `coin_stats.py` with intelligent profit-based configuration generation that calculates optimal trading parameters to achieve target profit percentages.

## Issue Requirements (All Implemented ✓)

1. **New Parameters**
   - `--percentage-profit` (default: 5.0) - Target profit percentage including slippage
   - `--profit-days` (default: 7) - Time window for achieving profit

2. **Profit Calculation Including Slippage**
   - Actual profit = price_movement - trailing_offset_slippage
   - For 5% profit with 2% trailing: needs 7% total movement
   - Algorithm automatically calculates required movement

3. **Optimal Parameter Selection**
   - Chooses trigger price offset from current price
   - Selects trailing offset (≥1.0%, TTSLO minimum)
   - Iterates through trailing offsets: 1.0%, 1.5%, 2.0%, 2.5%, 3.0%, 4.0%, 5.0%
   - Picks minimum trailing offset that achieves target

4. **Volatility-Based Validation**
   - Uses random walk model: σ_N_days = σ_minute × sqrt(N_days × 1440)
   - Ensures >50% probability brackets fire within timeframe
   - Reports which coins lack necessary volatility

5. **Unsuitable Coin Reporting**
   - Shows plausible profit for low-volatility coins
   - Suggests adjusting parameters (lower profit or longer days)
   - Clear on-screen notifications

## Implementation Details

### New Function: `calculate_profit_based_params()`

Calculates optimal trading parameters for target profit:

```python
def calculate_profit_based_params(stats, analyzer, target_profit_pct, profit_days, 
                                  min_trailing_offset_pct=1.0):
    """
    Returns:
    - achievable: bool (can we achieve target?)
    - trigger_offset_pct: trigger price offset
    - trailing_offset_pct: recommended trailing offset
    - plausible_profit_pct: max achievable profit
    - probability: probability of success
    - total_movement_needed_pct: total movement (profit + slippage)
    """
```

### Enhanced Function: `generate_config_suggestions()`

Now supports two modes:

**1. Profit-Based Mode (NEW, default)**
- Enabled when `target_profit_pct` is set
- Calculates optimal params per coin
- Reports unsuitable coins with alternatives

**2. Legacy Mode**
- Enabled when `target_profit_pct=None`
- Uses fixed bracket_offset_pct and trailing_offset_pct
- Maintains backward compatibility

### Algorithm Flow

```
1. For each coin:
   - Calculate volatility over profit_days window
   - Iterate trailing offsets (1.0% to 5.0%)
   - For each offset:
     * Calculate required movement = target_profit + trailing_offset
     * Calculate probability using distribution (normal or Student's t)
     * Check if probability >= 50%
   - Select minimum trailing offset that achieves target
   
2. If no offset works:
   - Calculate maximum plausible profit
   - Add to unsuitable pairs list
   
3. Generate config entries for suitable pairs
   
4. Report unsuitable pairs with plausible profits
```

### Example Output

```bash
$ python tools/coin_stats.py --percentage-profit 5.0 --profit-days 7

======================================================================
PROFIT-BASED CONFIG GENERATION
======================================================================
Target profit: 5.0% (after trailing offset slippage)
Profit window: 7 days

✓ BTC/USD: trigger ±6.5%, trailing 1.5%, prob 52.3%
✓ ETH/USD: trigger ±7.2%, trailing 2.0%, prob 51.8%
✓ SOL/USD: trigger ±8.5%, trailing 3.0%, prob 53.1%

Config generation complete:
  Pairs included: 25
  Pairs excluded (insufficient volatility): 7

======================================================================
UNSUITABLE PAIRS (Insufficient Volatility)
======================================================================
The following pairs cannot achieve 5.0% profit
within 7 days with >50% probability:

  ✗ STABLE/USD      Plausible profit: ~1.2%
    Insufficient volatility: max plausible profit ~1.2%
  ✗ LOWVOL/USD      Plausible profit: ~2.3%
    Insufficient volatility: max plausible profit ~2.3%

💡 Suggestion: Run with lower --percentage-profit or higher --profit-days
======================================================================
```

## Statistical Methodology

### Random Walk Model

Volatility accumulates over time following random walk:
```
σ_N_minutes = σ_1_minute × sqrt(N)

Example for 7 days:
σ_7_days = σ_minute × sqrt(7 × 1440)
         = σ_minute × sqrt(10,080)
         ≈ σ_minute × 100.4
```

### Distribution Handling

Supports both normal and Student's t-distributions:

- **Normal Distribution**: For symmetric, bell-curve data
- **Student's t-Distribution**: For fat-tailed distributions (crypto common)
- Automatically selects best fit from statistical analysis

### Probability Calculation

For target movement M with volatility σ:
```
z-score = M / σ
probability = 2 × (1 - CDF(z-score))  # Both directions
```

Must achieve P(movement ≥ M) ≥ 50% for both buy and sell brackets.

## Testing

### Unit Tests (9 tests)
- `test_coin_stats_profit_based.py`
- Tests parameter calculation logic
- Edge cases (zero volatility, missing stats)
- Distribution handling (normal, Student's t)
- Probability validation

### Integration Tests (5 tests)
- `test_coin_stats_integration.py`
- Full workflow testing
- Legacy mode compatibility
- Config file generation
- Unsuitable pairs reporting

**All 36 coin_stats tests pass** ✓

## Usage Examples

### Basic Profit-Based Mode
```bash
python3 tools/coin_stats.py \
  --percentage-profit 5.0 \
  --profit-days 7
```

### Custom Parameters
```bash
python3 tools/coin_stats.py \
  --pairs XXBTZUSD XETHZUSD SOLUSD \
  --percentage-profit 3.0 \
  --profit-days 14 \
  --target-usd-volume 2.0 \
  --csv-output stats.csv
```

### Legacy Mode (backward compatible)
```bash
python3 tools/coin_stats.py \
  --suggestbracket 2.0 \
  --suggestoffset 1.0
```
*Note: When --percentage-profit is NOT specified, uses legacy mode*

## Key Features

### ✓ Profit Includes Slippage
Actual profit calculation accounts for trailing offset:
- User requests 5% profit
- Algorithm adds trailing offset (e.g., 2%)
- Calculates for 7% total movement
- User gets 5% net profit after slippage

### ✓ Optimal Parameter Selection
- Minimizes trailing offset while meeting probability threshold
- Adjusts trigger price based on volatility
- Per-coin optimization (not one-size-fits-all)

### ✓ Statistical Validation
- >50% probability requirement ensures realistic targets
- Uses coin's actual distribution (normal or t-distribution)
- Random walk model for time-based volatility

### ✓ Unsuitable Pair Reporting
- Shows what profit IS achievable
- Helps users adjust expectations
- Suggests parameter changes

### ✓ Backward Compatibility
- Legacy mode preserved
- Existing scripts work unchanged
- Smooth migration path

## Files Changed

1. `tools/coin_stats.py`
   - Added `calculate_profit_based_params()` function
   - Enhanced `generate_config_suggestions()` with dual-mode support
   - Added `--percentage-profit` and `--profit-days` parameters
   - Improved unsuitable pairs reporting

2. `tests/test_coin_stats_profit_based.py` (NEW)
   - 9 unit tests for parameter calculation
   - Edge case handling
   - Distribution testing

3. `tests/test_coin_stats_integration.py` (NEW)
   - 5 integration tests
   - Full workflow validation
   - Legacy compatibility checks

4. `README.md`
   - Added profit-based mode documentation
   - Usage examples
   - Feature descriptions

## Benefits

1. **Smarter Trading**: Automatically calculates optimal parameters instead of guessing
2. **Realistic Targets**: Validates achievability with statistical probability
3. **Informed Decisions**: Shows what's actually possible for each coin
4. **Better Risk Management**: >50% probability threshold prevents unrealistic expectations
5. **Time Awareness**: Accounts for time window (7 days different from 24 hours)
6. **Slippage Awareness**: Includes trailing offset cost in profit calculation

## Future Enhancements (Optional)

- Support for custom probability thresholds (currently fixed at 50%)
- Multi-timeframe analysis (e.g., 1-day, 7-day, 30-day simultaneously)
- Risk/reward ratio calculations
- Portfolio-level profit targeting
- Historical backtesting validation

---

**Implementation Status**: ✅ Complete
**Tests**: ✅ 36/36 passing
**Documentation**: ✅ Complete
**Backward Compatibility**: ✅ Maintained
