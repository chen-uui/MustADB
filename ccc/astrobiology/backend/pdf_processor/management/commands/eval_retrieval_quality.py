import csv
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pdf_processor.unified_rag_service import RAGException, UnifiedRAGService


RelevantKey = Tuple[str, str]


class Command(BaseCommand):
    help = "Evaluate retrieval quality (Recall@k, MRR@k, nDCG@k) from manually labeled qrels CSV."

    MODES = ("bm25", "dense", "hybrid", "hybrid_rerank")
    YES_VALUES = {"yes", "y", "true", "1"}
    HYBRID_MODES = {"hybrid", "hybrid_rerank"}
    COLLECTION_ENV_KEY = "WEAVIATE_COLLECTION_NAME"

    REQUIRED_QRELS_COLUMNS = ("qid", "question", "doc_id", "doc_name", "is_relevant")

    SUMMARY_COLUMNS = (
        "mode",
        "hybrid_alpha",
        "n_queries",
        "n_qrels",
        "recall_at_k",
        "mrr_at_k",
        "ndcg_at_k",
        "k",
        "n_queries_total",
        "n_queries_skipped_no_relevant",
    )

    DETAILS_COLUMNS = (
        "qid",
        "mode",
        "hybrid_alpha",
        "topk_doc_ids_or_names",
        "relevant_doc_ids_or_names",
        "hit_at_k",
        "reciprocal_rank",
        "recall_at_k_query",
        "ndcg_at_k_query",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--qrels",
            type=str,
            required=True,
            help="Path to manually filled qrels CSV.",
        )
        parser.add_argument(
            "--k",
            type=int,
            default=5,
            help="Top-k cutoff for metrics. Default: 5.",
        )
        parser.add_argument(
            "--modes",
            nargs="+",
            choices=self.MODES,
            default=None,
            help="Retrieval modes to evaluate. Default: all modes.",
        )
        parser.add_argument(
            "--hybrid-alpha",
            type=float,
            default=None,
            help="Override hybrid fusion alpha for hybrid/hybrid_rerank. Default: current runtime default (0.7).",
        )
        parser.add_argument(
            "--collection-name",
            type=str,
            default=None,
            help="Override Weaviate collection for this evaluation run only.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: evaluation/",
        )

    def handle(self, *args, **options):
        qrels_path = Path(str(options["qrels"])).expanduser().resolve()
        if not qrels_path.exists():
            raise CommandError(f"qrels csv not found: {qrels_path}")

        k = int(options["k"])
        if k < 1:
            raise CommandError("--k must be >= 1")

        hybrid_alpha = options.get("hybrid_alpha")
        if hybrid_alpha is not None and not 0.0 <= float(hybrid_alpha) <= 1.0:
            raise CommandError("--hybrid-alpha must be between 0 and 1")

        modes = list(options.get("modes") or self.MODES)
        collection_name = self._normalize_optional_str(options.get("collection_name"))
        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        evaluation = self.evaluate(
            qrels_path=qrels_path,
            k=k,
            modes=modes,
            hybrid_alpha=hybrid_alpha,
            collection_name=collection_name,
        )

        summary_path, details_path = self.write_outputs(
            out_dir=out_dir,
            summary_rows=evaluation["summary_rows"],
            details_rows=evaluation["details_rows"],
        )

        self.stdout.write(f"qrels_path={qrels_path}")
        self.stdout.write(f"modes={','.join(modes)}")
        self.stdout.write(f"k={k}")
        if hybrid_alpha is not None:
            self.stdout.write(f"hybrid_alpha={self._fmt(hybrid_alpha)}")
        if collection_name:
            self.stdout.write(f"collection_name={collection_name}")
        self.stdout.write(f"n_queries_total={evaluation['n_queries_total']}")
        self.stdout.write(
            f"n_queries_skipped_no_relevant={evaluation['n_queries_skipped_no_relevant']}"
        )
        self.stdout.write(f"n_qrels={evaluation['n_qrels_total']}")
        self.stdout.write(f"summary_path={summary_path}")
        self.stdout.write(f"details_path={details_path}")

    def evaluate(
        self,
        *,
        qrels_path: Path,
        k: int,
        modes: Sequence[str],
        hybrid_alpha: Optional[float] = None,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        qrels_data = self._load_qrels(qrels_path)
        query_order: List[str] = qrels_data["query_order"]  # type: ignore[assignment]
        questions_by_qid: Dict[str, str] = qrels_data["questions_by_qid"]  # type: ignore[assignment]
        relevant_by_qid: Dict[str, Set[RelevantKey]] = qrels_data["relevant_by_qid"]  # type: ignore[assignment]

        if not query_order:
            raise CommandError(f"qrels csv has no valid rows: {qrels_path}")

        env_backup = self._backup_env(self.COLLECTION_ENV_KEY)
        self._apply_collection_env(collection_name)
        try:
            service = UnifiedRAGService()
            if not service.initialize():
                raise CommandError("UnifiedRAGService initialization failed")

            summary_rows: List[Dict[str, str]] = []
            details_rows: List[Dict[str, str]] = []

            n_queries_total = len(query_order)
            n_queries_skipped_no_relevant = sum(
                1 for qid in query_order if len(relevant_by_qid.get(qid, set())) == 0
            )
            n_qrels_total = sum(len(relevant_by_qid.get(qid, set())) for qid in query_order)

            for mode in modes:
                recall_values: List[float] = []
                reciprocal_ranks: List[float] = []
                ndcg_values: List[float] = []
                rendered_alpha = self._render_hybrid_alpha(mode=mode, hybrid_alpha=hybrid_alpha)

                for qid in query_order:
                    question = questions_by_qid.get(qid, "").strip()
                    relevant_targets = relevant_by_qid.get(qid, set())
                    if not relevant_targets:
                        continue

                    if not question:
                        self.stderr.write(
                            self.style.WARNING(f"skip qid={qid}: empty question in qrels")
                        )
                        continue

                    mode_hybrid_alpha = self._resolve_hybrid_alpha(mode=mode, hybrid_alpha=hybrid_alpha)

                    try:
                        results = service.search(
                            question,
                            limit=k,
                            retrieval_mode=mode,
                            hybrid_alpha=mode_hybrid_alpha,
                        )
                    except RAGException as exc:
                        self.stderr.write(
                            self.style.WARNING(
                                f"search failed qid={qid} mode={mode}: {exc.message}; treat as empty retrieval"
                            )
                        )
                        results = []
                    except Exception as exc:
                        self.stderr.write(
                            self.style.WARNING(
                                f"search failed qid={qid} mode={mode}: {exc}; treat as empty retrieval"
                            )
                        )
                        results = []

                    unique_results = self._collapse_results_to_unique_documents(results)
                    topk_labels: List[str] = []
                    matched_targets: Set[RelevantKey] = set()
                    first_relevant_rank: Optional[int] = None
                    binary_relevances: List[int] = []

                    for rank, result in enumerate(unique_results[:k], start=1):
                        doc_id = self._normalize_id(getattr(result, "document_id", ""))
                        doc_name = self._normalize_name(getattr(result, "title", ""))
                        topk_labels.append(self._format_item_label(doc_id, doc_name))

                        matched_key = self._match_relevant_key(
                            doc_id=doc_id,
                            doc_name=doc_name,
                            relevant_targets=relevant_targets,
                        )
                        is_relevant = matched_key is not None
                        binary_relevances.append(1 if is_relevant else 0)
                        if not is_relevant:
                            continue

                        matched_targets.add(matched_key)
                        if first_relevant_rank is None:
                            first_relevant_rank = rank

                    hit_at_k = 1 if first_relevant_rank is not None else 0
                    reciprocal_rank = (
                        1.0 / float(first_relevant_rank) if first_relevant_rank is not None else 0.0
                    )
                    recall_at_k_query = float(len(matched_targets)) / float(len(relevant_targets))
                    ndcg_at_k_query = self._compute_ndcg_at_k(
                        binary_relevances=binary_relevances,
                        n_relevant=len(relevant_targets),
                        k=k,
                    )

                    recall_values.append(recall_at_k_query)
                    reciprocal_ranks.append(reciprocal_rank)
                    ndcg_values.append(ndcg_at_k_query)

                    details_rows.append(
                        {
                            "qid": qid,
                            "mode": mode,
                            "hybrid_alpha": rendered_alpha,
                            "topk_doc_ids_or_names": "; ".join(topk_labels),
                            "relevant_doc_ids_or_names": "; ".join(
                                self._format_relevant_targets(relevant_targets)
                            ),
                            "hit_at_k": str(hit_at_k),
                            "reciprocal_rank": self._fmt(reciprocal_rank),
                            "recall_at_k_query": self._fmt(recall_at_k_query),
                            "ndcg_at_k_query": self._fmt(ndcg_at_k_query),
                        }
                    )

                n_queries_eval = len(recall_values)
                recall_at_k = sum(recall_values) / float(n_queries_eval) if n_queries_eval > 0 else 0.0
                mrr_at_k = (
                    sum(reciprocal_ranks) / float(n_queries_eval) if n_queries_eval > 0 else 0.0
                )
                ndcg_at_k = sum(ndcg_values) / float(n_queries_eval) if n_queries_eval > 0 else 0.0

                summary_rows.append(
                    {
                        "mode": mode,
                        "hybrid_alpha": rendered_alpha,
                        "n_queries": str(n_queries_eval),
                        "n_qrels": str(n_qrels_total),
                        "recall_at_k": self._fmt(recall_at_k),
                        "mrr_at_k": self._fmt(mrr_at_k),
                        "ndcg_at_k": self._fmt(ndcg_at_k),
                        "k": str(k),
                        "n_queries_total": str(n_queries_total),
                        "n_queries_skipped_no_relevant": str(n_queries_skipped_no_relevant),
                    }
                )
        finally:
            self._restore_env(env_backup)

        return {
            "summary_rows": summary_rows,
            "details_rows": details_rows,
            "n_queries_total": n_queries_total,
            "n_queries_skipped_no_relevant": n_queries_skipped_no_relevant,
            "n_qrels_total": n_qrels_total,
        }

    def write_outputs(
        self,
        *,
        out_dir: Path,
        summary_rows: Sequence[Dict[str, str]],
        details_rows: Sequence[Dict[str, str]],
    ) -> Tuple[Path, Path]:
        summary_path = out_dir / "retrieval_quality_summary.csv"
        details_path = out_dir / "retrieval_quality_details.csv"
        self._write_csv(summary_path, self.SUMMARY_COLUMNS, summary_rows)
        self._write_csv(details_path, self.DETAILS_COLUMNS, details_rows)
        return summary_path, details_path

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "evaluation").resolve()

    def _backup_env(self, *keys: str) -> Dict[str, Optional[str]]:
        return {key: os.environ.get(key) for key in keys}

    def _restore_env(self, backup: Dict[str, Optional[str]]) -> None:
        for key, value in backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _apply_collection_env(self, collection_name: Optional[str]) -> None:
        if collection_name:
            os.environ[self.COLLECTION_ENV_KEY] = collection_name
        else:
            os.environ.pop(self.COLLECTION_ENV_KEY, None)

    def _normalize_optional_str(self, value: Any) -> Optional[str]:
        normalized = str(value or "").strip()
        return normalized or None

    def _resolve_hybrid_alpha(self, *, mode: str, hybrid_alpha: Optional[float]) -> Optional[float]:
        if mode not in self.HYBRID_MODES:
            return None
        if hybrid_alpha is None:
            return UnifiedRAGService.DEFAULT_HYBRID_ALPHA
        return float(hybrid_alpha)

    def _render_hybrid_alpha(self, *, mode: str, hybrid_alpha: Optional[float]) -> str:
        resolved = self._resolve_hybrid_alpha(mode=mode, hybrid_alpha=hybrid_alpha)
        if resolved is None:
            return ""
        return self._fmt(resolved)

    def _load_qrels(self, qrels_path: Path) -> Dict[str, Any]:
        with qrels_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise CommandError(f"qrels csv has no header: {qrels_path}")

            missing_columns = [
                col for col in self.REQUIRED_QRELS_COLUMNS if col not in reader.fieldnames
            ]
            if missing_columns:
                raise CommandError(
                    f"qrels csv missing required columns: {', '.join(missing_columns)}"
                )

            query_order: List[str] = []
            query_seen: Set[str] = set()
            questions_by_qid: Dict[str, str] = {}
            relevant_by_qid: Dict[str, Set[RelevantKey]] = {}

            for idx, row in enumerate(reader, start=2):
                qid = str(row.get("qid", "") or "").strip()
                question = str(row.get("question", "") or "").strip()
                if not qid:
                    raise CommandError(f"qrels csv row {idx}: qid is required")

                if qid not in query_seen:
                    query_order.append(qid)
                    query_seen.add(qid)
                    relevant_by_qid[qid] = set()

                existing_question = questions_by_qid.get(qid, "")
                if not existing_question:
                    questions_by_qid[qid] = question
                elif question and existing_question != question:
                    raise CommandError(
                        f"qrels csv row {idx}: inconsistent question for qid={qid}"
                    )

                is_relevant = str(row.get("is_relevant", "") or "").strip().lower()
                if is_relevant not in self.YES_VALUES:
                    continue

                doc_id = self._normalize_id(row.get("doc_id", ""))
                doc_name = self._normalize_name(row.get("doc_name", ""))

                if doc_id:
                    relevant_by_qid[qid].add(("id", doc_id))
                elif doc_name:
                    relevant_by_qid[qid].add(("name", doc_name))

        return {
            "query_order": query_order,
            "questions_by_qid": questions_by_qid,
            "relevant_by_qid": relevant_by_qid,
        }

    def _normalize_id(self, value: Any) -> str:
        return str(value or "").strip()

    def _normalize_name(self, value: Any) -> str:
        return str(value or "").strip().lower()

    def _match_relevant_key(
        self,
        *,
        doc_id: str,
        doc_name: str,
        relevant_targets: Set[RelevantKey],
    ) -> Optional[RelevantKey]:
        if doc_id and ("id", doc_id) in relevant_targets:
            return ("id", doc_id)
        if doc_name and ("name", doc_name) in relevant_targets:
            return ("name", doc_name)
        return None

    def _collapse_results_to_unique_documents(self, results: Sequence[Any]) -> List[Any]:
        unique_results: List[Any] = []
        seen_doc_keys: Set[RelevantKey] = set()

        for result in results:
            doc_key = self._make_result_doc_key(result)
            if doc_key in seen_doc_keys:
                continue
            seen_doc_keys.add(doc_key)
            unique_results.append(result)

        return unique_results

    def _make_result_doc_key(self, result: Any) -> RelevantKey:
        doc_id = self._normalize_id(getattr(result, "document_id", ""))
        doc_name = self._normalize_name(getattr(result, "title", ""))
        if doc_id:
            return ("id", doc_id)
        if doc_name:
            return ("name", doc_name)
        page = getattr(result, "page", "")
        chunk_index = getattr(result, "chunk_index", "")
        return ("name", f"unknown:{page}:{chunk_index}")

    def _compute_ndcg_at_k(self, *, binary_relevances: Sequence[int], n_relevant: int, k: int) -> float:
        if k < 1 or n_relevant < 1:
            return 0.0

        dcg = 0.0
        for rank, relevance in enumerate(binary_relevances[:k], start=1):
            if relevance <= 0:
                continue
            dcg += float(relevance) / self._log2(rank + 1)

        ideal_hits = min(n_relevant, k)
        idcg = 0.0
        for rank in range(1, ideal_hits + 1):
            idcg += 1.0 / self._log2(rank + 1)

        if idcg <= 0.0:
            return 0.0
        return min(dcg / idcg, 1.0)

    def _log2(self, value: int) -> float:
        return math.log2(float(value))

    def _format_item_label(self, doc_id: str, doc_name: str) -> str:
        if doc_id:
            return f"id:{doc_id}"
        if doc_name:
            return f"name:{doc_name}"
        return "unknown"

    def _format_relevant_targets(self, targets: Set[RelevantKey]) -> List[str]:
        rendered = []
        for key_type, value in sorted(targets):
            rendered.append(f"{key_type}:{value}")
        return rendered

    def _fmt(self, value: float) -> str:
        return f"{value:.4f}"

    def _write_csv(
        self,
        path: Path,
        fieldnames: Sequence[str],
        rows: Sequence[Dict[str, str]],
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
