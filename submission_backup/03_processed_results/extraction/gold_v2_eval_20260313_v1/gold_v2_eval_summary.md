# Gold V2 Evaluation Summary

- base_gold: `backend/evaluation/gold_seed.csv`
- batch_gold: `backend/runs/gold_batch1_final_20260313_v1\gold_seed_batch1_final.csv`
- gold_seed_v2_csv: `backend/evaluation/gold_seed_v2.csv`
- gold_seed_v2_xlsx: `backend/evaluation/gold_seed_v2.xlsx`
- merged_total_rows: `22`
- base_total_rows: `15`
- batch_appended_rows: `7`
- duplicate_count: `0`

## Batch1 Formally Included
- Indigenous OrganicOxidized Fluid Interactions in the Tissint Mars Meteorite
- Investigating the impact of xray computed tomography imaging on soluble organic matter in the Murchison meteorite: Implications for Bennu sample analyses
- Extraterrestrial ribose and other sugars in primitive meteorites
- Molecular distribution and 13C isotope composition of volatile organic compounds in the Murchison and Sutters Mill carbonaceous chondrites
- Extraterrestrial hexamethylenetetramine Yasuhiro Oba
- High-spatial resolution functional chemistry of nitrogen compounds in the observed UK meteorite fall Winchcombe
- Speciation of organosulfur compounds in carbonaceous chondrites

## Evaluation Coverage
- old_gold: total_rows=15, evaluated_rows=11, skipped_rows=4, coverage_rate=0.7333
- new_gold_v2: total_rows=22, evaluated_rows=18, skipped_rows=4, coverage_rate=0.8182

## Metric Changes
- meteorite_name: P 0.8750 -> 0.6667, R 0.8750 -> 0.8333, F1 0.8750 -> 0.7407, n_samples 9 -> 16
- organic_compounds: P 0.3000 -> 0.5733, R 0.6667 -> 0.9149, F1 0.4138 -> 0.7049, n_samples 9 -> 16
- contamination_controls: P 0.1852 -> 0.2069, R 0.5000 -> 0.5455, F1 0.2703 -> 0.3000, n_samples 8 -> 10
- overall_macro_avg: P 0.4534 -> 0.4823, R 0.6806 -> 0.7646, F1 0.5197 -> 0.5819, n_samples 26 -> 42

## Duplicate Handling
- none

## Fixed Eval Input Duplicates
- none
