# Frozen Results Summary

Version: `revision_qrels_eval_v1_mpnet768`

## Fixed Experiment State

- benchmark queries: 45
- qrels total: 683
- relevant docs (relevance > 0): 292
- highly relevant docs (relevance = 2): 144
- evaluated queries: 45
- queries without relevant docs: 0
- embedding model: `sentence-transformers/all-mpnet-base-v2`
- query vector dimension: 768
- Weaviate stored vector dimension: 768
- collection: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`

## Metrics

### BM25

| Metric | Value |
|---|---:|
| Recall@1 | 0.125682 |
| Recall@3 | 0.311285 |
| Recall@5 | 0.398769 |
| Recall@10 | 0.456652 |
| nDCG@1 | 0.607407 |
| nDCG@3 | 0.535343 |
| nDCG@5 | 0.510874 |
| nDCG@10 | 0.490940 |
| MRR@10 | 0.797249 |

### Dense

| Metric | Value |
|---|---:|
| Recall@1 | 0.116944 |
| Recall@3 | 0.291871 |
| Recall@5 | 0.410642 |
| Recall@10 | 0.647050 |
| nDCG@1 | 0.518519 |
| nDCG@3 | 0.508249 |
| nDCG@5 | 0.512319 |
| nDCG@10 | 0.598760 |
| MRR@10 | 0.740741 |

### Hybrid

| Metric | Value |
|---|---:|
| Recall@1 | 0.093637 |
| Recall@3 | 0.279135 |
| Recall@5 | 0.459080 |
| Recall@10 | 0.663082 |
| nDCG@1 | 0.451852 |
| nDCG@3 | 0.483421 |
| nDCG@5 | 0.539196 |
| nDCG@10 | 0.594183 |
| MRR@10 | 0.717989 |

## Archive Inclusion Note

The qrels files are now included in this archive: `qrels_relevance_only.csv` and `qrels_annotated_manual_style.csv`.
