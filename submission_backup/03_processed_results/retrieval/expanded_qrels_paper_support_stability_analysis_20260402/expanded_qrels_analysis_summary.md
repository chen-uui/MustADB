# Expanded Qrels Analysis Summary

- bootstrap unit: query
- bootstrap reps: 2000
- CI method: percentile 95% CI
- qrels: retrieval_qrels_expanded.csv (20 queries, 57 relevant rows)

## Retrieval Main

| mode | alpha | Recall@5 | Recall@5 95% CI | MRR@5 | MRR@5 95% CI | nDCG@5 | nDCG@5 95% CI |
|---|---:|---:|---|---:|---|---:|---|
| bm25 | NA | 0.1917 | [0.1000, 0.2792] | 0.4083 | [0.2167, 0.6002] | 0.2227 | [0.1196, 0.3301] |
| dense | NA | 0.5842 | [0.4650, 0.7017] | 0.8042 | [0.6542, 0.9250] | 0.5879 | [0.4723, 0.6856] |
| hybrid | 0.7 | 0.5742 | [0.4458, 0.6950] | 0.7708 | [0.6083, 0.9167] | 0.5648 | [0.4530, 0.6692] |
| hybrid_rerank | 0.7 | 0.6033 | [0.4833, 0.7150] | 0.7392 | [0.5924, 0.8851] | 0.5562 | [0.4615, 0.6462] |

## Chunk Comparison

| comparison | metric | diff | 95% CI | crosses 0 |
|---|---|---:|---|---|
| 700:80 - 500:50 | Recall@5 | 0.1433 | [-0.0150, 0.3117] | yes |
| 700:80 - 500:50 | MRR@5 | 0.1183 | [-0.0650, 0.3125] | yes |
| 700:80 - 500:50 | nDCG@5 | 0.1082 | [-0.0152, 0.2213] | yes |
| 700:80 - 900:100 | Recall@5 | 0.0583 | [-0.0833, 0.2167] | yes |
| 700:80 - 900:100 | MRR@5 | 0.1375 | [-0.0500, 0.3351] | yes |
| 700:80 - 900:100 | nDCG@5 | 0.0613 | [-0.0815, 0.1904] | yes |

## Alpha Comparison

| comparison | metric | diff | 95% CI | crosses 0 |
|---|---|---:|---|---|
| alpha_0.7 - alpha_0.9 | Recall@5 | [0.0000] | [0.0000, 0.0000] | yes |
| alpha_0.7 - alpha_0.9 | MRR@5 | [0.0000] | [0.0000, 0.0000] | yes |
| alpha_0.7 - alpha_0.9 | nDCG@5 | [0.0000] | [0.0000, 0.0000] | yes |

## Notes

- Point estimates among chunk settings are highest for 700/80 on Recall@5, MRR@5, and nDCG@5.
- All chunk paired-difference CIs cross 0, so chunk differences should be written as trends rather than strong effects.
- For hybrid_rerank on the 700/80 collection, alpha=0.7 and alpha=0.9 are identical on the saved query-level results; there is no observed difference in the paired comparison.