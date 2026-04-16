import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Summarize manually annotated QA CSV into paper-support metrics."

    ANSWER_VALUES = ("correct", "incorrect", "unclear")
    SUPPORT_VALUES = ("supported", "partially_supported", "unsupported", "unclear")
    SUMMARY_COLUMNS = (
        "group_type",
        "group_value",
        "metric",
        "label",
        "count",
        "rate",
        "total_rows",
        "annotated_rows",
        "definition",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--in",
            dest="input_csv",
            type=str,
            required=True,
            help="Path to the annotated QA CSV.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/annotation_summary_<timestamp>/",
        )

    def handle(self, *args, **options):
        input_path = Path(str(options["input_csv"])).expanduser().resolve()
        if not input_path.exists():
            raise CommandError(f"annotated csv not found: {input_path}")

        rows = self._load_rows(input_path)
        if not rows:
            raise CommandError(f"annotated csv has no data rows: {input_path}")

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        summary_rows = self._build_summary_rows(rows)
        summary_csv_path = out_dir / "annotation_summary.csv"
        summary_md_path = out_dir / "annotation_summary.md"

        self._write_csv(summary_csv_path, summary_rows)
        summary_md_path.write_text(self._build_markdown(rows, summary_rows, input_path), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"summary_csv_path={summary_csv_path}"))
        self.stdout.write(self.style.SUCCESS(f"summary_md_path={summary_md_path}"))
        self.stdout.write(self.style.SUCCESS(f"rows={len(rows)}"))

    def _resolve_out_dir(self, path_arg: Optional[str]) -> Path:
        if path_arg and path_arg.strip():
            return Path(path_arg).expanduser().resolve()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"annotation_summary_{timestamp}").resolve()

    def _load_rows(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"sample_id", "mode", "answer_correct", "evidence_support", "unsupported_span_note"}
            missing = required.difference(set(reader.fieldnames or []))
            if missing:
                raise CommandError(f"annotated csv missing required columns: {sorted(missing)}")
            return [dict(row) for row in reader]

    def _build_summary_rows(self, rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
        groups: List[Tuple[str, str, List[Dict[str, str]]]] = [("overall", "all", list(rows))]
        by_mode: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        for row in rows:
            mode = self._clean(row.get("mode", "")) or "unknown"
            by_mode[mode].append(row)
        for mode, mode_rows in sorted(by_mode.items()):
            groups.append(("mode", mode, mode_rows))

        summary_rows: List[Dict[str, str]] = []
        for group_type, group_value, group_rows in groups:
            summary_rows.extend(self._summarize_answer_accuracy(group_type, group_value, group_rows))
            summary_rows.extend(self._summarize_evidence_support(group_type, group_value, group_rows))
            summary_rows.extend(self._summarize_unsupported_metrics(group_type, group_value, group_rows))
        return summary_rows

    def _summarize_answer_accuracy(
        self,
        group_type: str,
        group_value: str,
        rows: Sequence[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        normalized = [self._normalize_answer_correct(row.get("answer_correct")) for row in rows]
        annotated = [value for value in normalized if value is not None]
        counts = Counter(annotated)
        result_rows: List[Dict[str, str]] = []
        for label in self.ANSWER_VALUES:
            result_rows.append(
                self._summary_row(
                    group_type=group_type,
                    group_value=group_value,
                    metric="answer_accuracy",
                    label=label,
                    count=counts.get(label, 0),
                    annotated_rows=len(annotated),
                    total_rows=len(rows),
                    definition="Manual answer-accuracy label distribution over annotated rows.",
                )
            )
        return result_rows

    def _summarize_evidence_support(
        self,
        group_type: str,
        group_value: str,
        rows: Sequence[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        normalized = [self._normalize_evidence_support(row.get("evidence_support")) for row in rows]
        annotated = [value for value in normalized if value is not None]
        counts = Counter(annotated)
        result_rows: List[Dict[str, str]] = []
        for label in self.SUPPORT_VALUES:
            result_rows.append(
                self._summary_row(
                    group_type=group_type,
                    group_value=group_value,
                    metric="evidence_support_rate",
                    label=label,
                    count=counts.get(label, 0),
                    annotated_rows=len(annotated),
                    total_rows=len(rows),
                    definition="Manual evidence-support label distribution over annotated rows.",
                )
            )
        return result_rows

    def _summarize_unsupported_metrics(
        self,
        group_type: str,
        group_value: str,
        rows: Sequence[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        support_values = [self._normalize_evidence_support(row.get("evidence_support")) for row in rows]
        support_annotated = [value for value in support_values if value is not None]
        unsupported_count = sum(1 for value in support_annotated if value == "unsupported")
        span_annotated = [row for row in rows if self._clean(row.get("unsupported_span_note", "")) != ""]

        return [
            self._summary_row(
                group_type=group_type,
                group_value=group_value,
                metric="unsupported_output_rate",
                label="unsupported_by_evidence_support",
                count=unsupported_count,
                annotated_rows=len(support_annotated),
                total_rows=len(rows),
                definition="Manual proxy: proportion of rows labeled evidence_support=unsupported.",
            ),
            self._summary_row(
                group_type=group_type,
                group_value=group_value,
                metric="unsupported_span_marked_rate",
                label="rows_with_unsupported_span_note",
                count=len(span_annotated),
                annotated_rows=len(rows),
                total_rows=len(rows),
                definition="Share of rows where annotators wrote any unsupported span note.",
            ),
        ]

    def _summary_row(
        self,
        *,
        group_type: str,
        group_value: str,
        metric: str,
        label: str,
        count: int,
        annotated_rows: int,
        total_rows: int,
        definition: str,
    ) -> Dict[str, str]:
        rate = 0.0 if annotated_rows <= 0 else count / annotated_rows
        return {
            "group_type": group_type,
            "group_value": group_value,
            "metric": metric,
            "label": label,
            "count": str(count),
            "rate": f"{rate:.4f}",
            "total_rows": str(total_rows),
            "annotated_rows": str(annotated_rows),
            "definition": definition,
        }

    def _write_csv(self, path: Path, rows: Iterable[Dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.SUMMARY_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _build_markdown(
        self,
        rows: Sequence[Dict[str, str]],
        summary_rows: Sequence[Dict[str, str]],
        input_path: Path,
    ) -> str:
        lines = [
            "# QA Annotation Summary",
            "",
            f"- Input CSV: `{input_path}`",
            f"- Total rows: `{len(rows)}`",
            "",
            "## Metric Definitions",
            "- `answer_accuracy`: manual label distribution over `answer_correct` (`1/0/unclear`).",
            "- `evidence_support_rate`: manual label distribution over `evidence_support` (`supported/partially_supported/unsupported/unclear`).",
            "- `unsupported_output_rate`: manual proxy defined as the proportion of rows where `evidence_support = unsupported`.",
            "- `unsupported_span_marked_rate`: share of rows with a non-empty `unsupported_span_note`.",
            "",
            "## Summary",
            "",
            "| group_type | group_value | metric | label | count | rate | annotated_rows |",
            "|---|---|---|---|---:|---:|---:|",
        ]
        for row in summary_rows:
            lines.append(
                f"| {row['group_type']} | {row['group_value']} | {row['metric']} | {row['label']} | "
                f"{row['count']} | {row['rate']} | {row['annotated_rows']} |"
            )
        lines.append("")
        return "\n".join(lines)

    def _normalize_answer_correct(self, value: Optional[str]) -> Optional[str]:
        text = self._clean(value).lower()
        if not text:
            return None
        if text in {"1", "true", "yes", "correct"}:
            return "correct"
        if text in {"0", "false", "no", "incorrect"}:
            return "incorrect"
        if text == "unclear":
            return "unclear"
        return None

    def _normalize_evidence_support(self, value: Optional[str]) -> Optional[str]:
        text = self._clean(value).lower()
        if not text:
            return None
        if text in set(self.SUPPORT_VALUES):
            return text
        return None

    def _clean(self, value: Optional[str]) -> str:
        return str(value or "").strip()
