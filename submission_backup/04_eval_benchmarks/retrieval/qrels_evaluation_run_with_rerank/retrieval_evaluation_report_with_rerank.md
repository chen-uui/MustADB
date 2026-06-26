# Retrieval Evaluation Report With Hybrid + Rerank

## Inputs

- qrels: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\revision_qrels_eval_v1_mpnet768\qrels_relevance_only.csv`
- queries: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\expanded_query_set.jsonl`
- combined_ranked_results: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\qrels_evaluation_run_with_rerank\retrieval_results_by_method_with_rerank.json`
- collection: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`
- dense_embedding_model: `sentence-transformers/all-mpnet-base-v2`
- reranker_model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- reranker_available: `True`
- rerank_input_candidate_depth: `20`
- final_evaluated_top_k: `10`

## Qrels Summary

- qrels_total: `683`
- relevant_documents_relevance_gt_0: `292`
- highly_relevant_documents_relevance_eq_2: `144`
- evaluated_queries: `45`
- queries_without_relevant_docs: `0`
- handling: all queries contain at least one positive qrel and are included.
- unjudged_top10_method_query_count: `0`
- unjudged_top10_handling: all top-10 retrieved documents had qrels judgments.

## Ranked Results Export

| method | retrieved rows |
|---|---:|
| `bm25` | 274 |
| `dense` | 485 |
| `hybrid` | 414 |
| `hybrid_rerank` | 262 |

## Metrics

| method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | nDCG@1 | nDCG@3 | nDCG@5 | nDCG@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bm25 | 0.125682 | 0.311285 | 0.398769 | 0.456652 | 0.607407 | 0.535343 | 0.510874 | 0.490940 | 0.797249 |
| dense | 0.116944 | 0.291871 | 0.410642 | 0.647050 | 0.518519 | 0.508249 | 0.512319 | 0.598760 | 0.740741 |
| hybrid | 0.093637 | 0.279135 | 0.459080 | 0.663082 | 0.451852 | 0.483421 | 0.539196 | 0.594183 | 0.717989 |
| hybrid_rerank | 0.123741 | 0.279168 | 0.420242 | 0.509897 | 0.614815 | 0.529732 | 0.551437 | 0.552932 | 0.783333 |

## Paper-Ready Results Text

Using the manually annotated qrels, all 45 benchmark queries had at least one positive relevance judgment. Hybrid + rerank was evaluated by reranking the top 20 hybrid candidates and retaining the top 10 results. In this four-method comparison, hybrid achieved the highest Recall@10 (0.663082), while dense achieved the highest nDCG@10 (0.598760). The reranked hybrid run should therefore be interpreted as an additional reranking baseline under the same judged pool rather than a replacement for the original hybrid results.
