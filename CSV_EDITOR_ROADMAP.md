# CSV Editor Roadmap - Usability Improvements

This document outlines a comprehensive roadmap for improving the usability, features, and design of the CSV Editor TUI (`csv_editor.py`). The roadmap is organized into short-term (quick wins), medium-term (moderate effort), and long-term (significant enhancements) phases.

## Executive Summary

The CSV Editor is a functional Textual-based TUI for editing TTSLO configuration files. While it provides core editing capabilities with validation, there are several areas where usability, error handling, and user experience can be significantly improved. This roadmap prioritizes improvements based on impact, effort, and user pain points.

## Current State Analysis

### Strengths
- ✅ Functional table view with cell editing
- ✅ Basic validation (threshold_type, direction, pair, volume, ID uniqueness)
- ✅ File locking and coordination protocol with service
- ✅ Row management (add/delete)
- ✅ Financial responsibility validation (prevents "buy high, sell low")
- ✅ Intelligent pair matching (human-readable names → Kraken codes)
- ✅ Volume formatting to 8 decimal places
- ✅ Good test coverage

### Pain Points & Limitations

#### 1. **Discoverability & Help**
- ❌ No in-app help screen or command palette
- ❌ Keybindings only shown in footer (limited space)
- ❌ No tooltips or context-sensitive help
- ❌ No indication of which fields are validated

#### 2. **Error Handling & User Feedback**
- ❌ Validation errors only shown in edit modal (not in table view)
- ❌ No indication of which rows have validation issues
- ❌ File lock errors could be more user-friendly
- ❌ No undo/redo functionality

#### 3. **Navigation & Editing UX**
- ❌ Must press Enter to edit (not intuitive for some users)
- ❌ No bulk editing (e.g., enable/disable multiple rows)
- ❌ No search/filter functionality
- ❌ No copy/paste between cells
- ❌ No column sorting or reordering
- ❌ No row duplication feature (common workflow)

#### 4. **Validation & Error Prevention**
- ❌ Validation only happens on cell save (not real-time preview)
- ❌ No validation summary view for entire file
- ❌ Limited validation for numeric fields (threshold_price, trailing_offset_percent)
- ❌ No warnings for potentially dangerous configurations

#### 5. **Import/Export & File Management**
- ❌ No CSV dialect configuration (always uses default)
- ❌ No import from other formats (JSON, YAML)
- ❌ No export to other formats
- ❌ No backup/restore functionality
- ❌ No file history or version tracking

#### 6. **Performance & Large Files**
- ⚠️ No pagination for large files (could be slow with 100+ rows)
- ⚠️ No virtual scrolling (loads entire file into memory)
- ⚠️ No lazy loading of data

#### 7. **Advanced Features**
- ❌ No templates or presets for common configurations
- ❌ No batch operations (import multiple configs at once)
- ❌ No config validation against live Kraken API
- ❌ No price preview or testing mode
- ❌ No integration with TTSLO dashboard

## Roadmap Phases

---

## Phase 1: Quick Wins (Low Effort, High Impact)

### 1.1 Enhanced Help & Discoverability
**Priority: HIGH** | **Effort: 1-2 days**

- [ ] Add `?` or `F1` keybinding to show help screen
- [ ] Create a comprehensive help modal with:
  - All keybindings organized by category
  - Validation rules explanation
  - Quick tips and workflows
- [ ] Add tooltips for validation rules (show on hover in edit modal)
- [ ] Display current file path and status in header

**Benefits:**
- New users can discover features without reading docs
- Reduces support questions
- Improves onboarding experience

**Files to modify:**
- `csv_editor.py`: Add `HelpScreen` modal, keybinding

---

### 1.2 Improved Error Messages & Notifications
**Priority: HIGH** | **Effort: 1 day**

- [ ] Make file lock error messages more actionable
  - Show which process has the lock (if possible)
  - Suggest running `systemctl stop ttslo` if service is blocking
