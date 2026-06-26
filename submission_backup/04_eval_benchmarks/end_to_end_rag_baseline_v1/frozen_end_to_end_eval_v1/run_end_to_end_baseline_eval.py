#!/usr/bin/env python3
"""Prepare and summarize end-to-end LLM-only vs RAG baseline evaluation.

This script does not call any external API and does not generate answers by
default. It prepares batch prompt inputs from existing QA questions, ranked
retrieval outputs, and indexed metadata/snippets. A later annotation CSV can be
summarized with the same script.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(r"D:/workspace/123/submission_backup")
DEFAULT_OUT_DIR = ROOT / "04_eval_benchmarks" / "end_to_end_rag_baseline_v1"
DEFAULT_QA_SAMPLES = (
    ROOT
    / "08_manual_annotations"
    / "annotation_pack_paper_support_80samples_20260402_doclevel_fix"
    / "qa_annotation_samples_80_merged.csv"
)
DEFAULT_QRELS_METADATA = (
    ROOT
    / "04_eval_benchmarks"
    / "retrieval"
    / "qrels_annotation"
    / "qrels_annotation_template.csv"
)
DEFAULT_RESULTS_DIR = (
    ROOT
    / "04_eval_benchmarks"
    / "retrieval"
    / "qrels_evaluation_run_with_rerank"
)
DEFAULT_CONFIG_PATH = (
    ROOT
    / "04_eval_benchmarks"
    / "config_audit_revision_v1"
    / "revision_experiment_config.freeze.json"
)

PIPELINES = {
    "llm_only": {
        "method": None,
        "filename": "llm_only_prompts.jsonl",
        "description": "Question only; no retrieved evidence.",
    },
    "bm25_rag": {
        "method": "bm25",
        "filename": "bm25_rag_prompts.jsonl",
        "description": "BM25 top-k evidence plus the same local generation model.",
    },
    "dense_rag": {
        "method": "dense",
        "filename": "dense_rag_prompts.jsonl",
        "description": "Dense retrieval top-k evidence plus the same local generation model.",
    },
    "hybrid_rag": {
        "method": "hybrid",
        "filename": "hybrid_rag_prompts.jsonl",
        "description": "Hybrid retrieval top-k evidence plus the same local generation model.",
    },
    "hybrid_rerank_rag": {
        "method": "hybrid_rerank",
        "filename": "hybrid_rerank_rag_prompts.jsonl",
        "description": "Hybrid candidates reranked by cross-encoder, then top-k evidence.",
    },
}

RESULT_FILES = {
    "bm25": "bm25_results.jsonl",
    "dense": "dense_results.jsonl",
    "hybrid": "hybrid_results.jsonl",
    "hybrid_rerank": "hybrid_rerank_results.jsonl",
}

REQUIRED_PIPELINES = (
    "llm_only",
    "bm25_rag",
    "dense_rag",
    "hybrid_rag",
    "hybrid_rerank_rag",
)

SUPPORT_LABELS = {
    "fully supported",
    "partially supported",
    "unsupported",
    "evidence mismatch",
}
PARTIAL_SUBTYPES = {
    "missing detail",
    "incomplete entity boundary",
    "weak evidence match",
    "over-generalization",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_freeze_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Freeze config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Freeze config must be a JSON object: {path}")
    return config


def require_config_value(config: dict[str, Any], dotted_key: str) -> Any:
    value: Any = config
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"Missing required freeze config key: {dotted_key}")
        value = value[part]
    if value in (None, "", []):
        raise ValueError(f"Empty required freeze config key: {dotted_key}")
    return value


def load_rerank_metadata(results_dir: Path) -> dict[str, Any]:
    path = results_dir / "hybrid_rerank_export_metadata.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing rerank metadata: {path}")
    with path.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    if not isinstance(metadata, dict):
        raise ValueError(f"Rerank metadata must be a JSON object: {path}")
    return metadata


def validate_pinned_runtime(args: argparse.Namespace) -> dict[str, Any]:
    config_path = Path(args.config)
    config = load_freeze_config(config_path)

    generation_model = str(args.generation_model or "").strip()
    if not generation_model:
        raise ValueError("--generation-model is required; refusing to read LLM_MODEL from .env")

    expected_generation_model = str(
        require_config_value(config, "generation.intended_model_for_end_to_end_baseline")
    )
    if generation_model != expected_generation_model:
        raise ValueError(
            "--generation-model does not match freeze config: "
            f"{generation_model!r} != {expected_generation_model!r}"
        )

    backend = str(require_config_value(config, "generation.backend"))
    if backend != "local/Ollama":
        raise ValueError(f"Unsupported generation backend for this experiment: {backend}")
    if require_config_value(config, "generation.external_api_allowed") is not False:
        raise ValueError("Freeze config must set generation.external_api_allowed=false")

    collection = str(require_config_value(config, "retrieval.weaviate_collection"))
    if collection == "PDFDocument" or not collection.endswith("_mpnet768"):
        raise ValueError(
            "Refusing generic or non-mpnet collection in freeze config: "
            f"{collection!r}"
        )

    dense_model = str(require_config_value(config, "retrieval.dense_embedding_model"))
    if dense_model != "sentence-transformers/all-mpnet-base-v2":
        raise ValueError(f"Unexpected dense embedding model: {dense_model}")
    dense_dim = int(require_config_value(config, "retrieval.dense_vector_dimension"))
    if dense_dim != 768:
        raise ValueError(f"Unexpected dense vector dimension: {dense_dim}")

    reranker = str(require_config_value(config, "reranking.reranker_model"))
    if reranker != "cross-encoder/ms-marco-MiniLM-L-6-v2":
        raise ValueError(f"Unexpected reranker model: {reranker}")
    rerank_depth = int(require_config_value(config, "reranking.rerank_input_candidate_depth"))
    final_top_k = int(require_config_value(config, "reranking.final_evaluated_top_k"))
    if rerank_depth != 20 or final_top_k != 10:
        raise ValueError(
            "Unexpected rerank depth/final top-k: "
            f"rerank_depth={rerank_depth}, final_top_k={final_top_k}"
        )

    rerank_metadata = load_rerank_metadata(Path(args.results_dir))
    checks = {
        "collection_name": collection,
        "embedding_model": dense_model,
        "reranker_model": reranker,
        "rerank_input_candidate_depth": rerank_depth,
        "final_top_k": final_top_k,
    }
    for key, expected in checks.items():
        observed = rerank_metadata.get(key)
        if observed != expected:
            raise ValueError(
                f"Ranked rerank metadata mismatch for {key}: observed={observed!r}, expected={expected!r}"
            )

    return {
        "config_path": str(config_path),
        "freeze_config": config,
        "generation_model": generation_model,
        "generation_backend": backend,
        "dense_embedding_model": dense_model,
        "dense_vector_dimension": dense_dim,
        "weaviate_collection": collection,
        "reranker_model": reranker,
        "rerank_input_candidate_depth": rerank_depth,
        "final_evaluated_top_k": final_top_k,
        "temperature": require_config_value(config, "generation.temperature"),
        "max_tokens": require_config_value(config, "generation.max_tokens"),
        "external_api_allowed": False,
        "rerank_metadata": rerank_metadata,
    }


def load_questions(qa_samples_path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows = read_csv(qa_samples_path)
    if not rows:
        raise ValueError(f"No QA sample rows found: {qa_samples_path}")

    questions: list[dict[str, str]] = []
    seen: set[str] = set()
    mode_counts = Counter()
    label_nonempty = Counter()
    for row in rows:
        qid = (row.get("qid") or "").strip()
        query = (row.get("query") or "").strip()
        mode_counts[(row.get("mode") or "").strip()] += 1
        for col in ("answer_correct", "evidence_support", "unsupported_span_note", "annotation_note"):
            if (row.get(col) or "").strip():
                label_nonempty[col] += 1
        if qid and qid not in seen:
            questions.append(
                {
                    "qid": qid,
                    "question": query,
                    "source_sample_id": (row.get("sample_id") or "").strip(),
                }
            )
            seen.add(qid)

    metadata = {
        "source_rows": len(rows),
        "unique_questions": len(questions),
        "mode_counts": dict(mode_counts),
        "manual_label_nonempty_counts": dict(label_nonempty),
        "fieldnames": list(rows[0].keys()),
    }
    return questions, metadata


def load_metadata(metadata_path: Path) -> tuple[dict[tuple[str, str], dict[str, str]], dict[str, dict[str, str]]]:
    rows = read_csv(metadata_path)
    by_qid_doc: dict[tuple[str, str], dict[str, str]] = {}
    by_doc: dict[str, dict[str, str]] = {}
    for row in rows:
        qid = (row.get("qid") or "").strip()
        doc_id = (row.get("doc_id") or "").strip()
        if not doc_id:
            continue
        by_qid_doc[(qid, doc_id)] = row
        by_doc.setdefault(doc_id, row)
    return by_qid_doc, by_doc


def load_ranked_results(results_dir: Path) -> dict[str, dict[str, dict[str, Any]]]:
    output: dict[str, dict[str, dict[str, Any]]] = {}
    for method, filename in RESULT_FILES.items():
        path = results_dir / filename
        if not path.exists():
            output[method] = {}
            continue
        by_qid: dict[str, dict[str, Any]] = {}
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = json.loads(line)
                qid = str(item.get("qid") or "").strip()
                if qid:
                    by_qid[qid] = item
        output[method] = by_qid
    return output


def compact_text(text: str, max_chars: int) -> str:
    value = " ".join(str(text or "").split())
    if max_chars <= 0 or len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."


def build_evidence(
    qid: str,
    ranked_item: dict[str, Any] | None,
    metadata_by_qid_doc: dict[tuple[str, str], dict[str, str]],
    metadata_by_doc: dict[str, dict[str, str]],
    top_k: int,
    snippet_chars: int,
) -> list[dict[str, Any]]:
    if not ranked_item:
        return []
    evidence: list[dict[str, Any]] = []
    for result in (ranked_item.get("results") or [])[:top_k]:
        doc_id = str(result.get("doc_id") or "").strip()
        meta = metadata_by_qid_doc.get((qid, doc_id)) or metadata_by_doc.get(doc_id) or {}
        snippet = compact_text(meta.get("abstract_or_snippet", ""), snippet_chars)
        evidence.append(
            {
                "evidence_id": f"E{len(evidence) + 1}",
                "rank": int(result.get("rank") or len(evidence) + 1),
                "doc_id": doc_id,
                "score": result.get("score"),
                "document_title": meta.get("document_title") or result.get("title") or "NA",
                "doi": meta.get("doi") or "NA",
                "year": meta.get("year") or "NA",
                "snippet": snippet,
                "metadata_source": "qrels_annotation_template" if meta else "missing",
            }
        )
    return evidence


def render_prompt(question: str, pipeline: str, evidence: list[dict[str, Any]]) -> str:
    common = (
        "You are a scientific assistant answering a literature-mining question about "
        "extraterrestrial organic matter, meteorites, analytical methods, isotope "
        "evidence, contamination controls, or meteorite taxonomy.\n\n"
        "Answer concisely and distinguish direct evidence from uncertainty."
    )
    if pipeline == "llm_only":
        return (
            f"{common}\n\n"
            "No retrieved evidence is provided in this condition. Answer using only the "
            "model's internal knowledge. Do not invent paper-specific citations, document "
            "IDs, or unsupported details. If the question requires literature evidence "
            "that you cannot verify, state the uncertainty explicitly.\n\n"
            f"Question:\n{question}\n\n"
            "Answer:"
        )

    evidence_lines = []
    for item in evidence:
        evidence_lines.append(
            "[{evidence_id}] rank={rank}; doc_id={doc_id}; score={score}; title={title}; "
            "doi={doi}; year={year}\n{snippet}".format(
                evidence_id=item["evidence_id"],
                rank=item["rank"],
                doc_id=item["doc_id"],
                score=item["score"],
                title=item["document_title"],
                doi=item["doi"],
                year=item["year"],
                snippet=item["snippet"],
            )
        )
    evidence_block = "\n\n".join(evidence_lines) if evidence_lines else "No evidence retrieved."
    return (
        f"{common}\n\n"
        "Use only the retrieved evidence below. Cite evidence IDs such as [E1] for "
        "claims that depend on the evidence. If the evidence is insufficient, say so "
        "instead of filling gaps from outside knowledge.\n\n"
        f"Question:\n{question}\n\n"
        f"Retrieved evidence:\n{evidence_block}\n\n"
        "Answer:"
    )


def write_runtime_config_files(
    out_dir: Path,
    runtime: dict[str, Any],
    prompt_counts: dict[str, int],
    evidence_top_k: int,
    snippet_chars: int,
) -> None:
    local_generation_config = {
        "backend": runtime["generation_backend"],
        "ollama_base_url": "http://localhost:11434",
        "generation_model": runtime["generation_model"],
        "temperature": runtime["temperature"],
        "max_tokens": runtime["max_tokens"],
        "external_api_allowed": False,
        "fail_fast": True,
        "env_llm_model_fallback_allowed": False,
        "pipelines": list(REQUIRED_PIPELINES),
    }
    with (out_dir / "local_generation_config.json").open("w", encoding="utf-8") as handle:
        json.dump(local_generation_config, handle, ensure_ascii=False, indent=2)

    runtime_freeze = {
        "version": "end_to_end_runtime_config_v1",
        "source_freeze_config": runtime["config_path"],
        "generation": local_generation_config,
        "retrieval": {
            "dense_embedding_model": runtime["dense_embedding_model"],
            "dense_vector_dimension": runtime["dense_vector_dimension"],
            "weaviate_collection": runtime["weaviate_collection"],
            "reranker_model": runtime["reranker_model"],
            "rerank_input_candidate_depth": runtime["rerank_input_candidate_depth"],
            "final_evaluated_top_k": runtime["final_evaluated_top_k"],
            "prompt_evidence_top_k": evidence_top_k,
            "prompt_snippet_chars": snippet_chars,
        },
        "prompt_counts": prompt_counts,
        "constraints": {
            "do_not_use_external_api": True,
            "do_not_read_env_llm_model": True,
            "do_not_fallback_to_generic_collection": True,
            "do_not_rebuild_index": True,
            "do_not_modify_qrels": True,
        },
    }
    with (out_dir / "end_to_end_runtime_config.freeze.json").open("w", encoding="utf-8") as handle:
        json.dump(runtime_freeze, handle, ensure_ascii=False, indent=2)

    command_lines = [
        "C:\\Users\\19404\\AppData\\Local\\Programs\\Python\\Python311\\python.exe "
        "D:\\workspace\\123\\submission_backup\\04_eval_benchmarks\\end_to_end_rag_baseline_v1\\run_end_to_end_baseline_eval.py "
        "prepare-prompts ^",
        "  --config D:\\workspace\\123\\submission_backup\\04_eval_benchmarks\\config_audit_revision_v1\\revision_experiment_config.freeze.json ^",
        f"  --generation-model {runtime['generation_model']} ^",
        "  --out-dir D:\\workspace\\123\\submission_backup\\04_eval_benchmarks\\end_to_end_rag_baseline_v1",
    ]
    generation_command_lines = []
    for pipeline, filename in (
        ("llm_only", "llm_only_prompts.jsonl"),
        ("bm25_rag", "bm25_rag_prompts.jsonl"),
        ("dense_rag", "dense_rag_prompts.jsonl"),
        ("hybrid_rag", "hybrid_rag_prompts.jsonl"),
        ("hybrid_rerank_rag", "hybrid_rerank_rag_prompts.jsonl"),
    ):
        generation_command_lines.extend(
            [
                "C:\\Users\\19404\\AppData\\Local\\Programs\\Python\\Python311\\python.exe "
                "D:\\workspace\\123\\submission_backup\\04_eval_benchmarks\\end_to_end_rag_baseline_v1\\run_local_ollama_batch_generation.py ^",
                "  --runtime-config D:\\workspace\\123\\submission_backup\\04_eval_benchmarks\\end_to_end_rag_baseline_v1\\end_to_end_runtime_config.freeze.json ^",
                f"  --pipeline {pipeline} ^",
                f"  --input D:\\workspace\\123\\submission_backup\\04_eval_benchmarks\\end_to_end_rag_baseline_v1\\{filename} ^",
                f"  --output D:\\workspace\\123\\submission_backup\\04_eval_benchmarks\\end_to_end_rag_baseline_v1\\generated_answers_{pipeline}.jsonl",
                "",
            ]
        )

    report = [
        "# Generation Model Freeze Report",
        "",
        "## Scope",
        "",
        "This report pins the configuration for the future end-to-end LLM-only vs RAG baseline generation step. No LLM generation was run by this script invocation.",
        "",
        "## Frozen Generation Configuration",
        "",
        f"- backend: `{runtime['generation_backend']}`",
        f"- generation_model: `{runtime['generation_model']}`",
        f"- temperature: `{runtime['temperature']}`",
        f"- max_tokens: `{runtime['max_tokens']}`",
        "- external_api_allowed: `false`",
        "- `.env` LLM fallback allowed: `false`",
        "",
        "All five pipelines use the same generation model:",
        "",
        "- `llm_only`",
        "- `bm25_rag`",
        "- `dense_rag`",
        "- `hybrid_rag`",
        "- `hybrid_rerank_rag`",
        "",
        "Using the same local generation model isolates the contribution of retrieval evidence: any observed answer-level difference is attributable to whether evidence is provided and which retrieval method supplies it, not to a different LLM backend.",
        "",
        "## Frozen Retrieval/Index Configuration",
        "",
        f"- dense_embedding_model: `{runtime['dense_embedding_model']}`",
        f"- dense_vector_dimension: `{runtime['dense_vector_dimension']}`",
        f"- weaviate_collection: `{runtime['weaviate_collection']}`",
        f"- reranker_model: `{runtime['reranker_model']}`",
        f"- rerank_input_candidate_depth: `{runtime['rerank_input_candidate_depth']}`",
        f"- final_evaluated_top_k: `{runtime['final_evaluated_top_k']}`",
        f"- prompt_evidence_top_k: `{evidence_top_k}`",
        "",
        "The script fails fast if the freeze config is missing, if the generation model does not match the freeze file, if the collection is generic, or if rerank metadata does not match the frozen mpnet768 configuration.",
        "",
        "## Model-Agnostic System Statement",
        "",
        "The system remains model-agnostic: a different generation backend can be used in a separately frozen experiment. This experiment intentionally fixes the local Ollama model so that the comparison tests retrieval/evidence grounding rather than LLM model strength.",
        "",
        "## Command To Regenerate Pinned Prompt Inputs",
        "",
        "```powershell",
        *command_lines,
        "```",
        "",
        "## Future Answer Generation Command",
        "",
        "No answer generation was executed during pinning. The project does not currently include a standalone `run_local_ollama_batch_generation.py`; the commands below define the required formal entry point for the next step. That runner must read `end_to_end_runtime_config.freeze.json`, use local Ollama only, refuse external API fallback, and fail if `llama3.1:8b-instruct-q4_K_M` is unavailable.",
        "",
        "```powershell",
        *generation_command_lines,
        "```",
    ]
    (out_dir / "generation_model_freeze_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )


def prepare_prompts(args: argparse.Namespace) -> None:
    runtime = validate_pinned_runtime(args)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    questions, qa_metadata = load_questions(Path(args.qa_samples))
    metadata_by_qid_doc, metadata_by_doc = load_metadata(Path(args.metadata_csv))
    ranked_results = load_ranked_results(Path(args.results_dir))

    all_prompt_rows: list[dict[str, Any]] = []
    generation_rows: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {
        "qa_samples": str(Path(args.qa_samples)),
        "metadata_csv": str(Path(args.metadata_csv)),
        "results_dir": str(Path(args.results_dir)),
        "out_dir": str(out_dir),
        "config": runtime["config_path"],
        "generation_backend": runtime["generation_backend"],
        "generation_model": runtime["generation_model"],
        "dense_embedding_model": runtime["dense_embedding_model"],
        "dense_vector_dimension": runtime["dense_vector_dimension"],
        "weaviate_collection": runtime["weaviate_collection"],
        "reranker_model": runtime["reranker_model"],
        "rerank_input_candidate_depth": runtime["rerank_input_candidate_depth"],
        "final_evaluated_top_k": runtime["final_evaluated_top_k"],
        "external_api_allowed": False,
        "env_llm_model_fallback_allowed": False,
        "generic_collection_fallback_allowed": False,
        "evidence_top_k": args.evidence_top_k,
        "snippet_chars": args.snippet_chars,
        "qa_sample_structure": qa_metadata,
        "pipeline_counts": {},
        "missing_ranked_results": defaultdict(list),
        "missing_metadata_snippets": defaultdict(int),
    }

    for pipeline, config in PIPELINES.items():
        rows: list[dict[str, Any]] = []
        method = config["method"]
        for question in questions:
            qid = question["qid"]
            ranked_item = ranked_results.get(method, {}).get(qid) if method else None
            if method and ranked_item is None:
                diagnostics["missing_ranked_results"][pipeline].append(qid)
            evidence = build_evidence(
                qid=qid,
                ranked_item=ranked_item,
                metadata_by_qid_doc=metadata_by_qid_doc,
                metadata_by_doc=metadata_by_doc,
                top_k=args.evidence_top_k,
                snippet_chars=args.snippet_chars,
            )
            diagnostics["missing_metadata_snippets"][pipeline] += sum(
                1 for item in evidence if item.get("metadata_source") == "missing"
            )
            sample_id = f"{qid}_{pipeline}"
            prompt = render_prompt(question["question"], pipeline, evidence)
            row = {
                "sample_id": sample_id,
                "qid": qid,
                "question": question["question"],
                "pipeline": pipeline,
                "retrieval_method": method or "none",
                "evidence_top_k": args.evidence_top_k if method else 0,
                "generation_backend": runtime["generation_backend"],
                "generation_model": runtime["generation_model"],
                "dense_embedding_model": runtime["dense_embedding_model"],
                "weaviate_collection": runtime["weaviate_collection"],
                "reranker_model": runtime["reranker_model"] if method == "hybrid_rerank" else None,
                "rerank_input_candidate_depth": runtime["rerank_input_candidate_depth"] if method == "hybrid_rerank" else None,
                "final_evaluated_top_k": runtime["final_evaluated_top_k"] if method == "hybrid_rerank" else None,
                "prompt": prompt,
                "evidence": evidence,
                "source_question_sample_id": question["source_sample_id"],
                "source_question_file": str(Path(args.qa_samples)),
                "notes": config["description"],
            }
            rows.append(row)
            all_prompt_rows.append(row)
            generation_rows.append(
                {
                    "sample_id": sample_id,
                    "pipeline": pipeline,
                    "qid": qid,
                    "question": question["question"],
                    "generated_answer": "",
                    "gold_answer": "",
                    "support_label": "",
                    "partial_support_subtype": "",
                    "evidence_mismatch": "",
                    "answer_correct": "",
                    "evaluator_notes": "",
                }
            )
        diagnostics["pipeline_counts"][pipeline] = len(rows)
        prompt_path = out_dir / config["filename"]
        with prompt_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    with (out_dir / "all_pipeline_prompts.jsonl").open("w", encoding="utf-8") as handle:
        for row in all_prompt_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_csv(
        out_dir / "answer_level_evaluation_template.csv",
        generation_rows,
        [
            "sample_id",
            "pipeline",
            "qid",
            "question",
            "generated_answer",
            "gold_answer",
            "support_label",
            "partial_support_subtype",
            "evidence_mismatch",
            "answer_correct",
            "evaluator_notes",
        ],
    )

    diagnostics["missing_ranked_results"] = dict(diagnostics["missing_ranked_results"])
    diagnostics["missing_metadata_snippets"] = dict(diagnostics["missing_metadata_snippets"])
    with (out_dir / "prompt_preparation_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(diagnostics, handle, ensure_ascii=False, indent=2)
    write_runtime_config_files(
        out_dir=out_dir,
        runtime=runtime,
        prompt_counts=dict(diagnostics["pipeline_counts"]),
        evidence_top_k=args.evidence_top_k,
        snippet_chars=args.snippet_chars,
    )


def normalize_support_label(value: str) -> str:
    label = " ".join(str(value or "").strip().lower().replace("_", " ").split())
    aliases = {
        "supported": "fully supported",
        "full": "fully supported",
        "fully_supported": "fully supported",
        "partial": "partially supported",
        "partially_supported": "partially supported",
        "mismatch": "evidence mismatch",
        "evidence_mismatch": "evidence mismatch",
    }
    return aliases.get(label, label)


def normalize_bool(value: str) -> bool | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "y", "correct"}:
        return True
    if normalized in {"0", "false", "no", "n", "incorrect"}:
        return False
    return None


def summarize_annotations(args: argparse.Namespace) -> None:
    annotations = read_csv(Path(args.annotations_csv))
    if not annotations:
        raise ValueError(f"No annotation rows found: {args.annotations_csv}")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in annotations:
        pipeline = (row.get("pipeline") or "").strip()
        if pipeline:
            grouped[pipeline].append(row)

    rows: list[dict[str, Any]] = []
    for pipeline in sorted(grouped):
        items = grouped[pipeline]
        labels = Counter(normalize_support_label(row.get("support_label", "")) for row in items)
        valid_total = sum(labels[label] for label in SUPPORT_LABELS)
        correctness = [normalize_bool(row.get("answer_correct", "")) for row in items]
        correctness_values = [value for value in correctness if value is not None]
        row: dict[str, Any] = {
            "pipeline": pipeline,
            "total_rows": len(items),
            "labeled_rows": valid_total,
        }
        for label in (
            "fully supported",
            "partially supported",
            "unsupported",
            "evidence mismatch",
        ):
            count = labels[label]
            row[f"{label.replace(' ', '_')}_count"] = count
            row[f"{label.replace(' ', '_')}_pct"] = (count / valid_total) if valid_total else ""
        row["answer_correct_count"] = sum(1 for value in correctness_values if value)
        row["answer_accuracy"] = (
            row["answer_correct_count"] / len(correctness_values) if correctness_values else ""
        )
        rows.append(row)

    write_csv(
        Path(args.out_dir) / "end_to_end_metrics_by_pipeline.csv",
        rows,
        [
            "pipeline",
            "total_rows",
            "labeled_rows",
            "fully_supported_count",
            "fully_supported_pct",
            "partially_supported_count",
            "partially_supported_pct",
            "unsupported_count",
            "unsupported_pct",
            "evidence_mismatch_count",
            "evidence_mismatch_pct",
            "answer_correct_count",
            "answer_accuracy",
        ],
    )

    md_lines = [
        "# End-to-End Baseline Evaluation Summary",
        "",
        f"- annotations_csv: `{args.annotations_csv}`",
        f"- total_rows: `{len(annotations)}`",
        f"- pipelines: `{', '.join(sorted(grouped))}`",
        "",
        "| pipeline | labeled | fully supported | partially supported | unsupported | evidence mismatch | answer accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        accuracy = row["answer_accuracy"]
        accuracy_text = "" if accuracy == "" else f"{accuracy:.4f}"
        md_lines.append(
            "| {pipeline} | {labeled_rows} | {fully_supported_count} | "
            "{partially_supported_count} | {unsupported_count} | "
            "{evidence_mismatch_count} | {accuracy} |".format(
                pipeline=row["pipeline"],
                labeled_rows=row["labeled_rows"],
                fully_supported_count=row["fully_supported_count"],
                partially_supported_count=row["partially_supported_count"],
                unsupported_count=row["unsupported_count"],
                evidence_mismatch_count=row["evidence_mismatch_count"],
                accuracy=accuracy_text,
            )
        )
    (Path(args.out_dir) / "end_to_end_evaluation_summary.md").write_text(
        "\n".join(md_lines) + "\n", encoding="utf-8"
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-prompts")
    prepare.add_argument("--config", required=True)
    prepare.add_argument("--generation-model", required=True)
    prepare.add_argument("--qa-samples", default=str(DEFAULT_QA_SAMPLES))
    prepare.add_argument("--metadata-csv", default=str(DEFAULT_QRELS_METADATA))
    prepare.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    prepare.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    prepare.add_argument("--evidence-top-k", type=int, default=5)
    prepare.add_argument("--snippet-chars", type=int, default=1200)
    prepare.set_defaults(func=prepare_prompts)

    evaluate = subparsers.add_parser("summarize-annotations")
    evaluate.add_argument("--annotations-csv", required=True)
    evaluate.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    evaluate.set_defaults(func=summarize_annotations)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
