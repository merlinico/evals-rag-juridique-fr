# Fixtures de génération

Les fichiers `generations_chunk_*.json` contiennent les réponses du générateur local
(`qwen2.5:3b-instruct` via Ollama), figées pour que la CI ne dépende pas d'un LLM.

Format contrat : `GenerationRecord` (`question_id`, `config_id`, `model`,
`prompt_hash`, `answer`, `cited_ids`, `abstained`). Les fixtures MVP legacy
(`cited_article_nums`, `chunk_size`) restent acceptées via alias.

La CI recalcule uniquement le **retrieval** et les **métriques**, puis compare à
`baseline_metrics.json`. Les runs lourds 7–8B se font hors CI (GPU local) et
se commitent ici comme fixtures.

Régénérer :

```bash
ollama pull qwen2.5:3b-instruct
uv run rag-eval --generate --write-baseline
```
