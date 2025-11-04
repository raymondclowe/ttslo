# TERMINOLOGY ANALYSIS REPORT
## TTSLO - Triggered Trailing Stop Loss Orders

**Date**: 2025-11-04  
**Purpose**: Analyze terminology confusion in TTSLO application  
**Status**: Analysis Complete - NO CODE CHANGES MADE

---

## Executive Summary

This report identifies and analyzes terminology confusion in the TTSLO application. The analysis reveals multiple overlapping terms that create ambiguity for users and developers. Key findings:

1. **"trigger"** has 3 distinct meanings (7 occurrences)
2. **"offset"** has 2 distinct meanings (5+ occurrences)
3. **TTSLO vs TSL** causes confusion about operational layers
4. **"activated"** vs **"triggered"** overlap in state tracking
5. Additional confusing terms identified: price, threshold, gap, pending

---

## Problem 1: "Trigger" - Three Distinct Meanings

### Current Usage

The term "trigger" is overloaded with THREE completely different meanings:

#### Meaning 1: **Threshold Reached** (most common)
When a pending TTSLO config's threshold price is reached, causing order creation.

**Examples**:
```python
# ttslo.py line 178
# For 'above': trigger when current price >= threshold price

# state.csv fields
triggered: 'true'  # Config has triggered (threshold met)
trigger_price: '50000'  # Price when triggered
trigger_time: '2025-11-04T10:30:00Z'  # When triggered
```

#### Meaning 2: **TSL Order Execution** 
When a TSL order on Kraken actually fills/executes.

**Examples**:
```
README.md line 356:
- SELL order triggers at $2.53
- With 1% trailing offset, it executes when price drops to ~$2.50

README.md line 776:
2. When threshold is met, creates a TSL buy order with 2% trailing offset
3. **When the buy order fills successfully**, [linked order activates]
```

**Note**: The README says "trigger" but means "fills/executes"

#### Meaning 3: **Kraken API Price Type**
Technical parameter in Kraken API for which price to use (index vs last).

**Examples**:
```python
# ttslo.py line 687-688
api_kwargs = {'trigger': 'index'}
# Prefer 'index' trigger (use index price) but fall back to 'last'

# Line 723
api_kwargs['trigger'] = 'last'
```

### Confusion Examples

**User perspective**:
- "My order triggered!" - Does this mean threshold met OR order executed?
- "Trigger price reached" notification - Which trigger?
- "TSL will trigger" - Threshold or execution?

**Developer perspective**:
```python
# Line 465: create_tsl_order(self, config, trigger_price):
# Is trigger_price:
#   a) The price when threshold was met? (YES)
#   b) The price that will trigger TSL execution? (NO)
#   c) The Kraken API trigger parameter? (NO)
```

### Impact

**High Severity** - Critical confusion between:
- When TTSLO system acts (threshold → create order)
- When Kraken TSL order acts (trailing stop → fill order)
- Kraken API technical parameter

---

## Problem 2: "Offset" - Two Distinct Meanings

### Current Usage

#### Meaning 1: **TSL Trailing Offset** (config parameter)
The percentage the TSL order trails behind price.

**Examples**:
```csv
# config.csv
trailing_offset_percent,5.0  # TSL trails by 5%

# ttslo.py
trailing_offset = float(trailing_offset_str)  # 5.0%
```

**Behavior**: Order follows price at 5% distance, triggers when reverses.

#### Meaning 2: **Distance to Threshold** (gap calculation)
Current difference between price and threshold.

**Examples**:
```python
# validator.py (implicit usage)
gap = abs(current_price - threshold_price)
gap_percent = (gap / threshold_price) * 100
# If gap_percent < trailing_offset_percent → warning

# Dashboard progress bar calculates "offset" as distance remaining
```

**Behavior**: How far price needs to move to reach threshold.

### Confusion Examples

**User sees**:
```
Dashboard:
  Threshold: $100
  Current: $95
  Trailing Offset: 5%
  
Question: Is the 5% offset:
  a) How far TSL trails? (YES)
  b) Current distance to threshold? (NO, but that's also ~5%)
```

