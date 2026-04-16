import csv
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pdf_processor.models import PDFDocument
from pdf_processor.unified_rag_service import UnifiedRAGService


class Command(BaseCommand):
    help = "Export new retrieval-query candidates and per-query candidate documents for qrels expansion."

    DEFAULT_COLLECTION = "PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix"
    DEFAULT_MODE = "hybrid_rerank"
    DEFAULT_ALPHA = 0.7

    QUERY_COLUMNS = (
        "new_qid",
        "query",
        "source_origin",
        "why_selected",
        "overlap_with_existing_seed",
    )

    DOC_COLUMNS = (
        "new_qid",
        "query",
        "mode",
        "alpha",
        "collection_name",
        "rank",
        "document_id",
        "document_title",
        "score",
        "source_path",
        "evidence_snippet",
        "candidate_relevance",
        "annotation_note",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--query-source",
            type=str,
            required=True,
            help="Path to csv/jsonl query source containing qid + question.",
        )
        parser.add_argument(
            "--existing-qrels",
            type=str,
            default=None,
            help="Existing retrieval qrels CSV to exclude already-used queries. Default: evaluation/retrieval_qrels_seed.csv",
        )
        parser.add_argument(
            "--collection-name",
            type=str,
            default=self.DEFAULT_COLLECTION,
            help="Weaviate collection to query. Default: paper-ready 700/80 collection.",
        )
        parser.add_argument(
            "--mode",
            type=str,
            default=self.DEFAULT_MODE,
            choices=sorted(UnifiedRAGService.VALID_RETRIEVAL_MODES),
            help="Retrieval mode for candidate-doc export. Default: hybrid_rerank.",
        )
        parser.add_argument(
            "--alpha",
            type=float,
            default=self.DEFAULT_ALPHA,
            help="Hybrid alpha when mode is hybrid/hybrid_rerank. Default: 0.7",
        )
        parser.add_argument(
            "--top-k",
            type=int,
            default=10,
            help="Number of unique document candidates per query. Default: 10.",
        )
        parser.add_argument(
            "--candidate-limit",
            type=int,
            default=20,
            help="Initial retrieval limit before doc dedupe. Default: 20.",
        )
        parser.add_argument(
            "--snippet-char-limit",
            type=int,
            default=320,
            help="Character limit for evidence snippets. Default: 320.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/retrieval_qrels_expansion_paper_support_<timestamp>/",
        )

    def handle(self, *args, **options):
        query_source = Path(str(options["query_source"])).expanduser().resolve()
        if not query_source.exists():
            raise CommandError(f"query source not found: {query_source}")

        existing_qrels = self._resolve_existing_qrels(options.get("existing_qrels"))
        collection_name = str(options["collection_name"]).strip()
        mode = str(options["mode"]).strip().lower()
        alpha = float(options["alpha"])
        top_k = int(options["top_k"])
        candidate_limit = int(options["candidate_limit"])
        snippet_char_limit = int(options["snippet_char_limit"])
        if top_k < 1:
            raise CommandError("--top-k must be >= 1")
        if candidate_limit < top_k:
            raise CommandError("--candidate-limit must be >= --top-k")
        if not 0.0 <= alpha <= 1.0:
            raise CommandError("--alpha must be between 0 and 1")

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        source_queries = self._load_queries(query_source)
        existing_seed_questions = self._load_existing_seed_questions(existing_qrels)
        selected_queries = [
            item for item in source_queries if item["question"] not in existing_seed_questions
        ]
        if not selected_queries:
            raise CommandError("no new queries remain after excluding existing seed qrels")

        doc_map = self._load_document_metadata()
        service = UnifiedRAGService(collection_name=collection_name)
        if not service.initialize():
            raise CommandError("Failed to initialize UnifiedRAGService")

        query_rows = self._build_query_rows(selected_queries, query_source)
        doc_rows = self._build_doc_rows(
            queries=selected_queries,
            service=service,
            mode=mode,
            alpha=alpha,
            top_k=top_k,
            candidate_limit=candidate_limit,
            snippet_char_limit=snippet_char_limit,
            doc_map=doc_map,
        )

        query_csv = out_dir / "new_query_candidates.csv"
        docs_csv = out_dir / "new_query_candidate_docs.csv"
        guide_md = out_dir / "qrels_annotation_guidelines.md"

        self._write_csv(query_csv, self.QUERY_COLUMNS, query_rows)
        self._write_csv(docs_csv, self.DOC_COLUMNS, doc_rows)
        guide_md.write_text(self._build_guidelines(), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"query_candidates_csv={query_csv}"))
        self.stdout.write(self.style.SUCCESS(f"candidate_docs_csv={docs_csv}"))
        self.stdout.write(self.style.SUCCESS(f"guidelines_md={guide_md}"))
        self.stdout.write(self.style.SUCCESS(f"new_queries={len(query_rows)}"))
        self.stdout.write(self.style.SUCCESS(f"candidate_rows={len(doc_rows)}"))

    def _resolve_existing_qrels(self, path_arg: Optional[str]) -> Path:
        if path_arg and str(path_arg).strip():
            path = Path(str(path_arg)).expanduser().resolve()
        else:
            path = (Path(settings.BASE_DIR) / "evaluation" / "retrieval_qrels_seed.csv").resolve()
        if not path.exists():
            raise CommandError(f"existing qrels not found: {path}")
        return path

    def _resolve_out_dir(self, path_arg: Optional[str]) -> Path:
        if path_arg and str(path_arg).strip():
            return Path(str(path_arg)).expanduser().resolve()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (
            Path(settings.BASE_DIR)
            / "runs"
            / f"retrieval_qrels_expansion_paper_support_{timestamp}"
        ).resolve()

    def _load_queries(self, path: Path) -> List[Dict[str, str]]:
        if path.suffix.lower() == ".jsonl":
            return self._load_jsonl_queries(path)
        return self._load_csv_queries(path)

    def _load_jsonl_queries(self, path: Path) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            content = line.strip()
            if not content:
                continue
            import json

            item = json.loads(content)
            qid = str(item.get("qid", "")).strip()
            question = str(item.get("question", "")).strip()
            if qid and question:
                rows.append({"qid": qid, "question": question})
        return rows

    def _load_csv_queries(self, path: Path) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "question" not in reader.fieldnames:
                raise CommandError(f"query csv must contain 'question' column: {path}")
            qid_key = "new_qid" if "new_qid" in reader.fieldnames else "qid"
            for row in reader:
                qid = str(row.get(qid_key, "")).strip()
                question = str(row.get("question", "")).strip()
                if qid and question:
                    rows.append({"qid": qid, "question": question})
        return rows

    def _load_existing_seed_questions(self, path: Path) -> set[str]:
        questions = set()
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                question = str(row.get("question", "")).strip()
                if question:
                    questions.add(question)
        return questions

    def _load_document_metadata(self) -> Dict[str, Dict[str, str]]:
        doc_map: Dict[str, Dict[str, str]] = {}
        for doc in PDFDocument.objects.all().only("id", "title", "filename", "file_path"):
            doc_map[str(doc.id)] = {
                "title": doc.title or "",
                "filename": doc.filename or "",
                "file_path": doc.file_path or "",
            }
        return doc_map

    def _build_query_rows(
        self,
        queries: Sequence[Dict[str, str]],
        query_source: Path,
    ) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        for item in queries:
            qid = item["qid"]
            question = item["question"]
            rows.append(
                {
                    "new_qid": qid,
                    "query": question,
                    "source_origin": f"{query_source}:{qid}",
                    "why_selected": self._why_selected(question),
                    "overlap_with_existing_seed": "no: excluded by exact-question match against retrieval_qrels_seed.csv",
                }
            )
        return rows

    def _build_doc_rows(
        self,
        *,
        queries: Sequence[Dict[str, str]],
        service: UnifiedRAGService,
        mode: str,
        alpha: float,
        top_k: int,
        candidate_limit: int,
        snippet_char_limit: int,
        doc_map: Dict[str, Dict[str, str]],
    ) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        for item in queries:
            qid = item["qid"]
            query = item["question"]
            results = service.search(
                query,
                limit=candidate_limit,
                retrieval_mode=mode,
                rerank_k=max(candidate_limit, top_k),
                hybrid_alpha=alpha,
            )
            unique_results = self._collapse_to_unique_documents(results, top_k)
            for rank, result in enumerate(unique_results, start=1):
                doc_meta = doc_map.get(str(result.document_id), {})
                title = result.title or doc_meta.get("title") or doc_meta.get("filename") or ""
                rows.append(
                    {
                        "new_qid": qid,
                        "query": query,
                        "mode": mode,
                        "alpha": f"{alpha:.1f}" if mode in {"hybrid", "hybrid_rerank"} else "NA",
                        "collection_name": service.collection_name,
                        "rank": str(rank),
                        "document_id": str(result.document_id),
                        "document_title": title,
                        "score": f"{float(result.score):.6f}",
                        "source_path": doc_meta.get("file_path", ""),
                        "evidence_snippet": self._trim_text(result.content or "", snippet_char_limit),
                        "candidate_relevance": "",
                        "annotation_note": "",
                    }
                )
        return rows

    def _collapse_to_unique_documents(self, results, top_k: int):
        unique = []
        seen = set()
        for result in results:
            doc_key = str(result.document_id).strip() or (result.title or "").strip()
            if not doc_key or doc_key in seen:
                continue
            seen.add(doc_key)
            unique.append(result)
            if len(unique) >= top_k:
                break
        return unique

    def _why_selected(self, question: str) -> str:
        lower = question.lower()
        if "aqueous alteration" in lower:
            return "Covers parent-body alteration effects on organics."
        if "phthalate" in lower:
            return "Targets laboratory contamination indicators relevant to EOM handling."
        if "cm and cr" in lower:
            return "Adds meteorite-class comparison on organic abundance."
        if "procedural blanks" in lower or "field blanks" in lower:
            return "Covers contamination-control interpretation and QC practice."
        if "prebiotic" in lower:
            return "Adds abiotic/prebiotic context linked to meteoritic organics."
        if "thermal metamorphism" in lower:
            return "Covers thermal processing effects on organic matter."
        if "uncertainty" in lower:
            return "Adds reporting/QC information need for analytical results."
        if "compound-specific isotope" in lower:
            return "Targets isotope-based contamination-control reasoning."
        if "artifacts" in lower:
            return "Adds cross-lab artifact interpretation need."
        if "quality-control checklist" in lower or "pollution exclusion" in lower:
            return "Directly targets end-to-end pollution exclusion workflow."
        return "Topically relevant to EOM retrieval evaluation expansion."

    def _trim_text(self, text: str, limit: int) -> str:
        cleaned = " ".join((text or "").split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3].rstrip() + "..."

    def _write_csv(self, path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _build_guidelines(self) -> str:
        return """# Retrieval Qrels Annotation Guidelines

## What counts as `relevant`
- The document directly answers the query, or provides evidence that would clearly help answer it.
- A document can still be relevant if it only covers one important facet of a multi-part query.

## What counts as `not_relevant`
- The document is off-topic, too generic, or only loosely connected by shared keywords.
- The snippet and title do not support the query intent, even if some terms overlap.

## Partial coverage
- If the document covers a substantial part of the query intent, mark it as relevant.
- Use `annotation_note` to explain what part is covered or missing.

## If the snippet is not enough
- Judge the title and snippet together.
- If the document is obviously relevant from title plus snippet, mark it relevant.
- If relevance is still unclear, leave a note in `annotation_note` rather than guessing.

## How to fill `candidate_relevance`
- Use `1` for relevant.
- Use `0` for not relevant.
- Keep `annotation_note` for ambiguity, partial coverage, or quality issues.
"""
