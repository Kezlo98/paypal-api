# Frontend Integration Plan - Quick Start

## Objective
Integrate static HTML portfolio landing page into PayPal API FastAPI project with live API integration on finance page.

## Approach
- FastAPI StaticFiles mount (no nginx, no frameworks, no build step)
- Portfolio pages (index, journey) stay static
- Finance page connects to live `/api/v1/paypal/*` endpoints via vanilla JavaScript

## Files

### Main Plan
- **`plan.md`** - Comprehensive implementation plan with 6 phases, code samples, testing strategy

### References
- **Brainstorm report:** `../reports/brainstorm-251229-2028-frontend-integration.md`
- **Source location:** `/Users/nam/galaxy/sonbip/landing page/`

## Quick Implementation Steps

1. **Backend (15 min):** Add StaticFiles mount and HTML routes to `app/main.py`
2. **Migration (10 min):** Copy HTML/assets to new `static/` directory
3. **Path updates (20 min):** Fix asset paths in HTML files
4. **finance.js (45 min):** Create API integration module
5. **HTML updates (20 min):** Add loading/error UI to finance.html
6. **Testing (30 min):** Manual + automated testing

**Total:** ~2-3 hours

## Key Design Decisions

- ✅ Same-origin deployment (no CORS issues)
- ✅ Vanilla JS (no React/Vue overhead)
- ✅ No authentication (MVP scope)
- ✅ Last 30 days default range
- ✅ 20 transactions max (no pagination MVP)

## Success Metrics

- All pages load correctly at `http://localhost:8000/`
- Finance page displays live PayPal balance and transactions
- Navigation works across all pages
- No console errors
- Tests pass: `pytest tests/test_static_routes.py`

## Start Implementation

```bash
# Create feature branch
git checkout -b feature/frontend-integration

# Follow plan.md phases 1-6

# Test
uvicorn app.main:app --reload
# Open: http://localhost:8000/finance.html

# Run tests
pytest tests/test_static_routes.py -v
```

## Rollback

```bash
# If issues arise
git checkout main
git branch -D feature/frontend-integration
rm -rf static/
# Revert app/main.py changes
```

---

**Status:** READY FOR IMPLEMENTATION
**Created:** 2025-12-29 20:28
**Estimated effort:** 2-3 hours