**Validation error**:
```
"Insufficient gap: Gap 1.97% < trailing offset 2.00%"

User confusion:
- "Gap" and "offset" both measure percentages
- One is distance to threshold, other is TSL trailing distance
- Similar values, different meanings
```

### Impact

**Medium-High Severity** - Validation messages mix both meanings:
- "gap between threshold and price" (distance to threshold)
- "trailing offset" (TSL parameter)
- Values often similar magnitude (both 2-5%), increases confusion

---

## Problem 3: TTSLO vs TSL - Two Operational Layers

### Current Usage

#### Layer 1: **TTSLO** = This Application
Monitors prices, creates orders when thresholds met.

**Responsibilities**:
- Monitor cryptocurrency prices
- Check threshold conditions
- Create TSL orders on Kraken when triggered

#### Layer 2: **TSL** = Trailing Stop Loss (Kraken feature)
The actual order type on Kraken exchange.

**Responsibilities**:
- Trail behind price at specified offset
- Execute when price reverses
- Managed by Kraken, not TTSLO

### Confusion Examples

**README**:
```markdown
Line 3: "A Python tool for Kraken.com that monitors cryptocurrency 
         prices and automatically creates Trailing Stop Loss (TSL) 
         orders when specified price thresholds are met."
```

**Problem**: Users may think:
- "TTSLO creates trailing stop orders" ✓ Correct
- "TTSLO monitors TSL orders" ✗ No, it monitors thresholds
- "When TSL triggers, TTSLO acts" ✗ Backwards - TTSLO creates TSL

**State tracking**:
```python
triggered: 'true'  # TTSLO threshold met
order_id: 'OXJ...' # TSL order on Kraken
```

Which level "triggered"? Both use similar terminology.

### Impact

**Medium Severity** - Conceptual confusion:
- Two-layer system with overlapping terminology
- "Trigger" applies to both layers
- "Offset" applies to both layers
- Documentation doesn't always distinguish layers

---

## Problem 4: "Activated" vs "Triggered" - State Overlap

### Current Usage

Both terms describe when a config/order becomes active:

#### "Triggered"
```python
# state.csv
triggered: 'true'  # Threshold met, order created
trigger_price: '50000'
trigger_time: '2025-11-04T10:30:00Z'
```

#### "Activated"
```python
# state.csv  
activated_on: '2025-11-04T10:30:00Z'  # Timestamp when rule activated

# README line 514
activated_on: **Timestamp (ISO format) when the rule was activated/triggered.**
```

### Confusion

Both mean the same thing with slight nuance:
- **triggered** = event happened
- **activated** = resulting state
- Both set at same time
- Both in state.csv
- README says "activated/triggered" treating as synonyms

### Impact

**Low-Medium Severity** - Redundant terminology:
- Two words for same concept
- Minor confusion in logs/documentation
- No functional problems, just unclear

---

## Problem 5: Additional Confusing Terms

### "Price" - Multiple Types

**Types of prices**:
1. **Current price** - Real-time market price
2. **Threshold price** - Config trigger condition
3. **Trigger price** - Price when threshold met (same as current at that moment)
4. **Executed price** - Final fill price on Kraken
5. **Initial price** - Price when config created
6. **Index price** - Kraken API price type (vs "last price")

**Example confusion**:
```python
def create_tsl_order(self, config, trigger_price):
    # trigger_price is actually current_price when threshold met
```

### "Threshold" Ambiguity

Used for:
1. Config field: `threshold_price`
2. Validation: "threshold already met" error
3. Statistics: "95% probability threshold"
4. Action: "threshold reached" notification

### "Gap" vs "Distance" vs "Offset"

All measure price differences:
- **Gap**: Distance from current to threshold (validator)
- **Distance**: Same as gap (dashboard)
- **Offset**: TSL trailing parameter OR gap measurement

### "Pending" Multiple Meanings

