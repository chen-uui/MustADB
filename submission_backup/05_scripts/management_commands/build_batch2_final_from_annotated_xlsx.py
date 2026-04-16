import csv
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Build final batch2 core/supporting files strictly from an annotated batch2 xlsx."

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
    NS = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    YES_VALUES = {"yes", "y", "true", "1"}

    def add_arguments(self, parser):
        parser.add_argument("--annotated-xlsx", type=str, required=True, help="Annotated batch2 xlsx path.")
        parser.add_argument(
            "--out-dir",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_batch2_final_<timestamp>",
        )

    def handle(self, *args, **options):
        annotated_path = Path(str(options["annotated_xlsx"])).expanduser().resolve()
        if not annotated_path.exists():
            raise CommandError(f"annotated xlsx not found: {annotated_path}")

        out_dir = self._resolve_out_dir(options.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)

        rows = self._read_first_sheet_rows(annotated_path)
        if not rows:
            raise CommandError("annotated workbook has no rows")

        core_rows = []
        supporting_rows = []
        excluded_rows = []
        for row in rows:
            in_scope = self._norm(row.get("in_scope", ""))
            scope_type = self._norm(row.get("scope_type", ""))
            if in_scope in self.YES_VALUES and scope_type == "core_gold":
                core_rows.append(self._convert_row(row))
            elif in_scope in self.YES_VALUES and scope_type == "supporting_gold":
                supporting_rows.append(self._convert_row(row))
            else:
                excluded_rows.append(
                    {
                        "doc_name": row.get("doc_name", ""),
                        "in_scope": row.get("in_scope", ""),
                        "scope_type": row.get("scope_type", ""),
                        "review_priority": row.get("review_priority", ""),
                        "recommendation": row.get("recommendation", ""),
                        "notes": row.get("notes", ""),
                    }
                )

        core_csv = out_dir / "gold_seed_batch2_core_final.csv"
        core_xlsx = out_dir / "gold_seed_batch2_core_final.xlsx"
        supporting_csv = out_dir / "gold_seed_batch2_supporting_final.csv"
        supporting_xlsx = out_dir / "gold_seed_batch2_supporting_final.xlsx"
        summary_md = out_dir / "summary.md"
        summary_json = out_dir / "summary.json"
        excluded_csv = out_dir / "batch2_excluded_items.csv"

        self._write_csv(core_csv, self.OUTPUT_COLUMNS, core_rows)
        self._write_xlsx(core_xlsx, "Batch2CoreFinal", self.OUTPUT_COLUMNS, core_rows)
        self._write_csv(supporting_csv, self.OUTPUT_COLUMNS, supporting_rows)
        self._write_xlsx(supporting_xlsx, "Batch2SupportingFinal", self.OUTPUT_COLUMNS, supporting_rows)
        self._write_csv(excluded_csv, list(excluded_rows[0].keys()) if excluded_rows else ["doc_name"], excluded_rows)

        summary = {
            "annotated_xlsx": str(annotated_path),
            "core_final_added_count": len(core_rows),
            "supporting_final_added_count": len(supporting_rows),
            "core_titles": [row["doc_name"] for row in core_rows],
            "supporting_titles": [row["doc_name"] for row in supporting_rows],
            "excluded_titles": [row["doc_name"] for row in excluded_rows],
            "excluded_count": len(excluded_rows),
            "strict_rule": "Selection used only annotated in_scope, scope_type, review_priority, recommendation, and notes. gold_* values were copied exactly from annotated rows without any fallback.",
        }
        summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary_md.write_text(self._build_summary_markdown(summary, excluded_rows), encoding="utf-8")

        self.stdout.write(f"core_final_count={len(core_rows)}")
        self.stdout.write(f"supporting_final_count={len(supporting_rows)}")
        self.stdout.write(f"excluded_count={len(excluded_rows)}")
        self.stdout.write(f"core_csv={core_csv}")
        self.stdout.write(f"core_xlsx={core_xlsx}")
        self.stdout.write(f"supporting_csv={supporting_csv}")
        self.stdout.write(f"supporting_xlsx={supporting_xlsx}")
        self.stdout.write(f"summary_md={summary_md}")
        self.stdout.write(f"summary_json={summary_json}")
        self.stdout.write(f"excluded_csv={excluded_csv}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_batch2_final_{ts}").resolve()

    def _norm(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip().lower()

    def _read_first_sheet_rows(self, xlsx_path: Path) -> List[Dict[str, str]]:
        with zipfile.ZipFile(xlsx_path, "r") as zf:
            shared_strings = self._read_shared_strings(zf)
            workbook = ET.fromstring(zf.read("xl/workbook.xml"))
            sheets = workbook.find("a:sheets", self.NS)
            if sheets is None or not list(sheets):
                raise CommandError("workbook has no sheets")
            first_sheet = list(sheets)[0]
            rel_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            rel_map = {rel.attrib["Id"]: rel.attrib["Target"].lstrip("/") for rel in rels}
            target = rel_map.get(rel_id)
            if not target:
                raise CommandError("failed to resolve worksheet rel target")
            sheet_root = ET.fromstring(zf.read(target))
            sheet_data = sheet_root.find("a:sheetData", self.NS)
            if sheet_data is None:
                return []
            rows = sheet_data.findall("a:row", self.NS)
            if not rows:
                return []

            header_map = self._parse_row_cells(rows[0], shared_strings)
            if not header_map:
                return []
            max_col = max(header_map.keys())
            headers = [header_map.get(idx, "").strip() for idx in range(1, max_col + 1)]

            out_rows: List[Dict[str, str]] = []
            for row in rows[1:]:
                value_map = self._parse_row_cells(row, shared_strings)
                out_rows.append(
                    {
                        headers[idx - 1]: str(value_map.get(idx, "") or "").strip()
                        for idx in range(1, max_col + 1)
                        if headers[idx - 1]
                    }
                )
            return out_rows

    def _read_shared_strings(self, zf: zipfile.ZipFile) -> List[str]:
        if "xl/sharedStrings.xml" not in zf.namelist():
            return []
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        out: List[str] = []
        for si in root.findall("a:si", self.NS):
            out.append("".join(node.text or "" for node in si.iterfind(".//a:t", self.NS)))
        return out

    def _parse_row_cells(self, row_node: ET.Element, shared_strings: Sequence[str]) -> Dict[int, str]:
        values: Dict[int, str] = {}
        for cell in row_node.findall("a:c", self.NS):
            ref = cell.attrib.get("r", "")
            col_idx = self._column_index(ref)
            if not col_idx:
                continue
            cell_type = cell.attrib.get("t")
            if cell_type == "s":
                raw = cell.findtext("a:v", default="", namespaces=self.NS)
                text = shared_strings[int(raw)] if raw else ""
            elif cell_type == "inlineStr":
                text = "".join(node.text or "" for node in cell.iterfind(".//a:t", self.NS))
            else:
                text = cell.findtext("a:v", default="", namespaces=self.NS)
            values[col_idx] = str(text or "").strip()
        return values

    def _column_index(self, cell_ref: str) -> int:
        letters = "".join(ch for ch in str(cell_ref) if ch.isalpha()).upper()
        if not letters:
            return 0
        value = 0
        for ch in letters:
            value = value * 26 + (ord(ch) - 64)
        return value

    def _convert_row(self, row: Dict[str, str]) -> Dict[str, str]:
        return {
            "doc_id": row.get("doc_id", ""),
            "doc_name": row.get("doc_name", ""),
            "pred_meteorite_name": row.get("pred_meteorite_name", ""),
            "pred_organic_compounds": row.get("pred_organic_compounds_projected", ""),
            "pred_contamination_controls": row.get("pred_contamination_controls", ""),
            "in_scope": row.get("in_scope", ""),
            "skip_row": row.get("skip_row", "") or "no",
            "notes": row.get("notes", ""),
            "gold_meteorite_name": row.get("gold_meteorite_name", ""),
            "gold_organic_compounds": row.get("gold_organic_compounds", ""),
            "gold_contamination_controls": row.get("gold_contamination_controls", ""),
            "review_note": "batch2_final_from_annotated_xlsx_strict",
            "doc_filename": row.get("doc_filename", ""),
            "doc_year": row.get("doc_year", ""),
            "doc_journal": row.get("doc_journal", ""),
            "prediction_source": row.get("prediction_source", ""),
            "review_priority": row.get("review_priority", ""),
            "scope_type": row.get("scope_type", ""),
            "recommendation": row.get("recommendation", ""),
            "pred_organic_compounds_raw": row.get("pred_organic_compounds_raw", ""),
            "pred_organic_compounds_filtered": row.get("pred_organic_compounds_filtered", ""),
            "pred_organic_compounds_projected": row.get("pred_organic_compounds_projected", ""),
            "rerun_strategy": row.get("rerun_strategy", ""),
            "rerun_selected_chunk_ids": row.get("rerun_selected_chunk_ids", ""),
        }

    def _build_summary_markdown(self, summary: Dict[str, Any], excluded_rows: Sequence[Dict[str, str]]) -> str:
        lines = [
            "# Batch2 Final Summary",
            "",
            f"- annotated_xlsx: `{summary['annotated_xlsx']}`",
            f"- core_final_added_count: `{summary['core_final_added_count']}`",
            f"- supporting_final_added_count: `{summary['supporting_final_added_count']}`",
            f"- excluded_count: `{summary['excluded_count']}`",
            f"- strict_rule: {summary['strict_rule']}",
            "",
            "## Core Final",
        ]
        for title in summary["core_titles"] or ["none"]:
            lines.append(f"- {title}")
        lines.extend(["", "## Supporting Final"])
        for title in summary["supporting_titles"] or ["none"]:
            lines.append(f"- {title}")
        lines.extend(["", "## Excluded Items"])
        if excluded_rows:
            for row in excluded_rows:
                lines.append(
                    f"- {row.get('doc_name', '')} | in_scope={row.get('in_scope', '')} | scope_type={row.get('scope_type', '')} | review_priority={row.get('review_priority', '')} | recommendation={row.get('recommendation', '')}"
                )
                if row.get("notes", ""):
                    lines.append(f"  notes: {row.get('notes', '')}")
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
        safe_name = escape(sheet_name[:31] or "Batch2Final")
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
