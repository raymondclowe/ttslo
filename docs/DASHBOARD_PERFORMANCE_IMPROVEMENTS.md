# Dashboard Performance Improvements

## Problem
The dashboard had two major UX issues:
1. **Slow to populate** - Loading data took a long time
2. **Misleading empty panes** - When refreshing, the middle pane would clear out old data before loading new data, leaving it empty for several seconds and giving a false impression that there was no data

## Solution Implemented

### 1. Non-Destructive Refresh Pattern
Changed all three fetch functions (`fetchPendingOrders`, `fetchActiveOrders`, `fetchCompletedOrders`) to:
- **Keep existing data visible** during refresh
- Only update the DOM **after** new data arrives from the API
- Show a subtle "Refreshing..." overlay on top of existing content

### 2. Loading Overlay Helper
Added `showLoadingOverlay()` function that:
- Only shows overlay if there's existing data (`.order-card` elements)
- Prevents duplicate overlays
- Uses a semi-transparent overlay with `pointer-events: none` so it doesn't block interaction
- Positioned absolutely within the pane content

### 3. CSS Improvements
- Added `position: relative` to `.pane-content` to support absolute overlay positioning
- Created `.loading-overlay` class with:
  - Semi-transparent white background (rgba(255, 255, 255, 0.8))
  - Centered "Refreshing..." text
  - `pointer-events: none` to avoid blocking UI
  - `z-index: 10` to ensure visibility

### 4. Better Error Handling
- Added HTTP response validation (`response.ok` check)
- More informative error messages with HTTP status codes
- Null-safe operations on DOM elements

## Key Changes

### Before:
```javascript
async function fetchPendingOrders() {
    const response = await fetch('/api/pending');
    const orders = await response.json();
    
    const content = document.getElementById('pending-content');
    content.innerHTML = /* new content */;  // ← Clears immediately
}
```

### After:
```javascript
async function fetchPendingOrders() {
    const content = document.getElementById('pending-content');
    
    showLoadingOverlay(content);  // ← Show overlay over existing data
    
    const response = await fetch('/api/pending');
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const orders = await response.json();
    
    if (content) {
        content.innerHTML = /* new content */;  // ← Updates only after data arrives
    }
}
```

## Benefits
1. **Better UX** - Users always see data, never a misleading empty state
2. **Visual feedback** - "Refreshing..." overlay clearly indicates an update is in progress
3. **Smoother transitions** - Data appears to update in place rather than flickering
4. **Error resilience** - Better error handling and null-safety

## Files Modified
- `templates/dashboard.html`
  - Added `.loading-overlay` CSS
  - Added `position: relative` to `.pane-content`
  - Added `showLoadingOverlay()` helper function
  - Refactored `fetchPendingOrders()` to use overlay pattern
  - Refactored `fetchActiveOrders()` to use overlay pattern
  - Refactored `fetchCompletedOrders()` to use overlay pattern
  - Added HTTP response validation to all fetch functions

## Performance Note
The backend slowness (Kraken API calls) remains unchanged. These improvements only address the **perceived** performance by keeping the UI responsive and informative during slow data fetches.

## Future Improvements (Not Implemented)
To actually improve backend speed, consider:
1. **Caching** - Add short-term caching for Kraken API responses
2. **Parallel optimization** - Ensure all API calls happen in parallel (already done with `Promise.all`)
3. **WebSocket updates** - Use WebSocket for price data instead of polling
4. **Rate limiting awareness** - Implement backoff strategies for API rate limits
