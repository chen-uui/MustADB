import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pdf_processor.unified_rag_service import RAGException, UnifiedRAGService


class Command(BaseCommand):
    help = "Export retrieval candidates CSV for manual relevance annotation."

    MODES = ("bm25", "dense", "hybrid", "hybrid_rerank")
    CSV_COLUMNS = (
        "qid",
        "question",
        "mode",
        "rank",
        "doc_id",
        "doc_name",
        "is_relevant",
        "notes",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of queries to export. Default: 10.",
        )
        parser.add_argument(
            "--topk",
            type=int,
            default=5,
            help="Top-k retrieval results per query. Default: 5.",
        )
        parser.add_argument(
            "--mode",
            type=str,
            choices=self.MODES,
            default="hybrid_rerank",
            help="Retrieval mode. Default: hybrid_rerank.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output CSV path. Default: evaluation/retrieval_qrels_seed.csv",
        )

    def handle(self, *args, **options):
        limit = int(options["limit"])
        topk = int(options["topk"])
        mode = str(options["mode"]).strip()

        if limit < 1:
            raise CommandError("--limit must be >= 1")
        if topk < 1:
            raise CommandError("--topk must be >= 1")

        queries_path = self._resolve_queries_path()
        out_path = self._resolve_out_path(options.get("out"))
        out_path.parent.mkdir(parents=True, exist_ok=True)

        queries = self._load_queries(queries_path)
        selected_queries = queries[:limit]
        if not selected_queries:
            raise CommandError("no queries to export")

        service = UnifiedRAGService()
        if not service.initialize():
            raise CommandError("UnifiedRAGService initialization failed")

        rows: List[Dict[str, str]] = []
        empty_result_queries = 0
        for item in selected_queries:
            qid = item["qid"]
            question = item["question"]
            try:
                results = service.search(
                    question,
                    limit=topk,
                    retrieval_mode=mode,
                )
            except RAGException as exc:
                raise CommandError(f"search failed for qid={qid}: {exc.message}") from exc
            except Exception as exc:
                raise CommandError(f"search failed for qid={qid}: {exc}") from exc

            if not results:
                empty_result_queries += 1
                continue

            for rank, result in enumerate(results, start=1):
                rows.append(
                    {
                        "qid": qid,
                        "question": question,
                        "mode": mode,
                        "rank": str(rank),
                        "doc_id": str(getattr(result, "document_id", "") or "").strip(),
                        "doc_name": str(getattr(result, "title", "") or "").strip(),
                        "is_relevant": "",
                        "notes": "",
                    }
                )

        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.CSV_COLUMNS))
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(f"queries_path={queries_path}")
        self.stdout.write(f"selected_queries={len(selected_queries)}")
        self.stdout.write(f"mode={mode}")
        self.stdout.write(f"topk={topk}")
        self.stdout.write(f"rows={len(rows)}")
        self.stdout.write(f"empty_result_queries={empty_result_queries}")
        self.stdout.write(f"out_path={out_path}")

    def _resolve_queries_path(self) -> Path:
        return (Path(settings.BASE_DIR) / "evaluation" / "queries.jsonl").resolve()

    def _resolve_out_path(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "evaluation" / "retrieval_qrels_seed.csv").resolve()

    def _load_queries(self, path: Path) -> List[Dict[str, str]]:
        if not path.exists():
            raise CommandError(f"queries file not found: {path}")

        items: List[Dict[str, str]] = []
        seen_qids = set()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            content = line.strip()
            if not content:
                continue
            try:
                data = json.loads(content)
            except json.JSONDecodeError as exc:
                raise CommandError(f"invalid json at {path}:{line_no}: {exc}") from exc

            if not isinstance(data, dict):
                raise CommandError(f"invalid item at {path}:{line_no}: must be object")

            qid = str(data.get("qid", "")).strip()
            question = str(data.get("question", "")).strip()
            if not qid:
                raise CommandError(f"invalid item at {path}:{line_no}: qid is required")
            if not question:
                raise CommandError(f"invalid item at {path}:{line_no}: question is required")
            if qid in seen_qids:
                raise CommandError(f"duplicate qid at {path}:{line_no}: {qid}")

            seen_qids.add(qid)
            items.append({"qid": qid, "question": question})

        if not items:
            raise CommandError(f"queries file has no valid rows: {path}")
        return items
