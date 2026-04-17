# MustADB

GitHub repository: `https://github.com/chen-uui/MustADB`

This repository contains the public release codebase and curated manuscript-support materials for a PNAS Nexus submission on astrobiology literature retrieval and extraction. The runtime application lives in `ccc/astrobiology/`. A curated, smaller evidence bundle for manuscript traceability lives in `submission_backup/`.

## Included In This Public Release

- Application source code for the Django backend and Vue frontend.
- Dependency manifests and environment templates needed to inspect or deploy the software.
- Curated benchmark, result-summary, and annotation artifacts under `submission_backup/` that support manuscript traceability.
- Release-facing documentation in this repository root, including `PAPER_RESULTS_MAP.md` and `RELEASE_CHECKLIST.md`.
- Apache-2.0 licensing in `LICENSE`.

## Not Included In This Public Release

- Local `.env` files, secrets, tokens, and machine-specific launch settings.
- The manuscript PDF, the working PDF corpus, raw literature PDFs, vector-store data, uploaded files, model weights, and local runtime logs.
- Full local benchmark work directories under `ccc/astrobiology/backend/runs/` and `ccc/astrobiology/backend/evaluation/`; the curated manuscript-facing subset is provided in `submission_backup/` instead.

Raw literature PDFs should not be redistributed through this repository unless the authors confirm they have redistribution rights. The public release is designed to point to curated derived artifacts rather than ship the full source corpus.

## Repository Layout

- `ccc/astrobiology/astro_frontend/`: Vue 3 + Vite frontend.
- `ccc/astrobiology/backend/`: Django backend, APIs, and evaluation commands.
- `submission_backup/`: curated manuscript-traceability package with retained benchmark, summary, and annotation files.
- `docs/`: development notes and historical reports; these are not part of the release-critical runtime path.
- `manage.py`: repo-level proxy to `ccc/astrobiology/backend/manage.py`.

## Minimal Local Inspection

Minimal inspection does not require the full runtime stack.

1. Read this `README.md`.
2. Review `PAPER_RESULTS_MAP.md` for manuscript-to-artifact mapping.
3. Inspect `submission_backup/README.md` and the retained files under `submission_backup/`.
4. Review `.env.example`, `ccc/astrobiology/backend/requirements.txt`, and `ccc/astrobiology/astro_frontend/package.json` for dependencies and configuration shape.

## Full System Deployment

The full interactive system expects local infrastructure that is intentionally not bundled in this public release:

- Python 3.10+
- Node.js 18+
- PostgreSQL
- Docker / Docker Desktop
- Weaviate + `text2vec-transformers`
- Ollama for the default local LLM path

Backend setup:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r ccc/astrobiology/backend/requirements.txt
copy .env.example ccc/astrobiology/.env
python manage.py migrate
python manage.py runserver
```

Frontend setup:

```bash
cd ccc/astrobiology/astro_frontend
npm install
npm run dev
```

The Windows helper launchers in `ccc/astrobiology/backend/start_backend.bat` and `ccc/astrobiology/astro_frontend/start_frontend.bat` now use relative paths instead of machine-specific absolute paths.

## Result Traceability And Reproduction

This release separates reproducibility into two levels:

- `submission_backup/` supports manuscript result inspection and traceability using curated retained inputs, summaries, and annotations.
- The full live workspace contains larger local-only assets used during development and experimentation, but those are intentionally excluded from the public release.

The main traceability entry points are:

- `PAPER_RESULTS_MAP.md`
- `submission_backup/README.md`
- `submission_backup/09_archive_manifest/paper_results_traceability.md`
- `submission_backup/09_archive_manifest/missing_items.md`

## Current Known Limits

- The repository does not contain the full raw PDF corpus for copyright and size reasons.
- Some benchmark construction inputs originally lived outside the repository and are documented as missing in `submission_backup/09_archive_manifest/missing_items.md`.
- The archival Zenodo DOI is not yet included in `CITATION.cff` and can be added after the first GitHub release is archived.
