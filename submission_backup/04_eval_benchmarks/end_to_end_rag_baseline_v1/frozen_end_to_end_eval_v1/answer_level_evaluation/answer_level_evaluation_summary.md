# Answer-level evaluation summary

## Scope

- Total generated answers: 100

- Questions: 20

- Pipelines: llm_only, bm25_rag, dense_rag, hybrid_rag, hybrid_rerank_rag

- Generation model: llama3.1:8b-instruct-q4_K_M (local/Ollama)

- Annotation labels filled: answer_correct, evidence_support_label, partially_supported_subtype, evidence_mismatch, hallucination_flag, annotator_notes


## Pipeline-level metrics

| pipeline          |   n |   fully_supported | fully_supported_pct   |   partially_supported | partially_supported_pct   |   unsupported | unsupported_pct   |   answer_correct_1 | answer_correct_pct   |   answer_incorrect_0 |   answer_unclear |   evidence_mismatch_count | evidence_mismatch_pct   |   hallucination_flag_count | hallucination_flag_pct   |
|:------------------|----:|------------------:|:----------------------|----------------------:|:--------------------------|--------------:|:------------------|-------------------:|:---------------------|---------------------:|-----------------:|--------------------------:|:------------------------|---------------------------:|:-------------------------|
| llm_only          |  20 |                 0 | 0.0%                  |                     0 | 0.0%                      |            20 | 100.0%            |                 18 | 90.0%                |                    2 |                0 |                         0 | 0.0%                    |                         20 | 100.0%                   |
| bm25_rag          |  20 |                 7 | 35.0%                 |                    11 | 55.0%                     |             2 | 10.0%             |                 11 | 55.0%                |                    2 |                7 |                         2 | 10.0%                   |                          2 | 10.0%                    |
| dense_rag         |  20 |                 4 | 20.0%                 |                    15 | 75.0%                     |             1 | 5.0%              |                 16 | 80.0%                |                    1 |                3 |                         3 | 15.0%                   |                          2 | 10.0%                    |
| hybrid_rag        |  20 |                 5 | 25.0%                 |                    14 | 70.0%                     |             1 | 5.0%              |                 10 | 50.0%                |                    2 |                8 |                         5 | 25.0%                   |                          3 | 15.0%                    |
| hybrid_rerank_rag |  20 |                 7 | 35.0%                 |                    11 | 55.0%                     |             2 | 10.0%             |                 11 | 55.0%                |                    1 |                8 |                         1 | 5.0%                    |                          1 | 5.0%                     |


## Key findings

- The LLM-only setting produced many plausible answers, but none were document-grounded because no retrieved evidence was provided; all 20 LLM-only answers were therefore labeled `unsupported` for evidence support.
- All RAG settings substantially reduced unsupported outputs. Unsupported answers were 10.0% for BM25+LLM, 5.0% for dense+LLM, 5.0% for hybrid+LLM, and 10.0% for hybrid+rerank+LLM.
- Dense and hybrid settings produced the lowest unsupported rates, while hybrid+rerank had the lowest evidence-mismatch and hallucination-flag rates among the RAG variants.
- The results support the controlled conclusion that retrieval evidence improves document grounding under the same local generation model. The experiment should not be presented as a comparison of different LLM backends.

## Notes for manuscript use

A careful manuscript statement should emphasize evidence grounding rather than claiming that every RAG variant improves factual correctness. A suitable interpretation is: retrieval evidence reduced unsupported answer generation compared with the same LLM used without evidence, while different retrieval settings showed different precision/coverage trade-offs.