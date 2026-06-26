# Answer-Level Evaluation Guidelines

## Scope

Annotate each generated answer at the answer level. Do not use retrieval qrels as answer-support labels. Retrieval qrels judge whether documents are relevant to a query; this template judges whether a generated answer is factually correct and supported by the evidence shown to the generator.

## Columns To Fill

### answer_correct

Allowed values:

- `1` = factually correct
- `0` = factually incorrect
- `unclear` = cannot judge from available evidence

For RAG rows, judge correctness against the question and the provided evidence. For LLM-only rows, judge whether the answer is factually plausible/known; mark `unclear` when the answer requires paper-specific evidence that is not available in the row.

### evidence_support_label

Allowed values:

- `fully_supported`
- `partially_supported`
- `unsupported`

Use `fully_supported` when the answer directly addresses the query and all substantive factual claims are supported by the row evidence. Use `partially_supported` when the answer is useful but incomplete, over-broad, or only weakly grounded. Use `unsupported` when the main answer is not backed by the row evidence.

For LLM-only rows, there is no evidence text. If the answer makes specific literature claims, `unsupported` is usually appropriate for evidence support, even if `answer_correct` is marked `1` or `unclear`.

### partially_supported_subtype

Required only when `evidence_support_label=partially_supported`.

Allowed values:

- `missing_detail`
- `incomplete_entity_boundary`
- `weak_evidence_match`
- `over_generalization`
- `mixed`

Definitions:

- `missing_detail`: the answer omits key details needed to answer the query.
- `incomplete_entity_boundary`: the answer identifies a related entity/process but blurs the exact meteorite, compound, method, isotope, mineral phase, or contamination source.
- `weak_evidence_match`: the evidence is related background but does not directly substantiate the answer.
- `over_generalization`: the answer turns narrow evidence into a broader claim.
- `mixed`: more than one subtype applies and no single subtype dominates.

### evidence_mismatch

Allowed values:

- `1` = answer cites or implies evidence that does not support it
- `0` = no mismatch

Use `1` when the answer attributes a claim to evidence that says something different, cites the wrong document/snippet, or contradicts the provided evidence.

### hallucination_flag

Allowed values:

- `1` = answer contains unsupported specific factual claims
- `0` = no obvious hallucination

Mark `1` for unsupported named papers, meteorites, compounds, isotope values, analytical methods, numerical values, or causal claims that are not backed by the row evidence.

### annotator_notes

Briefly record the reason for the label, especially unsupported spans, evidence mismatch, or missing details.

## Important Rules

- Do not auto-fill labels.
- Do not use retrieval qrels as answer-level labels.
- Do not compare pipelines while labeling a row; label each row independently.
- Preserve generated answers and evidence text unchanged.
- For LLM-only rows, empty evidence is expected and should not be treated as a data error.
