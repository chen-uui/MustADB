# Answer-Level Evaluation Workflow

## Step 1: Open The Annotation Template

Use:

`answer_level_evaluation_template.csv`

Each row contains one generated answer for one question under one pipeline. The template preserves the query, evidence document IDs, evidence text, and generated answer.

## Step 2: Fill Human Labels

Annotators should fill only these columns:

- `answer_correct`
- `evidence_support_label`
- `partially_supported_subtype`
- `evidence_mismatch`
- `hallucination_flag`
- `annotator_notes`

Do not edit `query`, `evidence_text`, or `generated_answer` during annotation.

## Step 3: Treat LLM-Only Rows Carefully

LLM-only rows intentionally have empty `evidence_text`. They still require answer correctness and support/verifiability judgments. A factually plausible answer may still be unsupported because no retrieval evidence was supplied.

## Step 4: Do Not Use Retrieval Qrels As Answer Labels

Retrieval qrels are document-level relevance judgments. They must not be copied into `evidence_support_label`, `answer_correct`, or `hallucination_flag`.

## Step 5: Aggregate Metrics Only After Labels Are Complete

After manual labels are filled, run a separate metrics aggregation step to compute pipeline-level counts and percentages:

- fully supported
- partially supported
- unsupported
- evidence mismatch
- hallucination rate
- answer correctness, if labels are complete

No final metrics should be reported from the blank template.
