# Stability Analysis Summary

- Bootstrap replicates: `2000`
- Random seed: `20260402`
- Retrieval/chunk/alpha CI: percentile bootstrap over queries.
- Paired comparisons: percentile bootstrap over paired query-level metric differences.
- Manual evaluation CI: percentile bootstrap over annotated samples.

## Retrieval 95% CI

| mode | Recall@5 | Recall@5 95% CI | MRR@5 | MRR@5 95% CI | nDCG@5 | nDCG@5 95% CI |
|---|---:|---|---:|---|---:|---|
| bm25 | 0.1833 | [0.0500, 0.3333] | 0.2833 | [0.0500, 0.5500] | 0.1875 | [0.0414, 0.3535] |
| dense | 0.6583 | [0.4750, 0.8333] | 0.6583 | [0.4083, 0.8750] | 0.5731 | [0.3996, 0.7405] |
| hybrid | 0.6167 | [0.3833, 0.8338] | 0.6083 | [0.3500, 0.8583] | 0.5094 | [0.3179, 0.6983] |
| hybrid_rerank | 0.6833 | [0.4833, 0.8667] | 0.5783 | [0.3567, 0.8083] | 0.5173 | [0.3664, 0.6681] |

## Chunk Paired CI

| comparison | metric | diff | 95% CI | crosses 0 |
|---|---|---:|---|---|
| 700:80 - 500:50 | recall_at_5 | 0.2333 | [0.0000, 0.5000] | yes |
| 700:80 - 500:50 | mrr_at_5 | 0.1117 | [-0.1386, 0.3367] | yes |
| 700:80 - 500:50 | ndcg_at_5 | 0.1060 | [-0.0943, 0.2927] | yes |
| 700:80 - 900:100 | recall_at_5 | 0.0667 | [-0.1500, 0.3338] | yes |
| 700:80 - 900:100 | mrr_at_5 | 0.1083 | [-0.1634, 0.4250] | yes |
| 700:80 - 900:100 | ndcg_at_5 | 0.0275 | [-0.1850, 0.2532] | yes |

## Alpha Paired CI

| comparison | metric | diff | 95% CI | crosses 0 |
|---|---|---:|---|---|
| alpha_0.7 - alpha_0.9 | recall_at_5 | 0.0000 | [0.0000, 0.0000] | yes |
| alpha_0.7 - alpha_0.9 | mrr_at_5 | 0.0000 | [0.0000, 0.0000] | yes |
| alpha_0.7 - alpha_0.9 | ndcg_at_5 | 0.0000 | [0.0000, 0.0000] | yes |

## Manual Evaluation 95% CI

| metric | point | 95% CI |
|---|---:|---|
| answer_accuracy | 0.7875 | [0.6875, 0.8750] |
| supported_rate | 0.2625 | [0.1750, 0.3625] |
| partially_supported_rate | 0.6500 | [0.5375, 0.7500] |
| unsupported_rate | 0.0875 | [0.0375, 0.1500] |

## Manual Evaluation by Mode 95% CI

| mode | metric | point | 95% CI |
|---|---|---:|---|
| bm25 | answer_accuracy | 0.8000 | [0.6500, 0.9500] |
| bm25 | supported_rate | 0.3500 | [0.1500, 0.5500] |
| bm25 | partially_supported_rate | 0.5500 | [0.3500, 0.7500] |
| bm25 | unsupported_rate | 0.1000 | [0.0000, 0.2500] |
| dense | answer_accuracy | 0.8000 | [0.6000, 0.9500] |
| dense | supported_rate | 0.3000 | [0.1000, 0.5000] |
| dense | partially_supported_rate | 0.6000 | [0.3500, 0.8000] |
| dense | unsupported_rate | 0.1000 | [0.0000, 0.2500] |
| hybrid | answer_accuracy | 0.7000 | [0.5000, 0.9000] |
| hybrid | supported_rate | 0.2500 | [0.1000, 0.4500] |
| hybrid | partially_supported_rate | 0.6000 | [0.3500, 0.8000] |
| hybrid | unsupported_rate | 0.1500 | [0.0000, 0.3000] |
| hybrid_rerank | answer_accuracy | 0.8500 | [0.7000, 1.0000] |
| hybrid_rerank | supported_rate | 0.1500 | [0.0000, 0.3000] |
| hybrid_rerank | partially_supported_rate | 0.8500 | [0.7000, 1.0000] |
| hybrid_rerank | unsupported_rate | 0.0000 | [0.0000, 0.0000] |