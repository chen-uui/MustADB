import csv
from pathlib import Path
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Merge manually annotated retrieval-qrels expansion rows into an existing qrels CSV."

    POSITIVE_VALUES = {"1", "yes", "y", "true", "relevant"}
    NEGATIVE_VALUES = {"0", "no", "n", "false", "not_relevant", "not relevant"}
    OUTPUT_COLUMNS = ("qid", "question", "mode", "rank", "doc_id", "doc_name", "is_relevant", "notes")

    def add_arguments(self, parser):
        parser.add_argument("--existing-qrels", type=str, required=True, help="Existing seed qrels CSV.")
        parser.add_argument("--annotated-candidates", type=str, required=True, help="Annotated candidate-doc CSV.")
        parser.add_argument(
            "--mode",
            type=str,
            default="hybrid_rerank",
            help="Mode label to write into merged qrels rows. Default: hybrid_rerank.",
        )
        parser.add_argument("--out", type=str, required=True, help="Merged output CSV path.")

    def handle(self, *args, **options):
        existing_path = Path(str(options["existing_qrels"])).expanduser().resolve()
        annotated_path = Path(str(options["annotated_candidates"])).expanduser().resolve()
        out_path = Path(str(options["out"])).expanduser().resolve()
        mode = str(options["mode"]).strip()

        if not existing_path.exists():
            raise CommandError(f"existing qrels not found: {existing_path}")
        if not annotated_path.exists():
            raise CommandError(f"annotated candidates not found: {annotated_path}")

        existing_rows = self._read_csv(existing_path)
        annotated_rows = self._read_csv(annotated_path)
        new_rows = self._convert_annotated_rows(annotated_rows, mode=mode)

        merged_rows = existing_rows + new_rows
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.OUTPUT_COLUMNS)
            writer.writeheader()
            for row in merged_rows:
                writer.writerow(row)

        self.stdout.write(self.style.SUCCESS(f"merged_qrels_csv={out_path}"))
        self.stdout.write(self.style.SUCCESS(f"existing_rows={len(existing_rows)}"))
        self.stdout.write(self.style.SUCCESS(f"new_rows={len(new_rows)}"))
        self.stdout.write(self.style.SUCCESS(f"total_rows={len(merged_rows)}"))

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _convert_annotated_rows(self, rows: List[Dict[str, str]], *, mode: str) -> List[Dict[str, str]]:
        converted: List[Dict[str, str]] = []
        for row in rows:
            raw_label = str(row.get("candidate_relevance", "")).strip().lower()
            if raw_label not in self.POSITIVE_VALUES:
                continue

            converted.append(
                {
                    "qid": str(row.get("new_qid", "")).strip(),
                    "question": str(row.get("query", "")).strip(),
                    "mode": mode,
                    "rank": str(row.get("rank", "")).strip(),
                    "doc_id": str(row.get("document_id", "")).strip(),
                    "doc_name": str(row.get("document_title", "")).strip(),
                    "is_relevant": "yes",
                    "notes": str(row.get("annotation_note", "")).strip(),
                }
            )
        return converted
