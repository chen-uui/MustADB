# Retrieval Evaluation Report

## Inputs

- ranked_results: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\qrels_evaluation_run\retrieval_results_by_method.json`
- relevance_threshold_for_recall_mrr: `> 0`
- nDCG gain: `2^relevance - 1`
- unjudged retrieved documents: treated as relevance `0` by the evaluator; in this run, all top-10 retrieved documents were judged.

## Qrels Summary

- qrels_total: `683`
- relevant_documents_relevance_gt_0: `292`
- highly_relevant_documents_relevance_eq_2: `144`
- evaluated_queries: `45`
- queries_without_relevant_docs: `0`
- handling: all queries contain at least one positive qrel, so all are included.

## Ranked Results Export

| method | retrieved rows |
|---|---:|
| `bm25` | 274 |
| `dense` | 485 |
| `hybrid` | 414 |

## Metrics

| method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | nDCG@1 | nDCG@3 | nDCG@5 | nDCG@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bm25 | 0.125682 | 0.311285 | 0.398769 | 0.456652 | 0.607407 | 0.535343 | 0.510874 | 0.490940 | 0.797249 |
| dense | 0.116944 | 0.291871 | 0.410642 | 0.647050 | 0.518519 | 0.508249 | 0.512319 | 0.598760 | 0.740741 |
| hybrid | 0.093637 | 0.279135 | 0.459080 | 0.663082 | 0.451852 | 0.483421 | 0.539196 | 0.594183 | 0.717989 |

## Paper-Ready Results Text

Using the manually annotated qrels, all 45 benchmark queries had at least one positive relevance judgment and were included in macro-averaged evaluation. Among the three retrieval settings, hybrid obtained the highest Recall@10 (0.663082), while dense obtained the highest nDCG@10 (0.598760). These results indicate measurable differences between lexical, dense, and hybrid retrieval under the same judged pool; all top-10 retrieved documents in this evaluation had qrels judgments.
