# Retrieval Qrels Annotation Guidelines

## What counts as `relevant`
- The document directly answers the query, or provides evidence that would clearly help answer it.
- A document can still be relevant if it only covers one important facet of a multi-part query.

## What counts as `not_relevant`
- The document is off-topic, too generic, or only loosely connected by shared keywords.
- The snippet and title do not support the query intent, even if some terms overlap.

## Partial coverage
- If the document covers a substantial part of the query intent, mark it as relevant.
- Use `annotation_note` to explain what part is covered or missing.

## If the snippet is not enough
- Judge the title and snippet together.
- If the document is obviously relevant from title plus snippet, mark it relevant.
- If relevance is still unclear, leave a note in `annotation_note` rather than guessing.

## How to fill `candidate_relevance`
- Use `1` for relevant.
- Use `0` for not relevant.
- Keep `annotation_note` for ambiguity, partial coverage, or quality issues.
