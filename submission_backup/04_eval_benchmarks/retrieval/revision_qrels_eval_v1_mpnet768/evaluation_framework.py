#!/usr/bin/env python3
"""Standalone retrieval evaluation framework for the EOM benchmark.

The script has two stages:

1. make-qrels-template: build a pooled annotation sheet from retrieval results.
2. evaluate: compute Recall@K, nDCG@K, and MRR@10 from completed qrels.

Only the Python standard library is used so the evaluator can run outside the
project's Django runtime.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Sequence, Set, Tuple


DEFAULT_KS = (1, 3, 5, 10)
DEFAULT_RELEVANCE_THRESHOLD = 1
CANONICAL_METHODS = ("bm25", "dense", "hybrid", "hybrid_rerank")
METHOD_LABELS = {
    "bm25": "BM25",
    "dense": "Dense retrieval",
    "hybrid": "Hybrid retrieval",
    "hybrid_rerank": "Hybrid + rerank",
}
METHOD_ALIASES = {
    "bm25": "bm25",
    "sparse": "bm25",
    "lexical": "bm25",
    "dense": "dense",
    "dense_retrieval": "dense",
    "vector": "dense",
    "embedding": "dense",
    "hybrid": "hybrid",
    "hybrid_retrieval": "hybrid",
    "hybrid_rerank": "hybrid_rerank",
    "hybrid_reranker": "hybrid_rerank",
    "hybrid+rerank": "hybrid_rerank",
    "hybrid_plus_rerank": "hybrid_rerank",
    "rerank": "hybrid_rerank",
    "reranker": "hybrid_rerank",
}
RESULT_LIST_KEYS = ("results", "documents", "docs", "hits", "chunks", "retrieved")
TOP_LEVEL_RESULT_KEYS = ("results", "runs", "retrieval_results")
DOC_ID_KEYS = (
    "doc_id",
    "document_id",
    "source_doc_id",
    "paper_id",
    "documentId",
    "docId",
    "id",
    "chunk_id",
    "chunkId",
)
TITLE_KEYS = ("doc_title", "document_title", "title", "doc_name", "name", "filename")


@dataclass(frozen=True)
class Query:
    qid: str
    question: str


@dataclass
class RetrievedItem:
    method: str
    qid: str
    doc_id: str
    rank: int
    score: Optional[float] = None
    title: str = ""


@dataclass
class PerQueryScore:
    method: str
    qid: str
    question: str
    is_evaluable: bool
    n_qrels: int
    n_relevant: int
    retrieved_at_10: int
    judged_at_10: int
    recall: Dict[int, Optional[float]]
    ndcg: Dict[int, Optional[float]]
    mrr_at_10: Optional[float]


class EvaluationError(RuntimeError):
    pass


def load_queries(path: Path) -> List[Query]:
    queries: List[Query] = []
    seen_qids: Set[str] = set()

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        content = line.strip()
        if not content:
            continue
        try:
            item = json.loads(content)
        except json.JSONDecodeError as exc:
            raise EvaluationError(f"invalid JSONL at {path}:{line_no}: {exc}") from exc
        if not isinstance(item, dict):
            raise EvaluationError(f"invalid query at {path}:{line_no}: expected object")

        qid = str(item.get("qid", "")).strip()
        question = str(item.get("question", "")).strip()
        if not qid:
            raise EvaluationError(f"invalid query at {path}:{line_no}: qid is required")
        if not question:
            raise EvaluationError(f"invalid query at {path}:{line_no}: question is required")
        if qid in seen_qids:
            raise EvaluationError(f"duplicate qid at {path}:{line_no}: {qid}")

        seen_qids.add(qid)
        queries.append(Query(qid=qid, question=question))

    if not queries:
        raise EvaluationError(f"queries file has no rows: {path}")
    return queries


def load_qrels(path: Path) -> Dict[str, Dict[str, int]]:
    """Load qrels CSV with required qid, doc_id, relevance columns."""

    qrels: Dict[str, Dict[str, int]] = defaultdict(dict)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise EvaluationError(f"qrels CSV has no header: {path}")
        fields = set(reader.fieldnames)
        missing = {"qid", "doc_id", "relevance"} - fields
        if missing:
            raise EvaluationError(f"qrels CSV missing required columns: {', '.join(sorted(missing))}")

        for row_no, row in enumerate(reader, start=2):
            qid = str(row.get("qid", "")).strip()
            doc_id = str(row.get("doc_id", "")).strip()
            raw_relevance = str(row.get("relevance", "")).strip()
            if not qid or not doc_id:
                raise EvaluationError(f"qrels row {row_no}: qid and doc_id are required")
            if raw_relevance == "":
                raise EvaluationError(
                    f"qrels row {row_no}: relevance is blank; finish annotation before evaluation"
                )
            try:
                relevance = int(raw_relevance)
            except ValueError as exc:
                raise EvaluationError(
                    f"qrels row {row_no}: relevance must be integer 0, 1, or 2"
                ) from exc
            if relevance not in {0, 1, 2}:
                raise EvaluationError(f"qrels row {row_no}: relevance must be 0, 1, or 2")

            previous = qrels[qid].get(doc_id)
            if previous is not None and previous != relevance:
                raise EvaluationError(
                    f"qrels row {row_no}: conflicting relevance for qid={qid} doc_id={doc_id}"
                )
            qrels[qid][doc_id] = relevance

    return {qid: dict(docs) for qid, docs in qrels.items()}


def load_json_or_jsonl(path: Path) -> Any:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise EvaluationError(f"retrieval results file is empty: {path}")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some systems write JSONL with a .json suffix.
        try:
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError as exc:
            raise EvaluationError(f"invalid JSON or JSONL retrieval results: {path}") from exc


def normalize_method(raw_method: Any) -> str:
    text = str(raw_method or "").strip()
    if not text:
        return ""
    key = (
        text.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("__", "_")
    )
    plus_key = key.replace("_+_", "+").replace("_plus_", "_plus_")
    compact = key.replace("_", "")
    if text.lower().replace(" ", "") == "hybrid+rerank":
        return "hybrid_rerank"
    if key in METHOD_ALIASES:
        return METHOD_ALIASES[key]
    if plus_key in METHOD_ALIASES:
        return METHOD_ALIASES[plus_key]
    if compact == "hybridrerank":
        return "hybrid_rerank"
    return key


def load_retrieval_results(path: Path) -> Dict[str, Dict[str, List[RetrievedItem]]]:
    payload = load_json_or_jsonl(path)
    grouped: DefaultDict[str, DefaultDict[str, List[RetrievedItem]]] = defaultdict(
        lambda: defaultdict(list)
    )
    parse_payload(payload, grouped)
    normalized = normalize_grouped_results(grouped)
    if not normalized:
        raise EvaluationError(f"no retrieval results could be parsed from {path}")
    return normalized


def parse_payload(
    payload: Any,
    grouped: DefaultDict[str, DefaultDict[str, List[RetrievedItem]]],
    default_method: str = "",
    default_qid: str = "",
) -> None:
    if isinstance(payload, list):
        parse_record_list(payload, grouped, default_method=default_method, default_qid=default_qid)
        return

    if not isinstance(payload, dict):
        return

    if any(key in payload for key in TOP_LEVEL_RESULT_KEYS):
        for key in TOP_LEVEL_RESULT_KEYS:
            value = payload.get(key)
            if value is not None:
                parse_payload(value, grouped, default_method=default_method, default_qid=default_qid)
        return

    if default_method:
        parse_method_payload(default_method, payload, grouped)
        return

    for method_key, method_payload in payload.items():
        method = normalize_method(method_key)
        if not method:
            continue
        if isinstance(method_payload, (dict, list)):
            parse_method_payload(method, method_payload, grouped)


def parse_record_list(
    records: Sequence[Any],
    grouped: DefaultDict[str, DefaultDict[str, List[RetrievedItem]]],
    default_method: str = "",
    default_qid: str = "",
) -> None:
    for index, record in enumerate(records, start=1):
        if isinstance(record, dict):
            method = normalize_method(
                record.get("method")
                or record.get("mode")
                or record.get("retrieval_method")
                or default_method
            )
            qid = str(record.get("qid") or record.get("query_id") or default_qid or "").strip()

            result_list = find_result_list(record)
            if method and qid and result_list is not None:
                parse_result_list(method, qid, result_list, grouped)
                continue

            if method and qid and extract_doc_id(record):
                add_result(method, qid, record, grouped, default_rank=index)
                continue

        if default_method and default_qid:
            add_result(default_method, default_qid, record, grouped, default_rank=index)


def parse_method_payload(
    method: str,
    payload: Any,
    grouped: DefaultDict[str, DefaultDict[str, List[RetrievedItem]]],
) -> None:
    method = normalize_method(method)
    if not method:
        return

    if isinstance(payload, list):
        parse_record_list(payload, grouped, default_method=method)
        return

    if not isinstance(payload, dict):
        return

    if "queries" in payload and isinstance(payload["queries"], dict):
        parse_method_payload(method, payload["queries"], grouped)
        return
    if "results" in payload and isinstance(payload["results"], dict):
        parse_method_payload(method, payload["results"], grouped)
        return

    for qid_key, query_payload in payload.items():
        qid = str(qid_key).strip()
        if not qid:
            continue

        if isinstance(query_payload, list):
            parse_result_list(method, qid, query_payload, grouped)
            continue
        if isinstance(query_payload, dict):
            result_list = find_result_list(query_payload)
            if result_list is not None:
                parse_result_list(method, qid, result_list, grouped)
            elif extract_doc_id(query_payload):
                add_result(method, qid, query_payload, grouped, default_rank=1)


def parse_result_list(
    method: str,
    qid: str,
    results: Sequence[Any],
    grouped: DefaultDict[str, DefaultDict[str, List[RetrievedItem]]],
) -> None:
    for rank, result in enumerate(results, start=1):
        add_result(method, qid, result, grouped, default_rank=rank)


def add_result(
    method: str,
    qid: str,
    raw_result: Any,
    grouped: DefaultDict[str, DefaultDict[str, List[RetrievedItem]]],
    default_rank: int,
) -> None:
    doc_id = extract_doc_id(raw_result)
    if not doc_id:
        return
    rank = extract_rank(raw_result, default_rank)
    score = extract_score(raw_result)
    title = extract_title(raw_result)
    grouped[method][qid].append(
        RetrievedItem(method=method, qid=qid, doc_id=doc_id, rank=rank, score=score, title=title)
    )


def find_result_list(record: Dict[str, Any]) -> Optional[Sequence[Any]]:
    for key in RESULT_LIST_KEYS:
        value = record.get(key)
        if isinstance(value, list):
            return value
    return None


def extract_doc_id(raw_result: Any) -> str:
    if isinstance(raw_result, str):
        return raw_result.strip()
    if not isinstance(raw_result, dict):
        return ""

    for key in DOC_ID_KEYS:
        value = raw_result.get(key)
        if value not in (None, ""):
            return str(value).strip()

    metadata = raw_result.get("metadata")
    if isinstance(metadata, dict):
        for key in DOC_ID_KEYS:
            value = metadata.get(key)
            if value not in (None, ""):
                return str(value).strip()
    source = raw_result.get("source")
    if isinstance(source, dict):
        for key in DOC_ID_KEYS:
            value = source.get(key)
            if value not in (None, ""):
                return str(value).strip()
    return ""


def extract_title(raw_result: Any) -> str:
    if not isinstance(raw_result, dict):
        return ""
    for key in TITLE_KEYS:
        value = raw_result.get(key)
        if value not in (None, ""):
            return str(value).strip()
    metadata = raw_result.get("metadata")
    if isinstance(metadata, dict):
        for key in TITLE_KEYS:
            value = metadata.get(key)
            if value not in (None, ""):
                return str(value).strip()
    return ""


def extract_rank(raw_result: Any, default_rank: int) -> int:
    if isinstance(raw_result, dict):
        for key in ("rank", "position", "idx"):
            value = raw_result.get(key)
            if value not in (None, ""):
                try:
                    return max(int(value), 1)
                except (TypeError, ValueError):
                    pass
    return int(default_rank)


def extract_score(raw_result: Any) -> Optional[float]:
    if not isinstance(raw_result, dict):
        return None
    for key in ("score", "similarity", "retrieval_score", "rerank_score"):
        value = raw_result.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def normalize_grouped_results(
    grouped: DefaultDict[str, DefaultDict[str, List[RetrievedItem]]]
) -> Dict[str, Dict[str, List[RetrievedItem]]]:
    normalized: Dict[str, Dict[str, List[RetrievedItem]]] = {}
    for method, by_qid in grouped.items():
        method_out: Dict[str, List[RetrievedItem]] = {}
        for qid, items in by_qid.items():
            sorted_items = sorted(items, key=lambda item: (item.rank, item.doc_id))
            seen_docs: Set[str] = set()
            deduped: List[RetrievedItem] = []
            for item in sorted_items:
                if item.doc_id in seen_docs:
                    continue
                seen_docs.add(item.doc_id)
                deduped.append(item)
            if deduped:
                method_out[qid] = deduped
        if method_out:
            normalized[method] = method_out
    return normalized


def generate_qrels_template(
    queries: Sequence[Query],
    results_by_method: Dict[str, Dict[str, List[RetrievedItem]]],
    out_path: Path,
    top_k: int,
) -> None:
    query_map = {query.qid: query.question for query in queries}
    fieldnames = (
        "qid",
        "doc_id",
        "relevance",
        "question",
        "doc_title",
        "method_sources",
        "notes",
    )
    rows: List[Dict[str, str]] = []

    for query in queries:
        pooled: Dict[str, Dict[str, Any]] = {}
        for method in sorted_methods(results_by_method):
            items = results_by_method.get(method, {}).get(query.qid, [])[:top_k]
            for item in items:
                entry = pooled.setdefault(
                    item.doc_id,
                    {
                        "qid": query.qid,
                        "doc_id": item.doc_id,
                        "relevance": "",
                        "question": query_map.get(query.qid, ""),
                        "doc_title": item.title,
                        "sources": [],
                        "notes": "",
                    },
                )
                if item.title and not entry["doc_title"]:
                    entry["doc_title"] = item.title
                entry["sources"].append(f"{method}:{item.rank}")

        for doc_id in sorted(pooled):
            entry = pooled[doc_id]
            rows.append(
                {
                    "qid": entry["qid"],
                    "doc_id": entry["doc_id"],
                    "relevance": "",
                    "question": entry["question"],
                    "doc_title": entry["doc_title"],
                    "method_sources": "; ".join(entry["sources"]),
                    "notes": "",
                }
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(out_path, fieldnames, rows)


def evaluate_all(
    queries: Sequence[Query],
    qrels: Dict[str, Dict[str, int]],
    results_by_method: Dict[str, Dict[str, List[RetrievedItem]]],
    ks: Sequence[int],
    relevance_threshold: int,
) -> Tuple[List[PerQueryScore], List[Dict[str, Any]], List[str]]:
    per_query: List[PerQueryScore] = []
    warnings: List[str] = []
    query_map = {query.qid: query.question for query in queries}
    qids = [query.qid for query in queries]

    for method in sorted_methods(results_by_method):
        method_results = results_by_method[method]
        for query in queries:
            query_qrels = qrels.get(query.qid, {})
            retrieved = method_results.get(query.qid, [])
            score = evaluate_query(
                method=method,
                qid=query.qid,
                question=query.question,
                qrels=query_qrels,
                retrieved=retrieved,
                ks=ks,
                relevance_threshold=relevance_threshold,
            )
            per_query.append(score)

        missing_qids = [qid for qid in qids if qid not in method_results]
        if missing_qids:
            preview = ", ".join(missing_qids[:8])
            suffix = "..." if len(missing_qids) > 8 else ""
            warnings.append(
                f"{method}: missing retrieval results for {len(missing_qids)} queries ({preview}{suffix})"
            )

    missing_qrels = [qid for qid in qids if qid not in qrels]
    if missing_qrels:
        preview = ", ".join(missing_qrels[:8])
        suffix = "..." if len(missing_qrels) > 8 else ""
        warnings.append(f"missing qrels for {len(missing_qrels)} queries ({preview}{suffix})")

    metrics_by_method = aggregate_method_scores(per_query, ks)
    return per_query, metrics_by_method, warnings


def evaluate_query(
    method: str,
    qid: str,
    question: str,
    qrels: Dict[str, int],
    retrieved: Sequence[RetrievedItem],
    ks: Sequence[int],
    relevance_threshold: int,
) -> PerQueryScore:
    relevant_docs = {doc_id for doc_id, rel in qrels.items() if rel >= relevance_threshold}
    n_relevant = len(relevant_docs)
    is_evaluable = n_relevant > 0
    ranked_doc_ids = [item.doc_id for item in retrieved]
    judged_at_10 = sum(1 for doc_id in ranked_doc_ids[:10] if doc_id in qrels)

    recall_scores: Dict[int, Optional[float]] = {}
    ndcg_scores: Dict[int, Optional[float]] = {}
    for k in ks:
        if is_evaluable:
            recall_scores[k] = recall_at_k(ranked_doc_ids, relevant_docs, k)
            ndcg_scores[k] = ndcg_at_k(ranked_doc_ids, qrels, k)
        else:
            recall_scores[k] = None
            ndcg_scores[k] = None

    mrr = reciprocal_rank_at_k(ranked_doc_ids, relevant_docs, 10) if is_evaluable else None

    return PerQueryScore(
        method=method,
        qid=qid,
        question=question,
        is_evaluable=is_evaluable,
        n_qrels=len(qrels),
        n_relevant=n_relevant,
        retrieved_at_10=min(len(ranked_doc_ids), 10),
        judged_at_10=judged_at_10,
        recall=recall_scores,
        ndcg=ndcg_scores,
        mrr_at_10=mrr,
    )


def recall_at_k(ranked_doc_ids: Sequence[str], relevant_docs: Set[str], k: int) -> float:
    if not relevant_docs:
        return 0.0
    retrieved = set(ranked_doc_ids[:k])
    return len(retrieved & relevant_docs) / float(len(relevant_docs))


def ndcg_at_k(ranked_doc_ids: Sequence[str], qrels: Dict[str, int], k: int) -> float:
    dcg = 0.0
    for rank, doc_id in enumerate(ranked_doc_ids[:k], start=1):
        rel = int(qrels.get(doc_id, 0))
        if rel <= 0:
            continue
        dcg += graded_gain(rel) / math.log2(rank + 1)

    ideal_rels = sorted((rel for rel in qrels.values() if rel > 0), reverse=True)[:k]
    idcg = 0.0
    for rank, rel in enumerate(ideal_rels, start=1):
        idcg += graded_gain(rel) / math.log2(rank + 1)

    if idcg <= 0:
        return 0.0
    return dcg / idcg


def graded_gain(relevance: int) -> float:
    return float((2 ** int(relevance)) - 1)


def reciprocal_rank_at_k(ranked_doc_ids: Sequence[str], relevant_docs: Set[str], k: int) -> float:
    for rank, doc_id in enumerate(ranked_doc_ids[:k], start=1):
        if doc_id in relevant_docs:
            return 1.0 / float(rank)
    return 0.0


def aggregate_method_scores(
    per_query_scores: Sequence[PerQueryScore],
    ks: Sequence[int],
) -> List[Dict[str, Any]]:
    grouped: DefaultDict[str, List[PerQueryScore]] = defaultdict(list)
    for row in per_query_scores:
        grouped[row.method].append(row)

    method_rows: List[Dict[str, Any]] = []
    for method in sorted_methods({method: {} for method in grouped}):
        rows = grouped[method]
        evaluable = [row for row in rows if row.is_evaluable]
        out: Dict[str, Any] = {
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "n_queries": len(rows),
            "n_evaluable_queries": len(evaluable),
            "n_queries_without_positive_qrels": len(rows) - len(evaluable),
            "n_qrels": sum(row.n_qrels for row in rows),
            "n_relevant": sum(row.n_relevant for row in rows),
        }
        for k in ks:
            out[f"recall_at_{k}"] = mean_optional(row.recall.get(k) for row in evaluable)
        for k in ks:
            out[f"ndcg_at_{k}"] = mean_optional(row.ndcg.get(k) for row in evaluable)
        out["mrr_at_10"] = mean_optional(row.mrr_at_10 for row in evaluable)
        method_rows.append(out)
    return method_rows


def mean_optional(values: Iterable[Optional[float]]) -> Optional[float]:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return statistics.fmean(clean)


def write_outputs(
    out_dir: Path,
    per_query_scores: Sequence[PerQueryScore],
    method_scores: Sequence[Dict[str, Any]],
    queries_path: Path,
    results_path: Path,
    qrels_path: Path,
    ks: Sequence[int],
    relevance_threshold: int,
    warnings: Sequence[str],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_metrics_by_method(out_dir / "metrics_by_method.csv", method_scores, ks)
    write_per_query_scores(out_dir / "per_query_scores.csv", per_query_scores, ks)
    (out_dir / "summary_report.md").write_text(
        build_summary_report(
            method_scores=method_scores,
            per_query_scores=per_query_scores,
            queries_path=queries_path,
            results_path=results_path,
            qrels_path=qrels_path,
            ks=ks,
            relevance_threshold=relevance_threshold,
            warnings=warnings,
        ),
        encoding="utf-8",
    )


def write_metrics_by_method(
    path: Path,
    method_scores: Sequence[Dict[str, Any]],
    ks: Sequence[int],
) -> None:
    fieldnames = [
        "method",
        "method_label",
        "n_queries",
        "n_evaluable_queries",
        "n_queries_without_positive_qrels",
        "n_qrels",
        "n_relevant",
    ]
    fieldnames += [f"recall_at_{k}" for k in ks]
    fieldnames += [f"ndcg_at_{k}" for k in ks]
    fieldnames += ["mrr_at_10"]

    rows: List[Dict[str, str]] = []
    for score in method_scores:
        rows.append({field: format_csv_value(score.get(field)) for field in fieldnames})
    write_csv(path, fieldnames, rows)


def write_per_query_scores(
    path: Path,
    per_query_scores: Sequence[PerQueryScore],
    ks: Sequence[int],
) -> None:
    fieldnames = [
        "method",
        "method_label",
        "qid",
        "question",
        "is_evaluable",
        "n_qrels",
        "n_relevant",
        "retrieved_at_10",
        "judged_at_10",
    ]
    fieldnames += [f"recall_at_{k}" for k in ks]
    fieldnames += [f"ndcg_at_{k}" for k in ks]
    fieldnames += ["mrr_at_10"]

    rows: List[Dict[str, str]] = []
    for score in per_query_scores:
        row: Dict[str, Any] = {
            "method": score.method,
            "method_label": METHOD_LABELS.get(score.method, score.method),
            "qid": score.qid,
            "question": score.question,
            "is_evaluable": "yes" if score.is_evaluable else "no",
            "n_qrels": score.n_qrels,
            "n_relevant": score.n_relevant,
            "retrieved_at_10": score.retrieved_at_10,
            "judged_at_10": score.judged_at_10,
        }
        for k in ks:
            row[f"recall_at_{k}"] = score.recall.get(k)
        for k in ks:
            row[f"ndcg_at_{k}"] = score.ndcg.get(k)
        row["mrr_at_10"] = score.mrr_at_10
        rows.append({field: format_csv_value(row.get(field)) for field in fieldnames})
    write_csv(path, fieldnames, rows)


def build_summary_report(
    method_scores: Sequence[Dict[str, Any]],
    per_query_scores: Sequence[PerQueryScore],
    queries_path: Path,
    results_path: Path,
    qrels_path: Path,
    ks: Sequence[int],
    relevance_threshold: int,
    warnings: Sequence[str],
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    methods = [row["method"] for row in method_scores]
    n_queries = len({row.qid for row in per_query_scores})
    n_evaluable = max((int(row.get("n_evaluable_queries", 0)) for row in method_scores), default=0)
    baseline_lines = []
    for method in CANONICAL_METHODS:
        status = "present" if method in methods else "missing"
        baseline_lines.append(f"- {method}: {METHOD_LABELS[method]} ({status})")

    lines = [
        "# Retrieval Evaluation Summary",
        "",
        f"- generated_at: `{now}`",
        f"- queries_path: `{queries_path}`",
        f"- retrieval_results_path: `{results_path}`",
        f"- qrels_path: `{qrels_path}`",
        f"- total_queries: `{n_queries}`",
        f"- evaluable_queries_per_method: `{n_evaluable}`",
        f"- relevance_threshold_for_recall_mrr: `>= {relevance_threshold}`",
        f"- k_values: `{', '.join(str(k) for k in ks)}`",
        "",
        "## Baseline Compatibility",
        "",
        *baseline_lines,
        "",
        "## Metrics By Method",
        "",
        markdown_metrics_table(method_scores, ks),
        "",
        "## Interpretation Notes",
        "",
        "- Recall@K and MRR@10 treat relevance scores >= threshold as relevant.",
        "- nDCG@K uses graded relevance with gain = 2^relevance - 1.",
        "- Unjudged retrieved items are treated as relevance 0.",
        "- Queries with no positive qrels are marked non-evaluable and excluded from macro averages.",
    ]
    if warnings:
        lines += ["", "## Warnings", ""]
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def markdown_metrics_table(method_scores: Sequence[Dict[str, Any]], ks: Sequence[int]) -> str:
    columns = ["method", "n_evaluable_queries"]
    columns += [f"recall_at_{k}" for k in ks]
    columns += [f"ndcg_at_{k}" for k in ks]
    columns += ["mrr_at_10"]
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, divider]
    for row in method_scores:
        values = []
        for column in columns:
            value = row.get(column)
            if column == "method":
                value = METHOD_LABELS.get(str(value), str(value))
            values.append(format_csv_value(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def sorted_methods(results_by_method: Dict[str, Any]) -> List[str]:
    methods = list(results_by_method.keys())
    order = {method: idx for idx, method in enumerate(CANONICAL_METHODS)}
    return sorted(methods, key=lambda method: (order.get(method, 999), method))


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def format_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def parse_ks(values: Sequence[str]) -> Tuple[int, ...]:
    ks = tuple(sorted({int(value) for value in values}))
    if not ks or any(k < 1 for k in ks):
        raise EvaluationError("all K values must be positive integers")
    return ks


def cmd_make_qrels_template(args: argparse.Namespace) -> None:
    queries_path = Path(args.queries).expanduser().resolve()
    results_path = Path(args.results).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    queries = load_queries(queries_path)
    results = load_retrieval_results(results_path)
    generate_qrels_template(queries, results, out_path, top_k=int(args.top_k))
    print(f"qrels_template={out_path}")
    print(f"queries={len(queries)}")
    print(f"methods={','.join(sorted_methods(results))}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    queries_path = Path(args.queries).expanduser().resolve()
    results_path = Path(args.results).expanduser().resolve()
    qrels_path = Path(args.qrels).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    ks = parse_ks(args.ks)
    relevance_threshold = int(args.relevance_threshold)
    if relevance_threshold not in {1, 2}:
        raise EvaluationError("--relevance-threshold must be 1 or 2")

    queries = load_queries(queries_path)
    qrels = load_qrels(qrels_path)
    results = load_retrieval_results(results_path)
    per_query, method_scores, warnings = evaluate_all(
        queries=queries,
        qrels=qrels,
        results_by_method=results,
        ks=ks,
        relevance_threshold=relevance_threshold,
    )
    write_outputs(
        out_dir=out_dir,
        per_query_scores=per_query,
        method_scores=method_scores,
        queries_path=queries_path,
        results_path=results_path,
        qrels_path=qrels_path,
        ks=ks,
        relevance_threshold=relevance_threshold,
        warnings=warnings,
    )
    print(f"metrics_by_method={out_dir / 'metrics_by_method.csv'}")
    print(f"per_query_scores={out_dir / 'per_query_scores.csv'}")
    print(f"summary_report={out_dir / 'summary_report.md'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate EOM literature retrieval outputs against graded qrels."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    template_parser = subparsers.add_parser(
        "make-qrels-template",
        help="Create pooled qrels CSV template from retrieval results.",
    )
    template_parser.add_argument("--queries", required=True, help="Path to queries JSONL.")
    template_parser.add_argument("--results", required=True, help="Path to retrieval_results JSON/JSONL.")
    template_parser.add_argument("--out", required=True, help="Output qrels template CSV path.")
    template_parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Pool top K documents per method and query. Default: 10.",
    )
    template_parser.set_defaults(func=cmd_make_qrels_template)

    eval_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate retrieval methods with completed qrels.",
    )
    eval_parser.add_argument("--queries", required=True, help="Path to queries JSONL.")
    eval_parser.add_argument("--results", required=True, help="Path to retrieval_results JSON/JSONL.")
    eval_parser.add_argument("--qrels", required=True, help="Completed qrels CSV path.")
    eval_parser.add_argument("--out-dir", required=True, help="Output directory.")
    eval_parser.add_argument(
        "--ks",
        nargs="+",
        default=[str(k) for k in DEFAULT_KS],
        help="K values for Recall@K and nDCG@K. Default: 1 3 5 10.",
    )
    eval_parser.add_argument(
        "--relevance-threshold",
        type=int,
        default=DEFAULT_RELEVANCE_THRESHOLD,
        help="Minimum relevance treated as relevant for Recall/MRR. Default: 1.",
    )
    eval_parser.set_defaults(func=cmd_evaluate)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except EvaluationError as exc:
        parser.exit(status=2, message=f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
