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
    help = "Build the final confirmed batch1 gold_seed files from an existing gold_seed_batch1.csv."

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

    INCLUDE_RULES = {
        "Indigenous OrganicOxidized Fluid Interactions in the Tissint Mars Meteorite": {
            "gold_meteorite_name": None,
            "gold_organic_compounds": None,
            "gold_contamination_controls": None,
        },
        "Investigating the impact of xray computed tomography imaging on soluble organic matter in the Murchison meteorite: Implications for Bennu sample analyses": {
            "gold_meteorite_name": "Murchison",
            "gold_organic_compounds": None,
            "gold_contamination_controls": "",
        },
        "Extraterrestrial ribose and other sugars in primitive meteorites": {
            "gold_meteorite_name": "",
            "gold_organic_compounds": "ribose; sugars; arabinose; xylose; glucose; mannose",
            "gold_contamination_controls": "",
        },
        "Molecular distribution and 13C isotope composition of volatile organic compounds in the Murchison and Sutters Mill carbonaceous chondrites": {
            "gold_meteorite_name": "Murchison; Sutters Mill",
            "gold_organic_compounds": "volatile organic compounds; formaldehyde; methanol",
            "gold_contamination_controls": "",
        },
        "Extraterrestrial hexamethylenetetramine Yasuhiro Oba": {
            "gold_meteorite_name": "",
            "gold_organic_compounds": "HMT; HMT-CH3; HMT-CH2OH",
            "gold_contamination_controls": "",
        },
        "High-spatial resolution functional chemistry of nitrogen compounds in the observed UK meteorite fall Winchcombe": {
            "gold_meteorite_name": "Winchcombe",
            "gold_organic_compounds": "n-heterocycles; pyrrole; imidazole",
            "gold_contamination_controls": "",
        },
        "Speciation of organosulfur compounds in carbonaceous chondrites": {
            "gold_meteorite_name": "",
            "gold_organic_compounds": "organosulfur compounds; sulfonyls; sulfonates",
            "gold_contamination_controls": "",
        },
    }

    DEFER_TITLES = {
        "Reanalysis of the Viking results suggests perchlorate and organics at midlatitudes on Mars",
        "Nanoscale infrared imaging analysis of carbonaceous chondrites to understand organic-mineral interactions during aqueous alteration",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--input-csv",
            type=str,
            required=True,
            help="Existing gold_seed_batch1.csv path.",
        )
        parser.add_argument(
            "--out-dir",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_batch1_final_<timestamp>",
        )

    def handle(self, *args, **options):
        input_csv = Path(str(options["input_csv"])).expanduser().resolve()
        if not input_csv.exists():
            raise CommandError(f"input csv not found: {input_csv}")

        out_dir = self._resolve_out_dir(options.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)

        rows = self._read_csv(input_csv)
        row_map = {row.get("doc_name", ""): row for row in rows}

        missing_titles = [title for title in self.INCLUDE_RULES if title not in row_map]
        if missing_titles:
            raise CommandError(f"required source rows missing from input csv: {missing_titles}")

        finalized_rows = [self._finalize_row(row_map[title], self.INCLUDE_RULES[title]) for title in self.INCLUDE_RULES]
        csv_path = out_dir / "gold_seed_batch1_final.csv"
        xlsx_path = out_dir / "gold_seed_batch1_final.xlsx"
        summary_json_path = out_dir / "batch1_final_summary.json"
        summary_md_path = out_dir / "batch1_final_summary.md"

        self._write_csv(csv_path, self.OUTPUT_COLUMNS, finalized_rows)
        self._write_xlsx(xlsx_path, "GoldBatch1Final", self.OUTPUT_COLUMNS, finalized_rows)

        summary = {
            "input_csv": str(input_csv),
            "finalized_count": len(finalized_rows),
            "finalized_titles": [row["doc_name"] for row in finalized_rows],
            "deferred_titles": sorted(self.DEFER_TITLES),
            "intentionally_blank_fields": {
                row["doc_name"]: [
                    field for field in [
                        "gold_meteorite_name",
                        "gold_contamination_controls",
                    ]
                    if not row.get(field, "").strip()
                ]
                for row in finalized_rows
                if not row.get("gold_meteorite_name", "").strip() or not row.get("gold_contamination_controls", "").strip()
            },
        }
        summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary_md_path.write_text(self._build_summary_markdown(summary), encoding="utf-8")

        self.stdout.write(f"input_csv={input_csv}")
        self.stdout.write(f"finalized_count={len(finalized_rows)}")
        self.stdout.write(f"gold_seed_batch1_final_csv={csv_path}")
        self.stdout.write(f"gold_seed_batch1_final_xlsx={xlsx_path}")
        self.stdout.write(f"summary_json={summary_json_path}")
        self.stdout.write(f"summary_md={summary_md_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_batch1_final_{ts}").resolve()

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _finalize_row(self, row: Dict[str, str], overrides: Dict[str, Optional[str]]) -> Dict[str, str]:
        out = {field: row.get(field, "") for field in self.OUTPUT_COLUMNS}
        out["in_scope"] = "yes"
        out["skip_row"] = "no"
        out["scope_type"] = "core_gold"
        out["review_priority"] = row.get("review_priority", "") or "high"
        out["recommendation"] = "confirmed_core_gold"

        for field, value in overrides.items():
            if value is not None:
                out[field] = value

        existing_review_note = row.get("review_note", "").strip()
        final_note = "finalized_batch1_confirmed_core_gold"
        out["review_note"] = f"{existing_review_note}; {final_note}" if existing_review_note else final_note
        return out

    def _build_summary_markdown(self, summary: Dict[str, Any]) -> str:
        lines = [
            "# Gold Batch1 Final Summary",
            "",
            f"- input_csv: `{summary['input_csv']}`",
            f"- finalized_count: `{summary['finalized_count']}`",
            "",
            "## Finalized Documents",
        ]
        for title in summary["finalized_titles"]:
            lines.append(f"- {title}")
        lines.extend(["", "## Deferred Documents"])
        for title in summary["deferred_titles"]:
            lines.append(f"- {title}")
        lines.extend(["", "## Intentionally Blank Gold Fields"])
        if summary["intentionally_blank_fields"]:
            for title, fields in summary["intentionally_blank_fields"].items():
                lines.append(f"- {title}: {', '.join(fields)}")
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
        safe_name = escape(sheet_name[:31] or "GoldBatch1Final")
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
