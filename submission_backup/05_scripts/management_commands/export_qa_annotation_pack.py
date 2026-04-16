import csv
import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pdf_processor.models import PDFDocument
from pdf_processor.unified_rag_service import UnifiedRAGService


class Command(BaseCommand):
    help = "Export a human-annotation QA pack from real UnifiedRAG answers and evidence sources."

    DEFAULT_QRELS = "evaluation/retrieval_qrels_seed.csv"
    DEFAULT_CONFIGS = ("dense", "hybrid_rerank:0.7")
    ENV_KEYS = (
        "WEAVIATE_COLLECTION_NAME",
        "RAG_RETRIEVAL_MODE",
        "RAG_TOP_K",
        "RAG_RERANK_K",
        "RAG_HYBRID_ALPHA",
        "RAG_CONTEXT_TOKEN_LIMIT",
    )
    CSV_COLUMNS = (
        "sample_id",
        "qid",
        "query",
        "mode",
        "alpha",
        "collection_name",
        "retrieved_doc_ids",
        "retrieved_evidence_text",
        "model_answer",
        "source_paths",
        "notes_for_annotator",
        "answer_correct",
        "evidence_support",
        "unsupported_span_note",
        "annotation_note",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--qrels",
            type=str,
            default=None,
            help="Path to retrieval qrels CSV. Default: evaluation/retrieval_qrels_seed.csv",
        )
        parser.add_argument(
            "--collection-name",
            type=str,
            default=None,
            help="Weaviate collection to query. Default: runtime default collection.",
        )
        parser.add_argument(
            "--configs",
            nargs="+",
            default=list(self.DEFAULT_CONFIGS),
            help="QA configs as mode or mode:alpha, e.g. dense hybrid_rerank:0.7",
        )
        parser.add_argument(
            "--top-k",
            type=int,
            default=5,
            help="Top-k retrieval contexts for QA generation. Default: 5.",
        )
        parser.add_argument(
            "--rerank-k",
            type=int,
            default=None,
            help="Rerank candidate size. Default: top_k * 2.",
        )
        parser.add_argument(
            "--max-evidence-snippets",
            type=int,
            default=3,
            help="Maximum evidence snippets per sample. Default: 3.",
        )
        parser.add_argument(
            "--snippet-char-limit",
            type=int,
            default=500,
            help="Character limit per evidence snippet. Default: 500.",
        )
        parser.add_argument(
            "--limit-queries",
            type=int,
            default=0,
            help="Optional limit on number of unique qids. Default: 0 (all).",
        )
        parser.add_argument(
            "--sample-id-start",
            type=int,
            default=1,
            help="Starting integer for sequential sample IDs. Default: 1.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/annotation_pack_paper_support_<timestamp>/",
        )

    def handle(self, *args, **options):
        qrels_path = self._resolve_qrels_path(options.get("qrels"))
        collection_name = self._normalize_optional_str(options.get("collection_name"))
        top_k = int(options["top_k"])
        if top_k < 1:
            raise CommandError("--top-k must be >= 1")

        rerank_k = options.get("rerank_k")
        if rerank_k is not None and int(rerank_k) < 1:
            raise CommandError("--rerank-k must be >= 1")

        max_evidence_snippets = int(options["max_evidence_snippets"])
        if max_evidence_snippets < 1:
            raise CommandError("--max-evidence-snippets must be >= 1")

        snippet_char_limit = int(options["snippet_char_limit"])
        if snippet_char_limit < 80:
            raise CommandError("--snippet-char-limit must be >= 80")

        configs = self._parse_configs(options.get("configs") or [])
        queries = self._load_unique_queries(qrels_path, limit_queries=int(options.get("limit_queries") or 0))
        sample_id_start = int(options.get("sample_id_start") or 1)
        if sample_id_start < 1:
            raise CommandError("--sample-id-start must be >= 1")
        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        doc_map = self._load_document_metadata()
        rows: List[Dict[str, str]] = []
        raw_records: List[Dict[str, object]] = []

        self.stdout.write(f"qrels_path={qrels_path}")
        self.stdout.write(f"collection_name={collection_name or 'runtime_default'}")
        self.stdout.write(f"queries={len(queries)} configs={len(configs)}")

        sample_counter = sample_id_start - 1
        for mode, alpha in configs:
            with self._runtime_env(
                collection_name=collection_name,
                mode=mode,
                top_k=top_k,
                rerank_k=int(rerank_k) if rerank_k is not None else max(top_k * 2, top_k),
                alpha=alpha,
            ):
                service = UnifiedRAGService(collection_name=collection_name)
                if not service.initialize():
                    raise CommandError(f"Failed to initialize UnifiedRAGService for mode={mode}")

                for qid, query in queries:
                    sample_counter += 1
                    answer = service.ask_question(query)
                    selected_sources = self._select_evidence_sources(
                        answer.sources,
                        max_items=max_evidence_snippets,
                    )
                    rows.append(
                        self._build_csv_row(
                            qid=qid,
                            query=query,
                            sample_index=sample_counter,
                            mode=mode,
                            alpha=alpha,
                            collection_name=service.collection_name,
                            answer_text=answer.answer,
                            sources=selected_sources,
                            doc_map=doc_map,
                            snippet_char_limit=snippet_char_limit,
                        )
                    )
                    raw_records.append(
                        {
                            "qid": qid,
                            "query": query,
                            "mode": mode,
                            "alpha": alpha,
                            "collection_name": service.collection_name,
                            "answer": answer.to_dict(),
                        }
                    )
                    self.stdout.write(
                        f"exported qid={qid} mode={mode} alpha={self._format_alpha(alpha)} "
                        f"sources={len(selected_sources)}"
                    )

        csv_path = out_dir / "qa_annotation_samples.csv"
        raw_jsonl_path = out_dir / "qa_annotation_samples_raw.jsonl"
        guide_path = out_dir / "annotation_guidelines.md"
        metadata_path = out_dir / "annotation_pack_metadata.json"

        self._write_csv(csv_path, rows)
        self._write_jsonl(raw_jsonl_path, raw_records)
        guide_path.write_text(self._build_guidelines_markdown(), encoding="utf-8")
        metadata_path.write_text(
            json.dumps(
                {
                    "qrels_path": str(qrels_path),
                    "collection_name": collection_name or "runtime_default",
                    "configs": [{"mode": mode, "alpha": alpha} for mode, alpha in configs],
                    "top_k": top_k,
                    "rerank_k": int(rerank_k) if rerank_k is not None else max(top_k * 2, top_k),
                    "max_evidence_snippets": max_evidence_snippets,
                    "snippet_char_limit": snippet_char_limit,
                    "n_queries": len(queries),
                    "n_samples": len(rows),
                    "generated_at": datetime.now().isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS(f"csv_path={csv_path}"))
        self.stdout.write(self.style.SUCCESS(f"guide_path={guide_path}"))
        self.stdout.write(self.style.SUCCESS(f"raw_jsonl_path={raw_jsonl_path}"))
        self.stdout.write(self.style.SUCCESS(f"samples={len(rows)}"))

    def _resolve_qrels_path(self, path_arg: Optional[str]) -> Path:
        if path_arg and path_arg.strip():
            qrels_path = Path(path_arg).expanduser().resolve()
        else:
            qrels_path = (Path(settings.BASE_DIR) / self.DEFAULT_QRELS).resolve()
        if not qrels_path.exists():
            raise CommandError(f"qrels csv not found: {qrels_path}")
        return qrels_path

    def _resolve_out_dir(self, path_arg: Optional[str]) -> Path:
        if path_arg and path_arg.strip():
            return Path(path_arg).expanduser().resolve()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"annotation_pack_paper_support_{timestamp}").resolve()

    def _parse_configs(self, raw_items: Sequence[str]) -> List[Tuple[str, Optional[float]]]:
        valid_modes = UnifiedRAGService.VALID_RETRIEVAL_MODES
        configs: List[Tuple[str, Optional[float]]] = []
        for raw in raw_items:
            item = str(raw).strip()
            if not item:
                continue
            if ":" in item:
                mode_raw, alpha_raw = item.split(":", 1)
            else:
                mode_raw, alpha_raw = item, ""
            mode = mode_raw.strip().lower()
            if mode not in valid_modes:
                raise CommandError(f"invalid config mode: {mode}")
            alpha: Optional[float] = None
            if alpha_raw.strip():
                try:
                    alpha = float(alpha_raw)
                except ValueError as exc:
                    raise CommandError(f"invalid alpha in config '{item}'") from exc
                if not 0.0 <= alpha <= 1.0:
                    raise CommandError(f"alpha must be between 0 and 1 in config '{item}'")
            configs.append((mode, alpha))
        if not configs:
            raise CommandError("no valid configs provided")
        return configs

    def _load_unique_queries(self, qrels_path: Path, limit_queries: int) -> List[Tuple[str, str]]:
        queries: List[Tuple[str, str]] = []
        seen = set()
        with qrels_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"qid", "question"}
            missing = required.difference(set(reader.fieldnames or []))
            if missing:
                raise CommandError(f"qrels missing required columns: {sorted(missing)}")
            for row in reader:
                qid = str(row.get("qid", "")).strip()
                question = str(row.get("question", "")).strip()
                if not qid or not question or qid in seen:
                    continue
                seen.add(qid)
                queries.append((qid, question))
                if limit_queries > 0 and len(queries) >= limit_queries:
                    break
        if not queries:
            raise CommandError(f"no usable qids found in qrels: {qrels_path}")
        return queries

    def _load_document_metadata(self) -> Dict[str, Dict[str, str]]:
        doc_map: Dict[str, Dict[str, str]] = {}
        for doc in PDFDocument.objects.all().only("id", "title", "filename", "file_path"):
            doc_map[str(doc.id)] = {
                "title": doc.title or "",
                "filename": doc.filename or "",
                "file_path": doc.file_path or "",
            }
        return doc_map

    def _select_evidence_sources(
        self,
        sources: Sequence[Dict[str, object]],
        max_items: int,
    ) -> List[Dict[str, object]]:
        used_sources = [source for source in sources if bool(source.get("used"))]
        fallback_sources = [source for source in sources if not bool(source.get("used"))]
        picked: List[Dict[str, object]] = []
        seen_keys = set()

        for source in list(used_sources) + list(fallback_sources):
            key = (
                str(source.get("document_id", "")).strip(),
                int(source.get("page", 0) or 0),
                self._normalize_text(str(source.get("content", "")))[:120],
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            picked.append(dict(source))
            if len(picked) >= max_items:
                break
        return picked

    def _build_csv_row(
        self,
        *,
        qid: str,
        query: str,
        sample_index: int,
        mode: str,
        alpha: Optional[float],
        collection_name: str,
        answer_text: str,
        sources: Sequence[Dict[str, object]],
        doc_map: Dict[str, Dict[str, str]],
        snippet_char_limit: int,
    ) -> Dict[str, str]:
        sample_id = f"S{sample_index:03d}"
        doc_ids: List[str] = []
        source_paths: List[str] = []
        evidence_blocks: List[str] = []

        for idx, source in enumerate(sources, start=1):
            document_id = str(source.get("document_id", "") or "").strip()
            meta = doc_map.get(document_id, {})
            if document_id and document_id not in doc_ids:
                doc_ids.append(document_id)

            file_path = meta.get("file_path", "")
            if file_path and file_path not in source_paths:
                source_paths.append(file_path)

            title = str(source.get("title", "") or meta.get("title") or meta.get("filename") or "Unknown document")
            page = int(source.get("page", 0) or 0)
            snippet = self._trim_text(str(source.get("content", "") or ""), snippet_char_limit)
            used_label = "yes" if bool(source.get("used")) else "no"
            evidence_blocks.append(
                f"[E{idx}] title={title} | page={page} | doc_id={document_id or 'NA'} | used={used_label}\n{snippet}"
            )

        return {
            "sample_id": sample_id,
            "qid": qid,
            "query": query,
            "mode": mode,
            "alpha": self._format_alpha(alpha),
            "collection_name": collection_name,
            "retrieved_doc_ids": "; ".join(doc_ids) if doc_ids else "",
            "retrieved_evidence_text": "\n\n".join(evidence_blocks),
            "model_answer": answer_text or "",
            "source_paths": "; ".join(source_paths),
            "notes_for_annotator": (
                "Judge answer correctness and support only against the provided evidence snippets. "
                "If part of the answer lacks support, mark evidence_support accordingly and note that span."
            ),
            "answer_correct": "",
            "evidence_support": "",
            "unsupported_span_note": "",
            "annotation_note": "",
        }

    def _write_csv(self, path: Path, rows: Sequence[Dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _write_jsonl(self, path: Path, rows: Iterable[Dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    @contextmanager
    def _runtime_env(
        self,
        *,
        collection_name: Optional[str],
        mode: str,
        top_k: int,
        rerank_k: int,
        alpha: Optional[float],
    ):
        backup = {key: os.environ.get(key) for key in self.ENV_KEYS}
        try:
            if collection_name:
                os.environ["WEAVIATE_COLLECTION_NAME"] = collection_name
            else:
                os.environ.pop("WEAVIATE_COLLECTION_NAME", None)
            os.environ["RAG_RETRIEVAL_MODE"] = mode
            os.environ["RAG_TOP_K"] = str(top_k)
            os.environ["RAG_RERANK_K"] = str(rerank_k)
            if alpha is None:
                os.environ.pop("RAG_HYBRID_ALPHA", None)
            else:
                os.environ["RAG_HYBRID_ALPHA"] = str(alpha)
            os.environ.pop("RAG_CONTEXT_TOKEN_LIMIT", None)
            yield
        finally:
            for key, value in backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _format_alpha(self, alpha: Optional[float]) -> str:
        if alpha is None:
            return "NA"
        return f"{float(alpha):.1f}"

    def _trim_text(self, text: str, limit: int) -> str:
        cleaned = self._normalize_text(text)
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3].rstrip() + "..."

    def _normalize_text(self, text: str) -> str:
        return " ".join((text or "").split())

    def _normalize_optional_str(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _build_guidelines_markdown(self) -> str:
        return """# QA Annotation Guidelines

## `answer_correct`
- `1`: The answer is factually correct based on the provided evidence.
- `0`: The answer is incorrect, contradicts the evidence, or clearly overstates what the evidence says.
- `unclear`: The provided evidence is insufficient to judge correctness confidently.

## `evidence_support`
- `supported`: The answer is supported by the provided evidence snippets.
- `partially_supported`: Some answer content is supported, but some content is missing support.
- `unsupported`: The answer is not supported by the provided evidence.
- `unclear`: The evidence is too ambiguous or incomplete to judge support confidently.

## `unsupported_span_note`
- Only note the unsupported part of the answer.
- Do not rewrite the whole answer.
- Keep it short and specific.

## Annotation Rules
- Judge only against the evidence snippets in this pack.
- Do not infer support from outside knowledge or from documents not shown here.
- If the answer might be true elsewhere but is not supported here, mark it as unsupported or partially supported.
- If anything is ambiguous, write the reason in `annotation_note`.
"""
