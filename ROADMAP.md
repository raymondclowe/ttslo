ROADMAP — ttslo project

This file captures short, actionable work items with expected benefits. Keep items small and prioritized; mark status in the project's tracker.

1) Make oflags configurable (fcib / fciq)
   - What: Add optional `oflags` column in config.csv and wire through `create_tsl_order()` -> `KrakenAPI.add_trailing_stop_loss()`.
   - Why/Benefit: Lets operators choose which asset pays fees. Important when base balances are tight (avoid failed sells) or to prefer reducing dust in a particular currency.
   - Est: 1-2 hours
   - Risk: Low

2) Support `trigger` parameter per-config (index / last)
   - What: Allow config to specify `trigger=index` or `trigger=last` and send it to Kraken API.
   - Why/Benefit: Matches operator preference and example orders that use index-based triggering. Reduces mismatch between observed open orders and TTSLO-created orders.
   - Est: 1 hour
   - Risk: Low

3) Trailing-offset precision setting
   - What: Allow formatting precision of trailing offset (e.g., +5.0% vs +5.0000%).
   - Why/Benefit: More consistent order descriptions, easier matching to previously extracted orders, and predictable diffs in order-extraction tools.
   - Est: 30-60 minutes
   - Risk: Very low

4) Volume formatting helper
   - What: Add helper to canonicalize volume strings to pair-specific precision.
   - Why/Benefit: Prevent weird decimal rounding in order submissions and make extracted order rows consistent.
   - Est: 1-2 hours
   - Risk: Low

5) Harden `add_order()` validation and tests
   - What: Bring `add_order()` validation to the same level as `add_trailing_stop_loss()` and add unit tests.
   - Why/Benefit: Prevents malformed order requests for non-trailing types and improves code consistency.
   - Est: 2 hours
   - Risk: Low

6) Tests for `oflags` and `trigger` behaviour
   - What: Unit tests that assert these params are serialized correctly and integration dry-run smoke tests.
   - Why/Benefit: Avoid regressions and provide confidence when changing request serialization.
   - Est: 2-3 hours
   - Risk: Low

7) Docs & quickstart updates
   - What: Document `oflags`, `trigger`, formatting choices, and recommended defaults in README/QUICKSTART.
   - Why/Benefit: Less operator confusion and fewer support questions.
   - Est: 1 hour
   - Risk: Very low

8) Notifications for fee-source risks
   - What: When `oflags='fcib'` and base balance is near required volume, log/notify recommending `fciq`.
   - Why/Benefit: Prevent failed orders caused by using base currency for fees.
   - Est: 1-2 hours
   - Risk: Low

9) Example configs
   - What: Add sample config rows showing `oflags` and `trigger` examples in sample config generator and docs.
   - Why/Benefit: Helps operators adopt recommended settings quickly.
   - Est: 30 minutes
   - Risk: Very low

10) CI smoke test to validate payload serialization
    - What: Add a quick test that runs `add_trailing_stop_loss()` in dry-run/test mode and asserts JSON payload keys/format.
    - Why/Benefit: Prevents accidental API-contract regressions.
    - Est: 1-2 hours
    - Risk: Low

Prioritization notes
- Start with 1 & 2 (configurable `oflags` and `trigger`) — highest impact for operators.
- Then add tests (6 & 10) and docs (7 & 9).
- Precision/formatting and volume helper are nice-to-have improvements (3 & 4).

If you'd like I will:
- Create PR-ready edits for the top-priority item (add `oflags` support), including tests and docs.
- Or, keep the roadmap as-is and mark tasks as separate issues. 

Pick the next action and I'll implement it.