- [ ] Add more descriptive validation error messages
  - Include examples of valid values
  - Show current vs. expected format
- [ ] Add warning notifications for risky edits:
  - Changing enabled from true to false
  - Deleting rows with active orders
  - Very large volume values

**Benefits:**
- Users understand what went wrong
- Clear guidance on how to fix issues
- Prevents accidental misconfigurations

**Files to modify:**
- `csv_editor.py`: Update validation messages, lock handling

---

### 1.3 Row Duplication Feature
**Priority: MEDIUM** | **Effort: 0.5 days**

- [ ] Add `Ctrl+Shift+D` keybinding to duplicate current row
- [ ] Auto-increment ID when duplicating (e.g., `btc_1` → `btc_2`)
- [ ] Place duplicated row immediately below current row
- [ ] Show notification with new row ID

**Benefits:**
- Common workflow (create similar configs) becomes much faster
- Reduces typing and errors
- Improves productivity

**Files to modify:**
- `csv_editor.py`: Add `action_duplicate_row()` method

---

### 1.4 Visual Indicators for Validation Status
**Priority: MEDIUM** | **Effort: 1 day**

- [ ] Add colored indicators in table cells:
  - Green checkmark for valid cells
  - Red exclamation for invalid cells
  - Yellow warning for risky values
- [ ] Highlight entire row if any cell is invalid
- [ ] Add status bar showing validation summary (e.g., "2 errors, 1 warning")

**Benefits:**
- Users can immediately see problems without testing each cell
- Reduces time spent debugging invalid configs
- Proactive error prevention

**Files to modify:**
- `csv_editor.py`: Add cell styling, status widget
- `test_csv_editor.py`: Add tests for validation indicators

---

### 1.5 Direct Cell Editing (Type-to-Edit)
**Priority: MEDIUM** | **Effort: 1 day**

- [ ] Allow typing to start editing (in addition to Enter)
- [ ] Show visual feedback when cell enters edit mode
- [ ] Keep Enter key as explicit "edit" command
- [ ] Add `e` key as alternative to Enter (for muscle memory)

**Benefits:**
- More intuitive for users familiar with spreadsheets
- Faster editing workflow
- Reduces friction

**Files to modify:**
- `csv_editor.py`: Add key event handler for alphanumeric keys

---

### 1.6 Quick Save Indicator
**Priority: LOW** | **Effort: 0.5 days**

- [ ] Show "*" in title bar when file has unsaved changes
- [ ] Change footer color when modified
- [ ] Add visual feedback during save (progress indicator)
- [ ] Prompt to save on quit if changes exist

**Benefits:**
- Users know when they need to save
- Prevents accidental data loss
- Better status visibility

**Files to modify:**
- `csv_editor.py`: Update title, add quit confirmation

---

## Phase 2: Medium-Term Enhancements (Moderate Effort, High Value)

### 2.1 Search & Filter Functionality
**Priority: HIGH** | **Effort: 3-4 days**

- [ ] Add `/` keybinding to open search modal
- [ ] Support search by:
  - ID (exact or partial match)
  - Pair (e.g., "BTC" finds all BTC pairs)
  - Any column value
  - Regular expressions (advanced)
- [ ] Highlight matching rows in table
- [ ] Add "jump to next match" navigation
- [ ] Add filter mode to show only matching rows

**Benefits:**
- Essential for files with 20+ rows
- Quick navigation to specific configs
- Makes bulk editing feasible

**Files to modify:**
- `csv_editor.py`: Add `SearchScreen`, filtering logic

---

### 2.2 Copy/Paste & Clipboard Support
**Priority: MEDIUM** | **Effort: 2-3 days**

- [ ] Add `Ctrl+C` to copy current cell value
- [ ] Add `Ctrl+V` to paste into current cell
- [ ] Support copying entire row (`Ctrl+Shift+C`)
- [ ] Support pasting entire row (`Ctrl+Shift+V`)
- [ ] Show notification on copy/paste operations

