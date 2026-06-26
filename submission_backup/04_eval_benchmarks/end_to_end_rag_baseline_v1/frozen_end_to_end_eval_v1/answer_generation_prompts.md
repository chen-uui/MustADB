# Answer Generation Prompts

## Shared Rules

Use the same local LLM and decoding settings for every pipeline. The experiment isolates the effect of retrieval evidence, not the strength of different generation models.

Pinned model for this revision experiment:

- backend: `local/Ollama`
- generation model: `llama3.1:8b-instruct-q4_K_M`
- external API fallback: disabled
- `.env` `LLM_MODEL` fallback: disabled

The prompt JSONL files contain complete prompt strings. Each row includes:

- `sample_id`
- `qid`
- `question`
- `pipeline`
- `retrieval_method`
- `evidence_top_k`
- `prompt`
- `evidence`

## LLM-Only Condition

The LLM-only prompt provides only the question and task instruction. It must not receive retrieved evidence, document IDs, qrels, candidate pools, or full corpus/PDF text.

Template:

```text
You are a scientific assistant answering a literature-mining question about extraterrestrial organic matter, meteorites, analytical methods, isotope evidence, contamination controls, or meteorite taxonomy.

Answer concisely and distinguish direct evidence from uncertainty.

No retrieved evidence is provided in this condition. Answer using only the model's internal knowledge. Do not invent paper-specific citations, document IDs, or unsupported details. If the question requires literature evidence that you cannot verify, state the uncertainty explicitly.

Question:
{question}

Answer:
```

## RAG Conditions

RAG prompts provide the same question plus top-k ranked evidence snippets for the selected retrieval method.

Template:

```text
You are a scientific assistant answering a literature-mining question about extraterrestrial organic matter, meteorites, analytical methods, isotope evidence, contamination controls, or meteorite taxonomy.

Answer concisely and distinguish direct evidence from uncertainty.

Use only the retrieved evidence below. Cite evidence IDs such as [E1] for claims that depend on the evidence. If the evidence is insufficient, say so instead of filling gaps from outside knowledge.

Question:
{question}

Retrieved evidence:
[E1] rank={rank}; doc_id={doc_id}; score={score}; title={title}; doi={doi}; year={year}
{snippet}

Answer:
```

## Local LLM Execution

The preparation script intentionally does not call a model. To run generation, feed each JSONL prompt file to a local Ollama-only batch runner that reads `end_to_end_runtime_config.freeze.json` and fails if `llama3.1:8b-instruct-q4_K_M` is unavailable. Do not call external APIs.

Generation outputs should be saved with at least:

- `sample_id`
- `pipeline`
- `qid`
- `question`
- `generated_answer`

These outputs can then be merged into `answer_level_evaluation_template.csv` for manual or LLM-assisted answer-level annotation.
