# Fixtures de génération

Les fichiers `generations_chunk_*.json` contiennent les réponses du générateur local
figées pour que la CI ne dépende pas d'un LLM.

Format contrat : `GenerationRecord` (`question_id`, `config_id`, `model`,
`prompt_hash`, `answer`, `cited_ids`, `abstained`). Les fixtures MVP legacy
(`cited_article_nums`, `chunk_size`) restent acceptées via alias.

La CI recalcule uniquement le **retrieval** et les **métriques**, puis compare à
`baseline_metrics.json` via un **test de significance apparié** (pas un seuil fixe).
Les runs lourds 7–8B se font hors CI (GPU local) — voir [`RUN_ON_GPU.md`](../../RUN_ON_GPU.md).

## Regen CI-light (3B, optionnel)

```bash
ollama pull qwen2.5:3b-instruct
uv run rag-eval --generate --write-baseline
```

## Regen offline 7B (GPU, une fois)

```bash
ollama pull qwen2.5:7b-instruct
uv run python scripts/generate_offline.py \
  --model qwen2.5:7b-instruct \
  --write-baseline
```

`baseline_metrics.json` doit inclure `per_question.{recall_at_k,faithfulness}`
(ids + values) pour le gate CI.
