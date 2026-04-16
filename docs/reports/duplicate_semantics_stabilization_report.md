# Duplicate Semantics Stabilization Report

## 1. Actual files added or modified

Added:

- `D:\workspace\123\docs\reports\duplicate_upload_semantics.md`
- `D:\workspace\123\docs\reports\duplicate_semantics_stabilization_report.md`

Modified:

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\models.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\upload_storage_service.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views_user_upload.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

Not modified:

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views_review.py`

## 2. New developer documentation

Added `D:\workspace\123\docs\reports\duplicate_upload_semantics.md`.

It now documents:

- the exact meaning of `PDFDocument.duplicate_of`
- which entry points already perform hash inspection
- why user upload and Weaviate upload intentionally have different duplicate-hit semantics
- which behaviors are controlled changes versus intentionally unchanged
- why the codebase is not moving to `UploadEvent / ReviewAction` yet

## 3. Comments added

Added targeted semantic comments only where the code would otherwise be easy to misread:

- `models.py`
  - clarified that `duplicate_of` is a short-term bridge between content ownership and fresh review actions
- `upload_storage_service.py`
  - documented canonical duplicate-chain resolution
  - documented why duplicate lookup prefers rows with `duplicate_of is null`
  - documented that duplicate/filename-conflict log tokens are intentionally stable for smoke checks and ops triage
- `views_user_upload.py`
  - clarified that duplicate-hit user uploads still create a new pending review action while reusing the canonical physical file
- `weaviate_views.py`
  - clarified why Weaviate upload can safely short-circuit to an existing record while user upload cannot

No broad comment sweep was done.

## 4. Tests and assertions added

Strengthened `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py` with minimal assertions only:

- user upload filename-conflict path now asserts the stable `filename_conflict=True` log token
- user upload duplicate-hit path now asserts the stable `user_upload_duplicate_hit` log token
- Weaviate duplicate-hit path now asserts the stable `weaviate_existing_hit` log token
- existing coverage for:
  - user duplicate-hit pending action creation
  - duplicate-hit pending item visibility
  - duplicate-hit approve/reject isolation from the canonical parent
  - shared `file_path` download compatibility
  - Phase 1 / 2A / 2B smoke checks
  remains intact

One smoke harness mock had to be updated to include `filename` after the new Weaviate log line started referencing that field. That was a test-fixture compatibility fix, not a runtime behavior fix.

## 5. Logs and observability added

Added or stabilized the following machine-searchable log markers:

- `user_upload_duplicate_hit`
  - emitted when user upload hits `different name + same content` and reuses the canonical file while still creating a new pending `PDFDocument`
- `weaviate_existing_hit`
  - emitted for Weaviate upload short-circuits
  - includes `reason=same_filename` or `reason=duplicate_content`
- `filename_conflict=True`
  - continues to come from `UploadStorageService.log_duplicate_inspection(...)`

These changes do not alter response payloads or business branching; they only make duplicate scenarios easier to trace consistently across entry points.

## 6. Behavior change check

Expected behavior change for this round: none.

Observed result:

- no API route changes
- no HTTP method changes
- no payload structure changes
- no model semantics changes beyond better documentation
- no review-flow behavior changes
- no file movement, deletion, or migration

The only runtime-visible difference is more explicit logging text for duplicate-hit and existing-hit scenarios.

## 7. Validation results

Pre-change baseline:

- `upload_storage_smoke_check.py`: `24 pass / 0 fail / 0 error`

Post-change validation:

- `py -m py_compile` on the touched backend files: passed
- `upload_storage_smoke_check.py`: `24 pass / 0 fail / 0 error`

During the first post-change run, one smoke check failed because a test mock lacked `filename` after the Weaviate log line began including it. After fixing that test fixture, the full smoke suite returned to green with no runtime regression.

## 8. Submission readiness

This duplicate/upload-review line is now in a good state to stop and submit:

- semantics are documented
- the duplicate bridge field is explained where it matters
- the two duplicate-hit behaviors are easier to distinguish operationally
- the smoke suite now checks the most important duplicate observability tokens
- no business behavior changed in this round

Recommendation: safe to submit this stabilization batch before any further upload/review model work.