**Benefits:**
- Essential for productivity
- Enables bulk data entry from other sources
- Reduces typing errors

**Files to modify:**
- `csv_editor.py`: Add clipboard manager, copy/paste actions

---

### 2.3 Undo/Redo Functionality
**Priority: MEDIUM** | **Effort: 3-5 days**

- [ ] Add `Ctrl+Z` to undo last change
- [ ] Add `Ctrl+Y` or `Ctrl+Shift+Z` to redo
- [ ] Track change history (cell edits, row adds/deletes)
- [ ] Show change description in notification
- [ ] Limit history to last 50 operations (memory efficiency)

**Benefits:**
- Major confidence booster for users
- Enables experimentation without fear
- Reduces need for backups during editing

**Files to modify:**
- `csv_editor.py`: Add `ChangeHistory` class, undo/redo actions

---

### 2.4 Batch Enable/Disable Operations
**Priority: MEDIUM** | **Effort: 2-3 days**

- [ ] Add multi-row selection mode (`Shift+Arrow` or `Space` to toggle)
- [ ] Add `Ctrl+E` to toggle enabled state for selected rows
- [ ] Add `Ctrl+Shift+E` to enable all rows
- [ ] Add `Ctrl+Shift+D` to disable all rows
- [ ] Show count of affected rows in notification

**Benefits:**
- Common workflow (enable/disable strategies for testing)
- Much faster than editing individually
- Reduces errors

**Files to modify:**
- `csv_editor.py`: Add row selection state, batch operations

---

### 2.5 Column Sorting & Reordering
**Priority: LOW** | **Effort: 2-3 days**

- [ ] Add column header click to sort (ascending/descending)
- [ ] Show sort indicator (▲ or ▼) in header
- [ ] Support multi-column sort (with priority)
- [ ] Add keybinding to reset sort order
- [ ] (Optional) Allow column reordering (drag-and-drop)

**Benefits:**
- Better organization of large configs
- Easy to find rows by criteria (e.g., all "sell" orders)
- Improves visual scanning

**Files to modify:**
- `csv_editor.py`: Add sort logic, column header handlers

---

### 2.6 Enhanced Validation with Preview
**Priority: MEDIUM** | **Effort: 2-3 days**

- [ ] Add validation preview in edit modal (real-time)
- [ ] Show formatted/resolved value before saving:
  - Pair normalization preview
  - Volume formatting preview
  - Financial validation warnings
- [ ] Add "Validate All" command (`Ctrl+Shift+V`)
- [ ] Show validation report in modal (list all issues)

**Benefits:**
- Catch errors before saving
- Better understanding of auto-formatting
- Reduces round-trip time for validation

**Files to modify:**
- `csv_editor.py`: Add real-time validation, validation report screen

---

### 2.7 Row Templates & Presets
**Priority: LOW** | **Effort: 2-3 days**

- [ ] Add "Add Row from Template" command (`Ctrl+Shift+N`)
- [ ] Pre-define templates for common strategies:
  - Buy dip (below threshold, buy)
  - Sell peak (above threshold, sell)
  - Trailing stop loss default settings
- [ ] Allow saving current row as template
- [ ] Store templates in separate file (e.g., `templates.csv`)

**Benefits:**
- Faster onboarding for new users
- Consistent configuration patterns
- Reduces typing and errors

**Files to modify:**
- `csv_editor.py`: Add `TemplateManager`, template selection screen

---

## Phase 3: Long-Term Vision (High Effort, High Impact)

### 3.1 Advanced File Operations & History
**Priority: MEDIUM** | **Effort: 5-7 days**

- [ ] Add backup on save (e.g., `config.csv.backup-2024-10-22-08-00`)
- [ ] Keep last N backups (configurable, default 10)
- [ ] Add "Restore from Backup" command
- [ ] Show file change history (git integration?)
- [ ] Add "Compare with Saved" view (diff viewer)

