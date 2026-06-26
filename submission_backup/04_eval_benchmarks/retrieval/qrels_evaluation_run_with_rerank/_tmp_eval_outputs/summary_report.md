# Retrieval Evaluation Summary

- generated_at: `2026-06-24 10:25:20 UTC`
- queries_path: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\expanded_query_set.jsonl`
- retrieval_results_path: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\qrels_evaluation_run_with_rerank\retrieval_results_by_method_with_rerank.json`
- qrels_path: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\revision_qrels_eval_v1_mpnet768\qrels_relevance_only.csv`
- total_queries: `45`
- evaluable_queries_per_method: `45`
- relevance_threshold_for_recall_mrr: `>= 1`
- k_values: `1, 3, 5, 10`

## Baseline Compatibility

- bm25: BM25 (present)
- dense: Dense retrieval (present)
- hybrid: Hybrid retrieval (present)
- hybrid_rerank: Hybrid + rerank (present)

## Metrics By Method

| method | n_evaluable_queries | recall_at_1 | recall_at_3 | recall_at_5 | recall_at_10 | ndcg_at_1 | ndcg_at_3 | ndcg_at_5 | ndcg_at_10 | mrr_at_10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BM25 | 45 | 0.125682 | 0.311285 | 0.398769 | 0.456652 | 0.607407 | 0.535343 | 0.510874 | 0.490940 | 0.797249 |
| Dense retrieval | 45 | 0.116944 | 0.291871 | 0.410642 | 0.647050 | 0.518519 | 0.508249 | 0.512319 | 0.598760 | 0.740741 |
| Hybrid retrieval | 45 | 0.093637 | 0.279135 | 0.459080 | 0.663082 | 0.451852 | 0.483421 | 0.539196 | 0.594183 | 0.717989 |
| Hybrid + rerank | 45 | 0.123741 | 0.279168 | 0.420242 | 0.509897 | 0.614815 | 0.529732 | 0.551437 | 0.552932 | 0.783333 |

## Interpretation Notes

- Recall@K and MRR@10 treat relevance scores >= threshold as relevant.
- nDCG@K uses graded relevance with gain = 2^relevance - 1.
- Unjudged retrieved items are treated as relevance 0.
- Queries with no positive qrels are marked non-evaluable and excluded from macro averages.
