# Release Checklist

## Required Before Public Tag

- Review `submission_backup/09_archive_manifest/missing_items.md` and confirm that the listed gaps are acceptable for publication.
- After creating the Zenodo snapshot, add the archival DOI to `CITATION.cff`.
- Confirm that no third-party raw literature PDFs or restricted annotation files are being redistributed.

## Repository Safety

- Verify there are no committed `.env` files, tokens, passwords, or local absolute paths in release-facing files.
- Confirm that the frontend no longer depends on a hard-coded bearer token.
- Confirm that no bootstrap script creates public default credentials unless the user opts in through environment variables.

## Reproducibility

- Confirm that `submission_backup/` contains the exact benchmark/result subset intended to support the manuscript.
- Confirm that `PAPER_RESULTS_MAP.md` matches the final manuscript tables/figures or update it with exact numbering.
- Run `python scripts/create_submission_backup.py --skip-zip` after any traceability-file change.

## Documentation

- Re-read `README.md` from the perspective of a first-time external user.
- Confirm that deployment, inspection, and result-traceability workflows are clearly separated.
- Confirm that the repository description and manuscript availability statements match the final public scope.
