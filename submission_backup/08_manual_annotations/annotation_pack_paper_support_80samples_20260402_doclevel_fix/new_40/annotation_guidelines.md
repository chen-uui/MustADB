# QA Annotation Guidelines

## `answer_correct`
- `1`: The answer is factually correct based on the provided evidence.
- `0`: The answer is incorrect, contradicts the evidence, or clearly overstates what the evidence says.
- `unclear`: The provided evidence is insufficient to judge correctness confidently.

## `evidence_support`
- `supported`: The answer is supported by the provided evidence snippets.
- `partially_supported`: Some answer content is supported, but some content is missing support.
- `unsupported`: The answer is not supported by the provided evidence.
- `unclear`: The evidence is too ambiguous or incomplete to judge support confidently.

## `unsupported_span_note`
- Only note the unsupported part of the answer.
- Do not rewrite the whole answer.
- Keep it short and specific.

## Annotation Rules
- Judge only against the evidence snippets in this pack.
- Do not infer support from outside knowledge or from documents not shown here.
- If the answer might be true elsewhere but is not supported here, mark it as unsupported or partially supported.
- If anything is ambiguous, write the reason in `annotation_note`.