**Benefits:**
- Safety net for mistakes
- Easy rollback to previous versions
- Audit trail of changes

**Files to modify:**
- `csv_editor.py`: Add backup manager, diff viewer

---

### 3.2 Import/Export Other Formats
**Priority: LOW** | **Effort: 4-5 days**

- [ ] Add "Export to JSON" command
- [ ] Add "Export to YAML" command
- [ ] Add "Import from JSON" command
- [ ] Add "Import from YAML" command
- [ ] Support CSV dialect configuration (delimiter, quote char)

**Benefits:**
- Integration with other tools
- Easier bulk config generation from scripts
- Better version control (YAML is more readable)

**Files to modify:**
- `csv_editor.py`: Add import/export handlers
- New file: `config_converters.py`

---

### 3.3 Live Validation Against Kraken API
**Priority: LOW** | **Effort: 5-7 days**

- [ ] Add "Test Connection" command
- [ ] Validate pairs against live Kraken API
- [ ] Check balance sufficiency for volume
- [ ] Show current market price for pair
- [ ] Warn if threshold_price is far from current price
- [ ] Verify account has necessary permissions

**Benefits:**
- Catch errors before running TTSLO
- Real-time feedback on feasibility
- Better confidence in configs

**Files to modify:**
- `csv_editor.py`: Add API validation screen
- `kraken_api.py`: Add validation helpers

---

### 3.4 Integration with TTSLO Dashboard
**Priority: MEDIUM** | **Effort: 7-10 days**

- [ ] Add "Open in Dashboard" command
- [ ] Show live status of each config:
  - Active orders
  - Triggered state
  - Last check timestamp
- [ ] Allow triggering price checks from editor
- [ ] Show recent notifications/alerts
- [ ] Link to order details on Kraken

**Benefits:**
- Single interface for config and monitoring
- Better situational awareness
- Faster workflow (no context switching)

**Files to modify:**
- `csv_editor.py`: Add dashboard integration
- `dashboard.py`: Add editor hooks

---

### 3.5 Performance Optimizations for Large Files
**Priority: LOW** | **Effort: 7-10 days**

- [ ] Implement virtual scrolling (lazy render)
- [ ] Add pagination mode (e.g., 50 rows per page)
- [ ] Cache validation results
- [ ] Optimize table rendering
- [ ] Profile and optimize hot paths
- [ ] Add progress indicators for slow operations

**Benefits:**
- Support 500+ row configs
- Smooth editing experience
- Lower memory usage

**Files to modify:**
- `csv_editor.py`: Refactor data loading, add pagination

---

### 3.6 Collaborative Editing & Conflict Resolution
**Priority: VERY LOW** | **Effort: 10-15 days**

- [ ] Detect external file changes while editor is open
- [ ] Prompt to reload if file changed externally
- [ ] Add 3-way merge for conflicts
- [ ] Show diff of local vs. external changes
- [ ] Allow cherry-picking changes to merge

**Benefits:**
- Safe multi-user editing (rare use case)
- Better handling of service updates
- Professional-grade editor

**Files to modify:**
- `csv_editor.py`: Add file watcher, merge UI

---

## Implementation Priority Matrix

```
High Priority, Low Effort (Do First)
├─ Enhanced Help & Discoverability
├─ Improved Error Messages
├─ Row Duplication Feature
├─ Visual Validation Indicators
└─ Quick Save Indicator

High Priority, Medium Effort (Do Next)
├─ Search & Filter Functionality
├─ Undo/Redo Functionality
├─ Enhanced Validation with Preview
└─ Copy/Paste Support

Medium Priority, Medium Effort (Consider Later)
├─ Batch Enable/Disable Operations
├─ Row Templates & Presets
├─ Advanced File Operations & History
└─ Dashboard Integration

Low Priority or High Effort (Future/Nice-to-Have)
├─ Column Sorting & Reordering
├─ Import/Export Other Formats
├─ Live Kraken API Validation
├─ Performance Optimizations
└─ Collaborative Editing
```

