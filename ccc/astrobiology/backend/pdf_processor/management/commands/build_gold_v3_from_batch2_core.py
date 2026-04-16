import csv
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Fix the single batch2 core row and merge it into gold_seed_v2.csv to produce gold_seed_v3."

    TARGET_TITLE = "Concentration and variability of the AIB amino acid in polar micrometeorites: Implications for the exogenous delivery of amino acids to the primitive Earth"
    GOLD_COLUMNS = [
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
    EXTENDED_COLUMNS = [
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
        "review_note",
        "doc_filename",
        "doc_year",
        "doc_journal",
        "prediction_source",
        "review_priority",
        "scope_type",
        "recommendation",
        "pred_organic_compounds_raw",
        "pred_organic_compounds_filtered",
        "pred_organic_compounds_projected",
        "rerun_strategy",
        "rerun_selected_chunk_ids",
    ]

    def add_arguments(self, parser):
        parser.add_argument("--batch2-core-final", type=str, required=True, help="batch2 core final CSV path.")
        parser.add_argument("--gold-v2", type=str, required=True, help="Current gold_seed_v2.csv path.")
        parser.add_argument(
            "--out-dir",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_v3_build_<timestamp>",
        )
        parser.add_argument(
            "--gold-v3-csv",
            type=str,
            default=None,
            help="Output path for gold_seed_v3.csv. Default: evaluation/gold_seed_v3.csv",
        )
        parser.add_argument(
            "--gold-v3-xlsx",
            type=str,
            default=None,
            help="Output path for gold_seed_v3.xlsx. Default: evaluation/gold_seed_v3.xlsx",
        )

    def handle(self, *args, **options):
        batch2_core_path = Path(str(options["batch2_core_final"])).expanduser().resolve()
        gold_v2_path = Path(str(options["gold_v2"])).expanduser().resolve()
        if not batch2_core_path.exists():
            raise CommandError(f"batch2 core final csv not found: {batch2_core_path}")
        if not gold_v2_path.exists():
            raise CommandError(f"gold v2 csv not found: {gold_v2_path}")

        out_dir = self._resolve_out_dir(options.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)
        gold_v3_csv = self._resolve_gold_v3_csv(options.get("gold_v3_csv"))
        gold_v3_xlsx = self._resolve_gold_v3_xlsx(options.get("gold_v3_xlsx"))
        gold_v3_csv.parent.mkdir(parents=True, exist_ok=True)
        gold_v3_xlsx.parent.mkdir(parents=True, exist_ok=True)

        batch_rows = self._read_csv(batch2_core_path)
        target_rows = [row for row in batch_rows if row.get("doc_name", "") == self.TARGET_TITLE]
        if len(target_rows) != 1:
            raise CommandError(f"expected exactly one target row in batch2 core final, found {len(target_rows)}")

        fixed_row = self._fix_core_row(target_rows[0])
        fixed_core_rows = [fixed_row]

        fixed_core_csv = out_dir / "gold_seed_batch2_core_final_fixed.csv"
        fixed_core_xlsx = out_dir / "gold_seed_batch2_core_final_fixed.xlsx"
        self._write_csv(fixed_core_csv, self.EXTENDED_COLUMNS, fixed_core_rows)
        self._write_xlsx(fixed_core_xlsx, "Batch2CoreFixed", self.EXTENDED_COLUMNS, fixed_core_rows)

        gold_v2_rows = self._read_csv(gold_v2_path)
        merged_v3_rows, duplicate = self._merge_gold_rows(gold_v2_rows, fixed_row)
        self._write_csv(gold_v3_csv, self.GOLD_COLUMNS, merged_v3_rows)
        self._write_xlsx(gold_v3_xlsx, "GoldSeedV3", self.GOLD_COLUMNS, merged_v3_rows)

        summary = {
            "batch2_core_final_source": str(batch2_core_path),
            "gold_v2_source": str(gold_v2_path),
            "gold_seed_batch2_core_final_fixed_csv": str(fixed_core_csv),
            "gold_seed_batch2_core_final_fixed_xlsx": str(fixed_core_xlsx),
            "gold_seed_v3_csv": str(gold_v3_csv),
            "gold_seed_v3_xlsx": str(gold_v3_xlsx),
            "added_title": fixed_row["doc_name"] if not duplicate else "",
            "duplicate_detected": duplicate,
            "v2_row_count": len(gold_v2_rows),
            "v3_row_count": len(merged_v3_rows),
            "supporting_not_merged": True,
        }
        summary_md = out_dir / "summary.md"
        summary_json = out_dir / "summary.json"
        summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary_md.write_text(self._build_summary_markdown(summary), encoding="utf-8")

        self.stdout.write(f"fixed_core_csv={fixed_core_csv}")
        self.stdout.write(f"fixed_core_xlsx={fixed_core_xlsx}")
        self.stdout.write(f"gold_v3_csv={gold_v3_csv}")
        self.stdout.write(f"gold_v3_xlsx={gold_v3_xlsx}")
        self.stdout.write(f"summary_md={summary_md}")
        self.stdout.write(f"summary_json={summary_json}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_v3_build_{ts}").resolve()

    def _resolve_gold_v3_csv(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "evaluation" / "gold_seed_v3.csv").resolve()

    def _resolve_gold_v3_xlsx(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "evaluation" / "gold_seed_v3.xlsx").resolve()

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _fix_core_row(self, row: Dict[str, str]) -> Dict[str, str]:
        fixed = dict(row)
        fixed["gold_meteorite_name"] = "polar micrometeorites"
        fixed["gold_organic_compounds"] = "amino acids; AIB"
        fixed["gold_contamination_controls"] = ""
        existing_note = str(row.get("review_note", "") or "").strip()
        fix_note = "batch2_core_fixed_for_gold_v3"
        fixed["review_note"] = f"{existing_note}; {fix_note}" if existing_note else fix_note
        return fixed

    def _merge_gold_rows(self, gold_v2_rows: List[Dict[str, str]], fixed_row: Dict[str, str]):
        fixed_doc_id = self._norm(fixed_row.get("doc_id", ""))
        fixed_title = self._norm_title(fixed_row.get("doc_name", ""))
        merged = [{field: row.get(field, "") for field in self.GOLD_COLUMNS} for row in gold_v2_rows]
        for row in gold_v2_rows:
            if fixed_doc_id and self._norm(row.get("doc_id", "")) == fixed_doc_id:
                return merged, True
            if fixed_title and self._norm_title(row.get("doc_name", "")) == fixed_title:
                return merged, True
        merged.append({field: fixed_row.get(field, "") for field in self.GOLD_COLUMNS})
        return merged, False

    def _norm(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip().lower()

    def _norm_title(self, value: str) -> str:
        text = self._norm(value)
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _build_summary_markdown(self, summary: Dict[str, Any]) -> str:
        lines = [
            "# Gold V3 Build Summary",
            "",
            f"- batch2_core_final_source: `{summary['batch2_core_final_source']}`",
            f"- gold_v2_source: `{summary['gold_v2_source']}`",
            f"- gold_seed_batch2_core_final_fixed_csv: `{summary['gold_seed_batch2_core_final_fixed_csv']}`",
            f"- gold_seed_batch2_core_final_fixed_xlsx: `{summary['gold_seed_batch2_core_final_fixed_xlsx']}`",
            f"- gold_seed_v3_csv: `{summary['gold_seed_v3_csv']}`",
            f"- gold_seed_v3_xlsx: `{summary['gold_seed_v3_xlsx']}`",
            f"- v2_row_count: `{summary['v2_row_count']}`",
            f"- v3_row_count: `{summary['v3_row_count']}`",
            f"- duplicate_detected: `{summary['duplicate_detected']}`",
            "",
            "## v2 to v3 New Addition",
        ]
        if summary["added_title"]:
            lines.append(f"- {summary['added_title']}")
        else:
            lines.append("- none (row already existed in v2)")
        lines.extend(["", "## Supporting Status", "- supporting_final remains separate and was not merged into formal core gold."])
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
        safe_name = escape(sheet_name[:31] or "GoldV3")
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
