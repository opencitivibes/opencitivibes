# Notes: Edit Approved Ideas Phase 1 - Backend

**Date:** 2026-01-06
**Status:** COMPLETED ✅

## Summary

Implemented backend support for editing approved ideas with automatic re-moderation. Users can now edit their approved ideas (with rate limits), and edits trigger a re-moderation workflow while preserving votes and comments.

## Changes Made

### Database Schema
- Added `PENDING_EDIT` status to `IdeaStatus` enum in `db_models.py:52`
- Added edit tracking columns to `Idea` model (`db_models.py:348-364`):
  - `edit_count`: Integer, default 0
  - `last_edit_at`: DateTime, nullable
  - `previous_status`: String(20), nullable

### Domain Exceptions
- Added to `exceptions.py:510-556`:
  - `IdeaEditException` - Base class
  - `EditRateLimitException` - Max 3 edits/month exceeded
  - `EditCooldownException` - 24 hours between edits
  - `CannotEditIdeaException` - Idea in PENDING_EDIT status

### Repository Methods
- Added to `idea_repository.py:1560-1758`:
  - `get_edit_count_this_month()` - Get edits for current month
  - `update_edit_tracking()` - Update tracking fields and transition status
  - `get_pending_edits()` - Get ideas awaiting re-moderation
  - `count_pending_edits()` - Count pending edit reviews
  - `restore_previous_status()` - Restore status after approval

### Service Layer
- Modified `IdeaService.update_idea()` (`idea_service.py:238-384`):
  - Allow editing APPROVED ideas (previously only PENDING/REJECTED)
  - Rate limiting: max 3 edits per month per idea
  - Cool-down: 24 hours between edits
  - Transition to PENDING_EDIT status
  - Store previous_status for restoration
- Modified `IdeaService.moderate_idea()` (`idea_service.py:535-593`):
  - Handle PENDING_EDIT status
  - Approval: restore to previous status, preserve votes/comments
  - Rejection: set to REJECTED, preserve previous_status for history

### Schemas
- Updated `IdeaWithScore` schema (`schemas.py:398-405`) with edit tracking fields

### Migration
- Created `e8gk77h64i9f_add_edit_tracking.py` with:
  - Add `edit_count`, `last_edit_at`, `previous_status` columns
  - SQLite-compatible (no ALTER TYPE needed)

### Tests
- Created `test_idea_edit_workflow.py` with 19 tests covering:
  - Edit rate limiting
  - Cool-down period
  - Status transitions
  - Visibility rules
  - Vote/comment preservation

## Validation Results

**Task Validator:** ✅ APPROVED

- Ruff: ✅ PASS
- Pyright: ✅ PASS
- Bandit: ✅ PASS (0 security issues)
- Architecture scripts: ✅ PASS (0 violations)
- Tests: ✅ 19/19 PASSING

## Business Rules Implemented

1. **Rate Limiting:** Max 3 edits per month per idea (resets monthly)
2. **Cool-down:** Must wait 24 hours between edits
3. **Status Flow:**
   - APPROVED → PENDING_EDIT (on edit)
   - PENDING_EDIT → APPROVED (on approval)
   - PENDING_EDIT → REJECTED (on rejection)
4. **Visibility:** PENDING_EDIT ideas hidden from public but visible to owner
5. **Preservation:** Votes and comments preserved during re-moderation

## Next Steps

Phase 2: Frontend - Edit UI
- Add edit button for approved ideas (owner only)
- Show edit limit/cooldown status
- Handle PENDING_EDIT status display
- Add admin queue filter for edited ideas
