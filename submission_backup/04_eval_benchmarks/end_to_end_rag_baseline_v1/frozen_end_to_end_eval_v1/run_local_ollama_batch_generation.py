#!/usr/bin/env python3
"""Run local Ollama batch answer generation for end-to-end RAG baselines.

This runner is intentionally local-only. It refuses external API fallback, checks
that the requested Ollama model is available before writing results, validates
prompt metadata, and supports resume from an existing JSONL output.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(r"D:/workspace/123/submission_backup/04_eval_benchmarks/end_to_end_rag_baseline_v1")
DEFAULT_INPUT = ROOT / "all_pipeline_prompts.jsonl"
DEFAULT_RUNTIME_CONFIG = ROOT / "end_to_end_runtime_config.freeze.json"
DEFAULT_OUT_DIR = ROOT / "generated_answers_run"
DEFAULT_MODEL = "llama3.1:8b-instruct-q4_K_M"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_MAX_TOKENS = 512
REQUIRED_PIPELINES = {
    "llm_only",
    "bm25_rag",
    "dense_rag",
    "hybrid_rag",
    "hybrid_rerank_rag",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSONL file: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"JSONL row {line_no} must be an object: {path}")
            rows.append(item)
    if not rows:
        raise ValueError(f"No prompts found: {path}")
    return rows


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach local Ollama at {url}: {exc.reason}") from exc
    return json.loads(body)


def get_json(url: str, timeout: int) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach local Ollama at {url}: {exc.reason}") from exc
    return json.loads(body)


def normalize_base_url(value: str) -> str:
    base = str(value or "").strip().rstrip("/")
    if not base:
        raise ValueError("Ollama base URL is empty")
    if not (base.startswith("http://localhost") or base.startswith("http://127.0.0.1")):
        raise ValueError(f"Refusing non-local Ollama URL: {base}")
    return base


def validate_runtime_config(config: dict[str, Any], model: str) -> str:
    generation = config.get("generation") or {}
    retrieval = config.get("retrieval") or {}
    constraints = config.get("constraints") or {}
    if generation.get("backend") != "local/Ollama":
        raise ValueError(f"Unsupported backend: {generation.get('backend')}")
    if generation.get("generation_model") != model:
        raise ValueError(
            "Runtime config model mismatch: "
            f"{generation.get('generation_model')!r} != {model!r}"
        )
    if generation.get("external_api_allowed") is not False:
        raise ValueError("Runtime config must disable external API use")
    if constraints.get("do_not_use_external_api") is not True:
        raise ValueError("Runtime config does not explicitly forbid external API use")
    if constraints.get("do_not_fallback_to_generic_collection") is not True:
        raise ValueError("Runtime config does not forbid generic collection fallback")
    collection = retrieval.get("weaviate_collection")
    if collection == "PDFDocument" or not str(collection or "").endswith("_mpnet768"):
        raise ValueError(f"Refusing generic/non-mpnet collection: {collection!r}")
    if retrieval.get("dense_embedding_model") != "sentence-transformers/all-mpnet-base-v2":
        raise ValueError(f"Unexpected dense model: {retrieval.get('dense_embedding_model')}")
    if retrieval.get("reranker_model") != "cross-encoder/ms-marco-MiniLM-L-6-v2":
        raise ValueError(f"Unexpected reranker: {retrieval.get('reranker_model')}")
    if int(retrieval.get("rerank_input_candidate_depth", -1)) != 20:
        raise ValueError("Runtime config rerank input candidate depth must be 20")
    if int(retrieval.get("final_evaluated_top_k", -1)) != 10:
        raise ValueError("Runtime config final evaluated top-k must be 10")
    return normalize_base_url(generation.get("ollama_base_url") or "http://localhost:11434")


def validate_prompts(prompts: list[dict[str, Any]], model: str) -> None:
    sample_ids: set[str] = set()
    pipelines = Counter()
    for idx, prompt in enumerate(prompts, start=1):
        sample_id = str(prompt.get("sample_id") or "").strip()
        if not sample_id:
            raise ValueError(f"Prompt row {idx} has empty sample_id")
        if sample_id in sample_ids:
            raise ValueError(f"Duplicate sample_id: {sample_id}")
        sample_ids.add(sample_id)
        if prompt.get("generation_model") != model:
            raise ValueError(
                f"Prompt {sample_id} generation_model mismatch: "
                f"{prompt.get('generation_model')!r} != {model!r}"
            )
        if prompt.get("generation_backend") != "local/Ollama":
            raise ValueError(f"Prompt {sample_id} backend is not local/Ollama")
        collection = prompt.get("weaviate_collection")
        if collection == "PDFDocument" or not str(collection or "").endswith("_mpnet768"):
            raise ValueError(f"Prompt {sample_id} uses invalid collection: {collection!r}")
        pipeline = str(prompt.get("pipeline") or "").strip()
        if pipeline not in REQUIRED_PIPELINES:
            raise ValueError(f"Prompt {sample_id} has unexpected pipeline: {pipeline!r}")
        if not str(prompt.get("prompt") or "").strip():
            raise ValueError(f"Prompt {sample_id} has empty prompt")
        pipelines[pipeline] += 1
    missing = sorted(REQUIRED_PIPELINES - set(pipelines))
    if missing:
        raise ValueError(f"Missing pipelines in prompt file: {missing}")


def available_ollama_models(base_url: str, timeout: int) -> set[str]:
    data = get_json(f"{base_url}/api/tags", timeout=timeout)
    models = data.get("models") or []
    names: set[str] = set()
    for item in models:
        if not isinstance(item, dict):
            continue
        for key in ("name", "model"):
            value = item.get(key)
            if value:
                names.add(str(value))
    return names


def call_ollama_generate(
    base_url: str,
    model: str,
    prompt: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout: int,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
        },
    }
    data = post_json(f"{base_url}/api/generate", payload=payload, timeout=timeout)
    if "response" not in data:
        raise RuntimeError(f"Ollama response missing 'response' field: {data}")
    return str(data.get("response") or "").strip()


def load_completed(jsonl_path: Path) -> dict[str, dict[str, Any]]:
    completed: dict[str, dict[str, Any]] = {}
    if not jsonl_path.exists():
        return completed
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            sample_id = str(item.get("sample_id") or "").strip()
            if sample_id and not item.get("error") and str(item.get("generated_answer") or "").strip():
                completed[sample_id] = item
    return completed


def make_output_row(
    prompt_item: dict[str, Any],
    answer: str,
    model: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    latency: float,
    error: str,
) -> dict[str, Any]:
    evidence = prompt_item.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = []
    return {
        "sample_id": prompt_item.get("sample_id"),
        "question_id": prompt_item.get("qid"),
        "pipeline": prompt_item.get("pipeline"),
        "query": prompt_item.get("question"),
        "evidence_count": len(evidence),
        "evidence_doc_ids": ";".join(str(item.get("doc_id") or "") for item in evidence if isinstance(item, dict)),
        "prompt": prompt_item.get("prompt"),
        "generated_answer": answer,
        "generation_model": model,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "latency_seconds": round(latency, 3),
        "error": error,
    }


def write_csv_from_jsonl(jsonl_path: Path, csv_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
    fieldnames = [
        "sample_id",
        "question_id",
        "pipeline",
        "query",
        "evidence_count",
        "evidence_doc_ids",
        "prompt",
        "generated_answer",
        "generation_model",
        "temperature",
        "top_p",
        "max_tokens",
        "latency_seconds",
        "error",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_report(
    report_path: Path,
    prompts: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    model: str,
    base_url: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    skipped: int,
    started_at: float,
    finished_at: float,
) -> None:
    total = len(prompts)
    completed = sum(1 for row in rows if row.get("generated_answer") and not row.get("error"))
    failed = sum(1 for row in rows if row.get("error"))
    by_pipeline_total = Counter(str(row.get("pipeline") or "") for row in prompts)
    by_pipeline_completed = Counter(
        str(row.get("pipeline") or "") for row in rows if row.get("generated_answer") and not row.get("error")
    )
    by_pipeline_failed = Counter(str(row.get("pipeline") or "") for row in rows if row.get("error"))
    identical_settings = all(
        row.get("generation_model") == model
        and float(row.get("temperature")) == temperature
        and float(row.get("top_p")) == top_p
        and int(row.get("max_tokens")) == max_tokens
        for row in rows
    )
    lines = [
        "# Generation Run Report",
        "",
        f"- total prompts: `{total}`",
        f"- completed answers: `{completed}`",
        f"- failed answers: `{failed}`",
        f"- skipped by resume: `{skipped}`",
        f"- generation model: `{model}`",
        f"- backend: `local/Ollama`",
        f"- ollama_base_url: `{base_url}`",
        f"- temperature: `{temperature}`",
        f"- top_p: `{top_p}`",
        f"- max_tokens: `{max_tokens}`",
        f"- identical generator settings across all outputs: `{str(identical_settings).lower()}`",
        "- external API used: `no`",
        f"- elapsed seconds: `{round(finished_at - started_at, 3)}`",
        "",
        "## Pipeline Counts",
        "",
        "| pipeline | prompts | completed | failed |",
        "|---|---:|---:|---:|",
    ]
    for pipeline in sorted(REQUIRED_PIPELINES):
        lines.append(
            f"| `{pipeline}` | {by_pipeline_total[pipeline]} | "
            f"{by_pipeline_completed[pipeline]} | {by_pipeline_failed[pipeline]} |"
        )
    if failed:
        lines.extend(["", "## Failures", ""])
        for row in rows:
            if row.get("error"):
                lines.append(f"- `{row.get('sample_id')}`: {row.get('error')}")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--runtime-config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--generation-model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--stop-on-error", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    runtime_path = Path(args.runtime_config)
    out_dir = Path(args.out_dir)
    model = str(args.generation_model).strip()
    if model != DEFAULT_MODEL:
        raise ValueError(f"Generation model must be {DEFAULT_MODEL!r}; got {model!r}")
    if args.temperature != DEFAULT_TEMPERATURE:
        raise ValueError("Temperature is pinned to 0 for this run")
    if args.top_p != DEFAULT_TOP_P:
        raise ValueError("top_p is pinned to 1 for this run")
    if args.max_tokens != DEFAULT_MAX_TOKENS:
        raise ValueError("max_tokens is pinned to 512 for this run")

    runtime_config = read_json(runtime_path)
    base_url = validate_runtime_config(runtime_config, model)
    prompts = read_jsonl(input_path)
    validate_prompts(prompts, model)

    models = available_ollama_models(base_url, timeout=args.timeout_seconds)
    if model not in models:
        listed = ", ".join(sorted(models)) or "none"
        raise RuntimeError(
            f"Ollama model {model!r} is not available at {base_url}. "
            f"Available models: {listed}. Run: ollama pull {model}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "generated_answers_by_pipeline.jsonl"
    csv_path = out_dir / "generated_answers_by_pipeline.csv"
    report_path = out_dir / "generation_run_report.md"

    completed = load_completed(jsonl_path)
    skipped = 0
    started_at = time.time()
    with jsonl_path.open("a", encoding="utf-8") as handle:
        for prompt_item in prompts:
            sample_id = str(prompt_item.get("sample_id") or "").strip()
            if sample_id in completed:
                skipped += 1
                continue
            started = time.time()
            answer = ""
            error = ""
            try:
                answer = call_ollama_generate(
                    base_url=base_url,
                    model=model,
                    prompt=str(prompt_item.get("prompt") or ""),
                    temperature=args.temperature,
                    top_p=args.top_p,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout_seconds,
                )
                if not answer:
                    raise RuntimeError("Ollama returned an empty answer")
            except Exception as exc:  # keep partial run auditable
                error = str(exc)
                if args.stop_on_error:
                    raise
            latency = time.time() - started
            row = make_output_row(
                prompt_item=prompt_item,
                answer=answer,
                model=model,
                temperature=args.temperature,
                top_p=args.top_p,
                max_tokens=args.max_tokens,
                latency=latency,
                error=error,
            )
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            if not error:
                completed[sample_id] = row
    finished_at = time.time()

    rows = write_csv_from_jsonl(jsonl_path, csv_path)
    write_report(
        report_path=report_path,
        prompts=prompts,
        rows=rows,
        model=model,
        base_url=base_url,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        skipped=skipped,
        started_at=started_at,
        finished_at=finished_at,
    )


if __name__ == "__main__":
    main()
