# Duplicate Upload Semantics

## Current bridge

`PDFDocument.duplicate_of` is the current transition mechanism for duplicate-hit
user uploads.

- `duplicate_of is null`: the row owns the canonical physical file and content
  hash.
- `duplicate_of is not null`: the row represents a new review action that
  reuses the canonical file and `sha1` from the parent record.

This keeps the current review workflow intact without introducing new long-term
models yet.

## Hash detection coverage

Content-hash inspection is currently centralized in
`UploadStorageService.inspect_uploaded_file()` and used by:

- `views_user_upload.py`
- `views/direct_processing_views.py`
- `weaviate_views.py`

The helper reports:

- `duplicate_detected`
- `duplicate_document_id`
- `filename_conflict`
- `filename_conflict_same_content`

## Entry-point semantics

### User upload

User upload treats a duplicate hit as both:

- a repeated file content event
- and a fresh review action

So for `different name + same content`:

- no new physical file is written
- a new pending `PDFDocument` is still created
- the new row points to the canonical content row via `duplicate_of`
- the new row keeps the current upload filename and uploader context

For `same name + same content` and `same name + different content`, the existing
filename guard still wins.

### Weaviate upload

Weaviate upload does not create a separate review action, so it can safely
short-circuit to an existing record.

- `same name + same content`: return the existing document
- `different name + same content`: return the canonical existing document
- `same name + different content`: keep the existing filename guard behavior

This is intentionally different from user upload.

## Controlled changes vs unchanged behavior

### Controlled changes already introduced

- User upload `different name + same content` now reuses the canonical file
  instead of writing a second copy.
- Weaviate upload `different name + same content` now returns an existing hit
  instead of creating a duplicate record.

### Behavior intentionally unchanged

- API routes, methods, and payload shapes
- direct processing semantics
- review approval/rejection semantics
- automatic indexing semantics after review
- historical file layout and old file-path compatibility

## Why not UploadEvent / ReviewAction yet

The current duplicate handling still fits within `PDFDocument` with a small,
local bridge field. Introducing `UploadEvent` or `ReviewAction` now would force
broader migration work across review queues, response semantics, and reporting.

That longer-term split is still a valid direction, but the current priority is
to stabilize the landed `duplicate_of` behavior and keep the chain observable.
