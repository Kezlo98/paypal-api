# Fix Report: Default Date Range to 1 Year Ago

**Date:** 2025-12-29
**Type:** Fix
**Status:** ✅ Fixed
**File Modified:** `static/assets/js/finance.js`

---

## Issue

Default date range was incorrectly set to "now to 2 years from now" instead of "1 year ago to now".

---

## Root Cause

`setDefaultDateRange()` function calculated:
- Start: Current date/time
- End: Current date + 2 years

**Before:**
```javascript
const now = new Date();
const twoYearsFromNow = new Date();
twoYearsFromNow.setFullYear(now.getFullYear() + 2);

currentDateRange.startDate = now.toISOString();
currentDateRange.endDate = twoYearsFromNow.toISOString();
```

**Problem:**
- Shows future transactions (doesn't exist yet)
- Incorrect date range for historical data
- Confusing for users

---

## Solution

Changed to 1 year ago to now:
- Start: Current date - 1 year
- End: Current date/time

**After:**
```javascript
const now = new Date();
const oneYearAgo = new Date();
oneYearAgo.setFullYear(now.getFullYear() - 1);

currentDateRange.startDate = oneYearAgo.toISOString();
currentDateRange.endDate = now.toISOString();
```

---

## Changes Made

**File:** `static/assets/js/finance.js`

**Updated:**
1. `setDefaultDateRange()` function (line 343-361)
2. `resetFilters()` comment (line 390)
3. Initialization comment (line 406)

**Variable changes:**
- `twoYearsFromNow` → `oneYearAgo`
- `now.getFullYear() + 2` → `now.getFullYear() - 1`

---

## Date Range Examples

### Before (Incorrect)

**On 2025-12-29:**
- Start: `2025-12-29T21:49:00Z` (now)
- End: `2027-12-29T21:49:00Z` (2 years from now)
- Range: 730 days into the future ❌

### After (Correct)

**On 2025-12-29:**
- Start: `2024-12-29T21:49:00Z` (1 year ago)
- End: `2025-12-29T21:49:00Z` (now)
- Range: 365 days of historical data ✅

---

## Benefits

✅ **Correct historical range** - Shows past year of transactions
✅ **Immediate data** - Loads real transactions on page load
✅ **User-friendly** - Expected behavior for financial tracking
✅ **No future dates** - Only shows actual transactions

---

## Format Details

**ISO 8601 format maintained:**
```
2024-12-29T21:49:00.000Z  (1 year ago)
2025-12-29T21:49:00.000Z  (now)
```

**datetime-local format (for inputs):**
```
2024-12-29T21:49  (1 year ago)
2025-12-29T21:49  (now)
```

**Conversion handled by:**
- `toISOString()` - JavaScript → API
- `toDatetimeLocal()` - API → input field

---

## Impact

**Before:**
- Empty transaction list (no future transactions)
- Confusing date range
- Required manual date change

**After:**
- Shows last year of transactions
- Intuitive date range
- Works out of the box

---

## Testing

**Page load:**
```bash
open http://localhost:8000/finance.html
```

**Verify:**
1. ✅ Start date input shows 1 year ago
2. ✅ End date input shows current date/time
3. ✅ Transactions load automatically
4. ✅ Date range display shows "Dec 29, 2024 - Dec 29, 2025"

**Reset button:**
1. Change dates manually
2. Click "Reset" button
3. ✅ Dates return to 1 year ago - now

---

## Code Comments Updated

All comments now reflect "1 year ago to now":
- Function JSDoc
- Inline comments
- Initialization comments

---

## Related Functionality

**Date range splitting:**
- If range > 31 days, backend splits automatically
- 365 days = ~12 chunks
- Parallel requests for faster loading

**User customization:**
- Can still select any date range
- Reset button returns to default (1 year)
- Date inputs allow full customization

---

## Unresolved Questions

None. Fix complete and tested.
