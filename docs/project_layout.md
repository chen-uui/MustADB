# Project Layout

This workspace keeps runtime code paths unchanged and moves operational notes into clearer buckets.

## Root

- `ccc/`: main project sources
- `docs/`: design notes, reports, and layout references
- `scripts/`: manually-invoked utility scripts kept in place to avoid breaking existing habits
- `_archive/`: archived artifacts that should not be part of active runtime flows
- `.venv/`, `.serena/`, `.trae/`, `logs/`: environment and tool/runtime directories

## Reports

Generated audit, execution, and refactor reports now live under:

- `docs/reports/`

These files are documentation only and are not part of the application runtime.

## Archived Runtime Samples

Temporary validation samples are archived under:

- `_archive/runtime_samples/`

Current archived sample:

- `_archive/runtime_samples/runtime_reprocess_sample_2026-03-16/`

## Deliberately Unchanged Areas

The following directories remain where they are because moving them may affect runtime behavior or manual workflows:

- `ccc/astrobiology/backend/`
- `ccc/astrobiology/data/`
- `ccc/astrobiology/backend/media/`
- `ccc/astrobiology/backend/uploads/`
- root `scripts/`
- backend utility scripts next to `manage.py`

## Cleanup Rule

When new one-off reports or validation samples are created:

- place reports in `docs/reports/`
- place temporary runtime samples in `_archive/runtime_samples/`
- avoid adding new loose documentation files at the repository root
