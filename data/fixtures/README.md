# Fixtures de génération

Les fichiers `generations_chunk_*.json` contiennent les réponses du générateur local
(`qwen2.5:3b-instruct` via Ollama), figées pour que la CI ne dépende pas d'un LLM.

La CI recalcule uniquement le **retrieval** et les **métriques**, puis compare à
`baseline_metrics.json`.

Régénérer :

```bash
ollama pull qwen2.5:3b-instruct
uv run rag-eval --generate --write-baseline
```
