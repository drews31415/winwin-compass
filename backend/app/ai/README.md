# AI Layer

The AI layer turns user questions into grounded answers using database queries, policy retrieval, and LLM response generation.

## Files

- `prompts.py`: system, Text-to-SQL, and report prompt templates.
- `text_to_sql.py`: natural-language-to-SQL generation, validation, execution, and self-correction.
- `rag_engine.py`: policy document seeding, vector search, and fallback matching.
- `chat_engine.py`: intent classification and orchestration across data, report, policy, prediction, and risk flows.

## Fallback Policy

OpenAI-dependent features must degrade to sample responses when `OPENAI_API_KEY` is missing or the LLM call fails. Keep fallback text accurate and clearly based on sample/demo data.

## Safety

Generated SQL must remain read-only. Reject destructive statements such as `DROP`, `DELETE`, `UPDATE`, and `INSERT`.