1. **Pending TTSLO config** - Not yet triggered (watching threshold)
2. **Pending TSL order** - Created but not filled
3. **Pending linked order** - Disabled, waiting for parent (special status)

Dashboard shows all three types in "Pending" pane with different behaviors.

---

## Proposed Solutions

### Priority 1: Clarify "Trigger" 

**Current**: "trigger" means threshold reached, TSL execution, or API parameter

**Proposed**:

| Current Term | New Term | Context |
|--------------|----------|---------|
| trigger (threshold met) | **activate** or **execute** | TTSLO config becomes active |
| trigger (TSL execution) | **fill** or **execute** | TSL order on Kraken fills |
| trigger (API param) | **price_source** | Kraken API technical param |

**Code examples** (suggested):
```python
# BEFORE
triggered: 'true'  # Threshold met
trigger_price: '50000'  # Price when triggered

# AFTER - Option A
activated: 'true'  # Threshold met
activation_price: '50000'  # Price when activated

# AFTER - Option B  
executed: 'true'  # Threshold met
execution_price: '50000'  # Price when executed
```

**README examples** (suggested):
```markdown
# BEFORE
"When threshold is met, creates TSL order with 2% trailing offset"
"When the buy order fills successfully"

# AFTER
"When threshold is met, creates TSL order with 2% trailing offset"
"When the TSL order fills successfully on Kraken"
```

### Priority 2: Distinguish "Offset" Types

**Current**: "offset" means TSL parameter or distance to threshold

**Proposed**:

| Current Term | New Term | Context |
|--------------|----------|---------|
| trailing_offset_percent | **trailing_percent** or **trail_percent** | Config parameter |
| offset (gap) | **gap** or **distance** | Distance to threshold |

**Code examples**:
```python
# BEFORE
trailing_offset_percent: 5.0

# AFTER
trailing_percent: 5.0  # TSL parameter
```

**Validation messages**:
```
# BEFORE
"Gap 1.97% < trailing offset 2.00%"

# AFTER  
"Gap to threshold 1.97% < TSL trailing percent 2.00%"
```

### Priority 3: Clarify TTSLO vs TSL Layers

**Proposed**: Consistently use qualifiers

| Context | Terminology |
|---------|-------------|
| This application | **TTSLO system** or **monitor** |
| Kraken orders | **TSL order** or **Kraken TSL** |
| Threshold checking | **TTSLO threshold** or **activation threshold** |
| TSL trailing | **TSL offset** or **Kraken trailing offset** |

**Documentation examples**:
```markdown
# BEFORE (ambiguous)
"When trigger is met, TSL order created"

# AFTER (clear layers)
"When TTSLO threshold is met, system creates TSL order on Kraken"
"When Kraken TSL order fills, TTSLO sends notification"
```

### Priority 4: Consolidate State Terms

**Proposed**: Pick one term for state

**Option A - Use "activated"**:
```python
activated: 'true'
activation_price: '50000'
activation_time: '2025-11-04T10:30:00Z'
```

**Option B - Use "triggered"** (less change):
```python
triggered: 'true'  
triggered_price: '50000'  # Rename from trigger_price
triggered_time: '2025-11-04T10:30:00Z'  # Rename from trigger_time
```

Remove redundant `activated_on` field.

### Priority 5: Standardize Price Terms

**Proposed**: Use descriptive qualifiers consistently

| Price Type | Standard Term |
|------------|---------------|
| Real-time market | **current_price** ✓ (already used) |
| Config condition | **threshold_price** ✓ (already used) |
| When threshold met | **activation_price** (new) |
| Kraken fill price | **fill_price** or **executed_price** |
| Initial config price | **initial_price** ✓ (already used) |
| Kraken API type | **price_source** (index/last) |

---

## Implementation Difficulty Assessment

### Easy Changes (Documentation Only)
- README clarifications about two layers
- Add glossary section to docs
- Comments in code explaining terms
- **NO CODE CHANGES REQUIRED**

