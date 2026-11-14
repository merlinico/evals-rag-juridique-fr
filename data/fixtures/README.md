# Fixtures de génération

Les fichiers `generations_chunk_*.json` contiennent les réponses du générateur local
figées pour que la CI ne dépende pas d'un LLM.

Format contrat : `GenerationRecord` (`question_id`, `config_id`, `model`,
`prompt_hash`, `answer`, `cited_ids`, `abstained`). Les fixtures MVP legacy
(`cited_article_nums`, `chunk_size`) restent acceptées via alias.

La CI recalcule le **retrieval** (hybrid e5 sur `eval_subset.json.gz`) et les
**métriques**, puis compare à `baseline_metrics.json` via un **test de
significance apparié** (pas un seuil fixe).

Runs hors CI :

- **7B Ollama** → `scripts/generate_offline.py` (voir [`RUN_ON_GPU.md`](../../RUN_ON_GPU.md))
- **Retrieval lourd** (bge-m3 / rerank / graph) → `RAG_HEAVY=1` sur Talos
  (`python -m rag_juridique.retrieval.eval_recall --all`)

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
# corpus complet (optionnel) :
#   --corpus-path data/corpus/articles.json.gz
```

`baseline_metrics.json` doit inclure `per_question.{recall_at_k,faithfulness}`
(ids + values) pour le gate CI.
