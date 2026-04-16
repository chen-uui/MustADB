# Batch4 Core Review Summary

- gold_v3_csv: `D:\workspace\123\ccc\astrobiology\backend\evaluation\gold_seed_v3.csv`
- supporting_final_csv: `D:\workspace\123\ccc\astrobiology\backend\runs\gold_batch2_final_annotated_20260313_v1\gold_seed_batch2_supporting_final.csv`
- metadata_pool_count: `5`
- selected_count: `4`
- review_first_count: `2`
- backup_count: `2`

## What Changed Relative To Batch3

- Batch3 started from the old 50-row candidate table and tried to salvage stricter core-only items from that historical pool.
- Batch4 rebuilds the pool from the full processed PDF library, then excludes gold_v3 and supporting-first records before rerun.
- The new metadata gate is sample-anchor first: meteorites, micrometeorites, carbonaceous chondrites, asteroid-return samples, and real martian meteorites are favored.
- Analog/model/review/survivability/supporting-QC titles are filtered or demoted before they ever become batch4 review candidates.

## Most Recommended For Formal Core Review First
- Nanoscale infrared imaging analysis of carbonaceous chondrites to understand organic-mineral interactions during aqueous alteration
- Sulfur isotopic fractionation in vacuum UV photodissociation of hydrogen sulfide and its potential relevance to meteorite analysis

## Backup Only
- Organic material and gases in the early Solar System : the meteorite record
- Irradiation of nitrogen-rich ices by swift heavy ions - Clues for the formation of ultracarbonaceous micrometeorites

## Candidate Details
- Nanoscale infrared imaging analysis of carbonaceous chondrites to understand organic-mineral interactions during aqueous alteration | likelihood=review_first | scope_risk=moderate_scope_risk | score=16
  tags: analytical_methods; amino_acids; organic_matter
  why: direct sample paper with interpretable organics evidence, despite a methods-heavy presentation; metadata_bucket=core_sample_metadata; priority_reason=sample:chondrite; sample:chondrites; sample:carbonaceous; organic:organic; title:chondrite; title:imaging; recent_enough; projected_organics=1
- Sulfur isotopic fractionation in vacuum UV photodissociation of hydrogen sulfide and its potential relevance to meteorite analysis | likelihood=review_first | scope_risk=moderate_scope_risk | score=12
  tags: analytical_methods; amino_acids
  why: direct sample paper with interpretable organics evidence, despite a methods-heavy presentation; metadata_bucket=core_sample_metadata; priority_reason=sample:meteorite; organic:sulfur; cached_projected=1; title:meteorite; projected_organics=1; meteorite_name_present; organic_evidence_present; table_caption_or_analytical_evidence
- Organic material and gases in the early Solar System : the meteorite record | likelihood=backup | scope_risk=broad_review_like | score=25
  tags: amino_acids; carboxylic_acids; sugars; organic_matter
  why: broad or synthesis-style paper; keep only as backup if the cleaner sample pool is too small; metadata_bucket=soft_scope_boundary; priority_reason=sample:meteorite; organic:organic; cached_projected=7; broad_review_like; title:meteorite; title:organic material; projected_organics=7; rich_raw_support=8
- Irradiation of nitrogen-rich ices by swift heavy ions - Clues for the formation of ultracarbonaceous micrometeorites | likelihood=backup | scope_risk=analog_or_ice_simulation | score=23
  why: simulation-style ice irradiation study; keep only as backup despite micrometeorite relevance; metadata_bucket=soft_scope_boundary; priority_reason=sample:meteorite; sample:meteorites; sample:micrometeorite; sample:micrometeorites; title:meteorite; projected_organics=5; rich_raw_support=6; organic_evidence_present

## Suggested Exclusions / Borderlines
- broad_review: 16
- comment_or_reply; mars_non_sample_boundary: 2
- mars_analogue; mars_non_sample_boundary: 1
- mars_non_sample_boundary: 33
- mars_non_sample_boundary; survivability_or_life_discussion: 2
- missing_projected_organics: 1
- missing_sample_anchor: 567
- model_compound: 1
- sample:bennu; recent_enough; missing_organic_signal: 1
- sample:carbonaceous; recent_enough; broad_review_like; missing_organic_signal: 1
- sample:chondrite; sample:chondrites; missing_organic_signal: 1
- sample:chondrite; sample:chondrites; recent_enough; missing_organic_signal: 1
- sample:meteorite; analytical:raman; recent_enough; missing_organic_signal: 1
- sample:meteorite; missing_organic_signal: 1

## Estimated Core Size After New Additions
- current_core_total_rows: `23`
- current_core_evaluated_rows: `19`
- if_add_6_rows: total=`29`, evaluated=`25`
- if_add_10_rows: total=`33`, evaluated=`29`

## Why This Pool Is Better Suited To Core Gold
- The selected set prioritizes real-sample papers with clearer meteorite/sample anchors and usable organics evidence, instead of trying to reuse older boundary-heavy candidates.
- Backup items are kept visible, but they are explicitly separated from the first-pass formal-core list.
