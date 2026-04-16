import csv
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Merge official gold with batch1_final, write gold_seed_v2, and rerun fixed-version extraction evaluation."

    OUTPUT_COLUMNS = [
        "doc_id",
        "doc_name",
        "pred_meteorite_name",
        "pred_organic_compounds",
        "pred_contamination_controls",
        "in_scope",
        "skip_row",
        "notes",
        "gold_meteorite_name",
        "gold_organic_compounds",
        "gold_contamination_controls",
    ]
    SUMMARY_FIELDS = (
        "meteorite_name",
        "organic_compounds",
        "contamination_controls",
        "overall_macro_avg",
    )

    def add_arguments(self, parser):
        parser.add_argument("--base-gold", type=str, required=True, help="Current official gold_seed.csv path.")
        parser.add_argument("--batch-gold", type=str, required=True, help="Final batch1 CSV path.")
        parser.add_argument(
            "--base-fixed-csv",
            type=str,
            default=None,
            help="Existing fixed-version rerun CSV for the current official gold. Default: runs/gold_raw_recall_20260312_v2/raw_recall_improved/gold_seed_rerun.csv",
        )
        parser.add_argument(
            "--gold-out-csv",
            type=str,
            default=None,
            help="Merged gold CSV output path. Default: evaluation/gold_seed_v2.csv",
        )
        parser.add_argument(
            "--gold-out-xlsx",
            type=str,
            default=None,
            help="Merged gold XLSX output path. Default: evaluation/gold_seed_v2.xlsx",
        )
        parser.add_argument(
            "--out-dir",
            type=str,
            default=None,
            help="Evaluation output directory. Default: runs/gold_v2_eval_<timestamp>",
        )

    def handle(self, *args, **options):
        base_gold_path = Path(str(options["base_gold"])).expanduser().resolve()
        batch_gold_path = Path(str(options["batch_gold"])).expanduser().resolve()
        base_fixed_csv_path = self._resolve_base_fixed_csv(options.get("base_fixed_csv"))
        if not base_gold_path.exists():
            raise CommandError(f"base gold not found: {base_gold_path}")
        if not batch_gold_path.exists():
            raise CommandError(f"batch gold not found: {batch_gold_path}")
        if not base_fixed_csv_path.exists():
            raise CommandError(f"base fixed csv not found: {base_fixed_csv_path}")

        gold_out_csv = self._resolve_gold_csv_path(options.get("gold_out_csv"))
        gold_out_xlsx = self._resolve_gold_xlsx_path(options.get("gold_out_xlsx"))
        out_dir = self._resolve_out_dir(options.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)
        gold_out_csv.parent.mkdir(parents=True, exist_ok=True)
        gold_out_xlsx.parent.mkdir(parents=True, exist_ok=True)

        base_rows = self._read_csv(base_gold_path)
        batch_rows = self._read_csv(batch_gold_path)
        base_fixed_rows = self._read_csv(base_fixed_csv_path)

        merged_rows, duplicate_rows = self._merge_rows(base_rows, batch_rows)
        self._write_csv(gold_out_csv, self.OUTPUT_COLUMNS, merged_rows)
        self._write_xlsx(gold_out_xlsx, "GoldSeedV2", self.OUTPUT_COLUMNS, merged_rows)

        merged_fixed_eval_rows, fixed_duplicate_rows = self._merge_rows(base_fixed_rows, batch_rows)
        merged_fixed_eval_csv = out_dir / "gold_seed_v2_fixed_eval_input.csv"
        merged_fixed_eval_xlsx = out_dir / "gold_seed_v2_fixed_eval_input.xlsx"
        self._write_csv(merged_fixed_eval_csv, self.OUTPUT_COLUMNS, merged_fixed_eval_rows)
        self._write_xlsx(merged_fixed_eval_xlsx, "GoldSeedV2Eval", self.OUTPUT_COLUMNS, merged_fixed_eval_rows)

        old_eval_dir = out_dir / "old_gold_fixed_eval"
        new_eval_dir = out_dir / "new_gold_v2_fixed_eval"
        comparison_csv_path = out_dir / "before_after_comparison.csv"
        summary_json_path = out_dir / "gold_v2_eval_summary.json"
        summary_md_path = out_dir / "gold_v2_eval_summary.md"

        call_command("eval_extraction_accuracy", gold=str(base_fixed_csv_path), out=str(old_eval_dir))
        call_command("eval_extraction_accuracy", gold=str(merged_fixed_eval_csv), out=str(new_eval_dir))

        old_summary = self._load_summary_rows(old_eval_dir / "accuracy_summary.csv")
        new_summary = self._load_summary_rows(new_eval_dir / "accuracy_summary.csv")
        self._write_comparison_csv(old_summary, new_summary, comparison_csv_path)

        summary = {
            "base_gold": str(base_gold_path),
            "batch_gold": str(batch_gold_path),
            "base_fixed_csv": str(base_fixed_csv_path),
            "gold_seed_v2_csv": str(gold_out_csv),
            "gold_seed_v2_xlsx": str(gold_out_xlsx),
            "gold_seed_v2_fixed_eval_input_csv": str(merged_fixed_eval_csv),
            "gold_seed_v2_fixed_eval_input_xlsx": str(merged_fixed_eval_xlsx),
            "merged_total_rows": len(merged_rows),
            "base_total_rows": len(base_rows),
            "batch_appended_rows": len(merged_rows) - len(base_rows),
            "duplicate_count": len(duplicate_rows),
            "duplicate_rows": duplicate_rows,
            "fixed_eval_duplicate_count": len(fixed_duplicate_rows),
            "fixed_eval_duplicate_rows": fixed_duplicate_rows,
            "batch1_formally_included": [row.get("doc_name", "") for row in batch_rows if row.get("doc_name", "") not in {dup["doc_name"] for dup in duplicate_rows}],
            "old_eval": self._extract_eval_meta(old_summary),
            "new_eval": self._extract_eval_meta(new_summary),
            "comparison_csv": str(comparison_csv_path),
            "old_eval_dir": str(old_eval_dir),
            "new_eval_dir": str(new_eval_dir),
        }
        summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary_md_path.write_text(self._build_summary_markdown(summary, old_summary, new_summary), encoding="utf-8")

        self.stdout.write(f"gold_seed_v2_csv={gold_out_csv}")
        self.stdout.write(f"gold_seed_v2_xlsx={gold_out_xlsx}")
        self.stdout.write(f"gold_seed_v2_fixed_eval_input_csv={merged_fixed_eval_csv}")
        self.stdout.write(f"gold_seed_v2_fixed_eval_input_xlsx={merged_fixed_eval_xlsx}")
        self.stdout.write(f"old_eval_dir={old_eval_dir}")
        self.stdout.write(f"new_eval_dir={new_eval_dir}")
        self.stdout.write(f"comparison_csv={comparison_csv_path}")
        self.stdout.write(f"summary_json={summary_json_path}")
        self.stdout.write(f"summary_md={summary_md_path}")

    def _resolve_gold_csv_path(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "evaluation" / "gold_seed_v2.csv").resolve()

    def _resolve_gold_xlsx_path(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "evaluation" / "gold_seed_v2.xlsx").resolve()

    def _resolve_base_fixed_csv(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        return (
            Path(settings.BASE_DIR)
            / "runs"
            / "gold_raw_recall_20260312_v2"
            / "raw_recall_improved"
            / "gold_seed_rerun.csv"
        ).resolve()

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_v2_eval_{ts}").resolve()

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _merge_rows(self, base_rows: List[Dict[str, str]], batch_rows: List[Dict[str, str]]):
        merged = [{field: row.get(field, "") for field in self.OUTPUT_COLUMNS} for row in base_rows]
        seen_doc_ids = {self._norm(row.get("doc_id", "")) for row in base_rows if self._norm(row.get("doc_id", ""))}
        seen_titles = {self._norm_title(row.get("doc_name", "")) for row in base_rows if self._norm_title(row.get("doc_name", ""))}
        duplicates: List[Dict[str, str]] = []

        for row in batch_rows:
            doc_id_key = self._norm(row.get("doc_id", ""))
            title_key = self._norm_title(row.get("doc_name", ""))
            duplicate_reason = None
            if doc_id_key and doc_id_key in seen_doc_ids:
                duplicate_reason = "duplicate_doc_id"
            elif title_key and title_key in seen_titles:
                duplicate_reason = "duplicate_doc_name"

            if duplicate_reason:
                duplicates.append(
                    {
                        "doc_id": row.get("doc_id", ""),
                        "doc_name": row.get("doc_name", ""),
                        "reason": duplicate_reason,
                    }
                )
                continue

            merged.append({field: row.get(field, "") for field in self.OUTPUT_COLUMNS})
            if doc_id_key:
                seen_doc_ids.add(doc_id_key)
            if title_key:
                seen_titles.add(title_key)
        return merged, duplicates

    def _load_summary_rows(self, path: Path) -> Dict[str, Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return {
                str(row.get("field", "") or "").strip(): {k: str(v or "").strip() for k, v in row.items()}
                for row in reader
            }

    def _extract_eval_meta(self, summary_rows: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        row = summary_rows.get("overall_macro_avg", {})
        return {
            "total_rows": row.get("total_rows", ""),
            "evaluated_rows": row.get("evaluated_rows", ""),
            "skipped_rows": row.get("skipped_rows", ""),
            "coverage_rate": row.get("coverage_rate", ""),
        }

    def _write_comparison_csv(
        self,
        old_summary: Dict[str, Dict[str, str]],
        new_summary: Dict[str, Dict[str, str]],
        path: Path,
    ) -> None:
        rows: List[Dict[str, str]] = []
        for field in self.SUMMARY_FIELDS:
            old = old_summary.get(field, {})
            new = new_summary.get(field, {})
            rows.append(
                {
                    "field": field,
                    "old_total_rows": old.get("total_rows", ""),
                    "old_evaluated_rows": old.get("evaluated_rows", ""),
                    "old_skipped_rows": old.get("skipped_rows", ""),
                    "old_n_samples": old.get("n_samples", ""),
                    "old_precision": old.get("precision", ""),
                    "old_recall": old.get("recall", ""),
                    "old_f1": old.get("f1", ""),
                    "new_total_rows": new.get("total_rows", ""),
                    "new_evaluated_rows": new.get("evaluated_rows", ""),
                    "new_skipped_rows": new.get("skipped_rows", ""),
                    "new_n_samples": new.get("n_samples", ""),
                    "new_precision": new.get("precision", ""),
                    "new_recall": new.get("recall", ""),
                    "new_f1": new.get("f1", ""),
                    "delta_precision": self._delta(old.get("precision", ""), new.get("precision", "")),
                    "delta_recall": self._delta(old.get("recall", ""), new.get("recall", "")),
                    "delta_f1": self._delta(old.get("f1", ""), new.get("f1", "")),
                }
            )
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _delta(self, old_value: str, new_value: str) -> str:
        try:
            return f"{float(new_value) - float(old_value):.4f}"
        except Exception:
            return ""

    def _norm(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip().lower()

    def _norm_title(self, value: str) -> str:
        text = self._norm(value)
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _build_summary_markdown(
        self,
        summary: Dict[str, Any],
        old_summary: Dict[str, Dict[str, str]],
        new_summary: Dict[str, Dict[str, str]],
    ) -> str:
        lines = [
            "# Gold V2 Evaluation Summary",
            "",
            f"- base_gold: `{summary['base_gold']}`",
            f"- batch_gold: `{summary['batch_gold']}`",
            f"- gold_seed_v2_csv: `{summary['gold_seed_v2_csv']}`",
            f"- gold_seed_v2_xlsx: `{summary['gold_seed_v2_xlsx']}`",
            f"- merged_total_rows: `{summary['merged_total_rows']}`",
            f"- base_total_rows: `{summary['base_total_rows']}`",
            f"- batch_appended_rows: `{summary['batch_appended_rows']}`",
            f"- duplicate_count: `{summary['duplicate_count']}`",
            "",
            "## Batch1 Formally Included",
        ]
        for title in summary["batch1_formally_included"]:
            lines.append(f"- {title}")
        lines.extend(["", "## Evaluation Coverage"])
        lines.append(
            f"- old_gold: total_rows={summary['old_eval']['total_rows']}, evaluated_rows={summary['old_eval']['evaluated_rows']}, skipped_rows={summary['old_eval']['skipped_rows']}, coverage_rate={summary['old_eval']['coverage_rate']}"
        )
        lines.append(
            f"- new_gold_v2: total_rows={summary['new_eval']['total_rows']}, evaluated_rows={summary['new_eval']['evaluated_rows']}, skipped_rows={summary['new_eval']['skipped_rows']}, coverage_rate={summary['new_eval']['coverage_rate']}"
        )
        lines.extend(["", "## Metric Changes"])
        for field in self.SUMMARY_FIELDS:
            old = old_summary.get(field, {})
            new = new_summary.get(field, {})
            lines.append(
                f"- {field}: P {old.get('precision', '')} -> {new.get('precision', '')}, R {old.get('recall', '')} -> {new.get('recall', '')}, F1 {old.get('f1', '')} -> {new.get('f1', '')}, n_samples {old.get('n_samples', '')} -> {new.get('n_samples', '')}"
            )
        lines.extend(["", "## Duplicate Handling"])
        if summary["duplicate_rows"]:
            for row in summary["duplicate_rows"]:
                lines.append(f"- {row['doc_name']} ({row['doc_id']}): {row['reason']}")
        else:
            lines.append("- none")
        lines.extend(["", "## Fixed Eval Input Duplicates"])
        if summary["fixed_eval_duplicate_rows"]:
            for row in summary["fixed_eval_duplicate_rows"]:
                lines.append(f"- {row['doc_name']} ({row['doc_id']}): {row['reason']}")
        else:
            lines.append("- none")
        return "\n".join(lines) + "\n"

    def _write_csv(self, path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})

    def _write_xlsx(
        self,
        path: Path,
        sheet_name: str,
        fieldnames: Sequence[str],
        rows: Sequence[Dict[str, str]],
    ) -> None:
        headers = list(fieldnames)
        table_rows: List[List[Any]] = [headers]
        for row in rows:
            table_rows.append([row.get(field, "") for field in headers])

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", self._build_content_types_xml())
            zf.writestr("_rels/.rels", self._build_root_rels_xml())
            zf.writestr("xl/workbook.xml", self._build_workbook_xml(sheet_name))
            zf.writestr("xl/_rels/workbook.xml.rels", self._build_workbook_rels_xml())
            zf.writestr("xl/styles.xml", self._build_styles_xml())
            zf.writestr("xl/worksheets/sheet1.xml", self._build_sheet_xml(table_rows))

    def _build_sheet_xml(self, table_rows: Sequence[Sequence[Any]]) -> str:
        max_col = max((len(row) for row in table_rows), default=0)
        max_row = len(table_rows)
        ref = f"A1:{self._col_name(max_col)}{max_row}" if max_col and max_row else "A1:A1"

        rows_xml: List[str] = []
        for row_idx, row in enumerate(table_rows, start=1):
            cells: List[str] = []
            for col_idx, value in enumerate(row, start=1):
                cell_ref = f"{self._col_name(col_idx)}{row_idx}"
                style_id = "1" if row_idx == 1 else "0"
                cells.append(self._build_cell_xml(cell_ref, value, style_id))
            rows_xml.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            f'<dimension ref="{ref}"/>'
            f'<sheetData>{"".join(rows_xml)}</sheetData>'
            f'<autoFilter ref="{ref}"/>'
            "</worksheet>"
        )

    def _build_cell_xml(self, cell_ref: str, value: Any, style_id: str) -> str:
        text = "" if value is None else str(value)
        if text == "":
            return f'<c r="{cell_ref}" s="{style_id}" t="inlineStr"><is><t></t></is></c>'
        if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
            return f'<c r="{cell_ref}" s="{style_id}"><v>{escape(text)}</v></c>'
        safe = escape(text)
        preserve = ' xml:space="preserve"' if text != text.strip() or "\n" in text else ""
        return f'<c r="{cell_ref}" s="{style_id}" t="inlineStr"><is><t{preserve}>{safe}</t></is></c>'

    def _col_name(self, idx: int) -> str:
        out = ""
        value = idx
        while value > 0:
            value, rem = divmod(value - 1, 26)
            out = chr(65 + rem) + out
        return out or "A"

    def _build_content_types_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            "</Types>"
        )

    def _build_root_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    def _build_workbook_xml(self, sheet_name: str) -> str:
        safe_name = escape(sheet_name[:31] or "GoldSeedV2")
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            f'<sheet name="{safe_name}" sheetId="1" r:id="rId1"/>'
            "</sheets>"
            "</workbook>"
        )

    def _build_workbook_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>"
        )

    def _build_styles_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
            '</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>"
        )