---

## Testing & Documentation Requirements

For each implemented feature:

1. **Unit Tests**
   - Add tests in `test_csv_editor.py`
   - Cover happy path and error cases
   - Test validation logic

2. **Integration Tests**
   - Add tests in `test_editor_integration.py`
   - Test with sample config files
   - Test file locking coordination

3. **Documentation**
   - Update `CSV_EDITOR_README.md`
   - Update `CSV_EDITOR_DEMO.md` with screenshots/examples
   - Add inline docstrings

4. **User Acceptance Testing**
   - Manually test each feature
   - Verify keybindings work as expected
   - Check for regressions

---

## Success Metrics

Track these metrics to measure improvement:

1. **Usability**
   - Time to complete common tasks (before vs. after)
   - Number of clicks/keystrokes required
   - User satisfaction ratings

2. **Error Prevention**
   - Reduction in invalid config submissions
   - Reduction in support questions
   - Reduction in service failures due to bad configs

3. **Productivity**
   - Time to add new config (with vs. without templates)
   - Time to find and edit specific config (with vs. without search)
   - Number of configs managed per user

4. **Reliability**
   - File corruption incidents (should be zero)
   - Data loss incidents from unsaved changes
   - File lock conflicts

---

## Inspiration from Other Editors

### CSV Editors (Reference)
- **VisiData**: Advanced TUI with powerful filtering, sorting, statistics
- **csvkit**: Command-line CSV manipulation tools
- **Tabview**: Lightweight TUI CSV viewer
- **Rainbow CSV (VS Code)**: Column coloring, SQL queries on CSV

### General TUI/CLI Editors
- **Vim**: Powerful keybindings, modal editing, extensibility
- **Emacs**: Customization, advanced search/replace
- **Micro**: Modern TUI editor with intuitive keybindings
- **Helix**: Modern modal editor with LSP integration

### Features Worth Adopting
- Command palette (searchable command list)
- Regex search/replace
- Macro recording for repetitive tasks
- Syntax highlighting (for special columns)
- Mini-buffer for quick commands

---

## Contribution Guidelines

When implementing roadmap items:

1. **Create an issue** for the feature before starting
2. **Start with tests** (TDD approach)
3. **Keep changes minimal** (one feature per PR)
4. **Update documentation** in the same PR
5. **Add screenshots/demos** for UI changes
6. **Follow existing code style** (use textual patterns)
7. **Test with real configs** (not just unit tests)

---

## Questions & Decisions

Track open questions and design decisions:

| Question | Decision | Rationale |
|----------|----------|-----------|
| Should we support direct typing to edit cells? | TBD | Pro: More intuitive. Con: Conflicts with search keybindings |
| Should we add column reordering? | TBD | Pro: Flexibility. Con: Adds complexity, rarely needed |
| Should we integrate with git for version tracking? | TBD | Pro: Professional feature. Con: Assumes git is available |
| Should we support Excel-style formulas? | NO | Too complex, not aligned with CSV editing use case |
| Should we add graphing/visualization? | MAYBE | Could be useful for threshold_price analysis |

---

## Conclusion

This roadmap provides a structured approach to improving the CSV Editor over time. By prioritizing quick wins first, we can deliver value to users early while building toward more ambitious long-term features.

**Next Steps:**
1. Review and validate roadmap with stakeholders
2. Create GitHub issues for Phase 1 items
3. Prioritize based on user feedback and pain points
4. Start implementation with highest priority items

**Estimated Timeline:**
- Phase 1 (Quick Wins): 1-2 weeks
- Phase 2 (Medium-Term): 2-3 months
- Phase 3 (Long-Term): 6-12 months

---

*Last Updated: 2025-10-22*
*Maintainer: @copilot*
