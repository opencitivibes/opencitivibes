# Edit Approved Ideas - Phase 2: Frontend Notes

## Date: 2026-01-06

## Overview
Implemented frontend UI updates to support editing approved ideas with proper confirmation dialogs, status messaging, and handling for the new PENDING_EDIT status.

## Files Modified

### Types
- `frontend/src/types/index.ts`
  - Added `pending_edit` to `IdeaStatus` type
  - Added edit tracking fields to `Idea` interface: `edit_count`, `last_edit_at`, `previous_status`

### Components
- `frontend/src/components/Badge.tsx`
  - Added `pending_edit` variant with purple styling
  - Added Edit2 icon from lucide-react

- `frontend/src/components/EditApprovedIdeaDialog.tsx` (NEW)
  - Confirmation dialog for editing approved ideas
  - Shows warning about re-moderation requirement
  - Displays preserved votes/comments count
  - Shows remaining edits this month (3 - edit_count)
  - Requires explicit checkbox confirmation

- `frontend/src/components/pages/IdeaDetailClient.tsx`
  - Updated edit button to show for approved ideas (not just pending/rejected)
  - Hide edit button for pending_edit status
  - Added info alert for pending_edit status to owner
  - Updated Badge variant type assertion

### Pages
- `frontend/src/app/ideas/[id]/edit/page.tsx`
  - Removed block for approved ideas
  - Added confirmation dialog integration
  - Added info alert for approved ideas showing remaining edits
  - Added error handling for rate limit and cooldown errors
  - Block editing for pending_edit status (must wait for re-approval)

- `frontend/src/app/admin/page.tsx`
  - Added "Edited Idea" badge for pending_edit status
  - Shows edit count for edited ideas

### i18n
- `frontend/src/i18n/locales/en.json` - Added all EN translations
- `frontend/src/i18n/locales/fr.json` - Added all FR translations

## New i18n Keys Added
- `ideas.status.pending_edit`
- `ideas.cannotEditPendingEdit`
- `ideas.editApprovedTitle`
- `ideas.editApprovedWarning`
- `ideas.editApprovedInfo`
- `ideas.editApprovedConfirm`
- `ideas.editApprovedConfirmCheckbox`
- `ideas.editRemainingThisMonth`
- `ideas.editRateLimitError`
- `ideas.editCooldownError`
- `ideas.votesPreserved`
- `ideas.commentsPreserved`
- `ideas.ideaHiddenDuringReview`
- `ideas.pendingEditMessage`
- `admin.editedIdea`
- `admin.editCount`
- `admin.filterPendingEdit`

## Error Handling
- `edit_rate_limit` - Shows "You have reached the edit limit for this month"
- `edit_cooldown` - Shows "Please wait X hours before editing again"
- `cannot_edit_idea` - Shows "This idea is awaiting re-approval and cannot be edited"

## Validation Results
- ESLint: 0 errors
- TypeScript: 0 errors
- Build: Success
- Audit: 0 high/critical vulnerabilities
- Architecture checks: 0 violations (centralized API, no hardcoded URLs)

## UI/UX Decisions
1. Purple color chosen for pending_edit badge to differentiate from pending (yellow)
2. Confirmation dialog requires explicit checkbox to prevent accidental edits
3. Shows preserved data (votes, comments) to reassure users
4. Remaining edits displayed to help users plan

## Dependencies on Phase 1
- Backend endpoints updated to allow editing approved ideas
- PENDING_EDIT status added to backend IdeaStatus enum
- Edit tracking fields (edit_count, last_edit_at, previous_status) returned by API
- Rate limiting (3 edits/month) and cooldown (24h) enforced by backend

## Testing Notes
- Test editing approved idea → should show confirmation dialog
- Test editing pending/rejected idea → should work as before (no dialog)
- Test editing pending_edit idea → should redirect with error
- Test exceeding rate limit → should show rate limit error
- Test within cooldown period → should show cooldown error with hours remaining
- Verify admin sees "Edited Idea" badge and edit count