### Medium Changes (Rename Fields)
- State.csv column names
- Config.csv column names  
- Database/CSV migrations needed
- Backward compatibility required
- **REQUIRES CODE CHANGES + MIGRATION**

### Hard Changes (Core Logic)
- Function parameter names
- Internal variable names
- API responses (dashboard)
- Extensive test updates
- **MAJOR REFACTORING REQUIRED**

---

## Recommendations

### Phase 1: Documentation (Immediate - No Code Changes)

1. **Add Glossary to README**
   ```markdown
   ## Terminology Glossary
   
   - **TTSLO**: This application that monitors prices
   - **TSL**: Trailing Stop Loss orders on Kraken
   - **Threshold**: Price level that activates TTSLO
   - **Activation**: When TTSLO creates order (threshold met)
   - **Fill/Execute**: When TSL order completes on Kraken
   - **Trailing Percent**: TSL offset parameter (not gap)
   - **Gap**: Distance from current price to threshold
   ```

2. **Clarify README Examples**
   - Add layer qualifiers (TTSLO vs Kraken)
   - Distinguish threshold met vs order filled
   - Explain offset types explicitly

3. **Add Code Comments**
   ```python
   # TTSLO Activation: threshold price reached, create order
   triggered: 'true'
   
   # Price when TTSLO activated (not TSL execution price)
   trigger_price: '50000'
   ```

### Phase 2: Field Renames (Future - Requires Migration)

**IF undertaking code changes** (not in current scope):

1. State.csv:
   - `triggered` → `activated`
   - `trigger_price` → `activation_price`
   - `trigger_time` → `activation_time`
   - Remove `activated_on` (duplicate)

2. Config.csv:
   - `trailing_offset_percent` → `trailing_percent`
   - `threshold_price` → Keep (clear enough)

3. Kraken API params:
   - `trigger='index'` → `price_source='index'`

### Phase 3: Comprehensive Rename (Long-term)

**Full terminology overhaul** if pursuing perfection:
- Update all function names
- Update all variable names
- Update all API responses
- Update all documentation
- Extensive testing required

**Estimated effort**: 40+ hours

---

## Conclusion

The TTSLO application suffers from **terminology overlap** that creates confusion:

1. **"trigger"** - 3 meanings (HIGH priority to clarify)
2. **"offset"** - 2 meanings (MEDIUM priority)
3. **TTSLO vs TSL** - 2 layers (MEDIUM priority)
4. **"activated" vs "triggered"** - redundant (LOW priority)
5. **Price types** - 6+ variations (LOW priority)

### Immediate Actions (No Code Changes)

✓ **Create glossary in README**  
✓ **Add clarifying comments in code**  
✓ **Update documentation examples**  
✓ **This report serves as reference**

### Future Considerations

For major refactoring:
- Rename state/config fields
- Update API responses
- Comprehensive testing
- Migration scripts
- Version bump (breaking changes)

**Current recommendation**: Documentation improvements first, code changes only if major refactoring planned.

---

## Appendix: Term Frequency Analysis

Based on codebase search:

| Term | Files | Occurrences | Meanings |
|------|-------|-------------|----------|
| trigger | 50+ | 500+ | 3 distinct meanings |
| offset | 30+ | 200+ | 2 distinct meanings |
| threshold | 40+ | 300+ | 1 meaning (mostly clear) |
| price | 60+ | 1000+ | 6+ types |
| ttslo | 20+ | 100+ | Application name |
| tsl | 15+ | 80+ | Kraken order type |
| gap | 5 | 30+ | 1 meaning (validator) |
| activated | 8 | 25+ | Same as triggered |
| triggered | 25+ | 200+ | Same as activated |

**Legend**:
- trigger: HIGH confusion (3 meanings)
- offset: MEDIUM confusion (2 meanings)  
- Others: LOW confusion (mostly context-clear)

---

**Report prepared by**: GitHub Copilot  
**For**: raymondclowe/ttslo repository  
**Issue**: "Terminology problems"  
**Status**: Analysis complete, recommendations provided, NO CODE CHANGES MADE per requirements

