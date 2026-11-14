# Regen fixtures 7B + retrieval lourd — Windows/WSL ou Talos

Hors CI. Pas de clé d’API payante.

Deux chemins GPU distincts :

1. **Génération 7B** (Ollama) → fixtures `GenerationRecord` pour le harness
2. **Retrieval lourd** (`RAG_HEAVY=1`) → bge-m3 / reranker / graph sur Talos

## Corpus

| Fichier | Usage |
|---|---|
| `data/corpus/eval_subset.json.gz` | Défaut CI / harness (`configs/default.yaml` → `corpus_path`) — gold-aligned |
| `data/corpus/articles.json.gz` | Snapshot complet civil + consommation + travail (`corpus.full_articles_path`) |
| `versions.json.gz` / `crossrefs.json.gz` | Versions LEGI + graphe (graph retriever / `as_of`) |

Le script de génération lit `corpus_path` (subset par défaut). Pour indexer le
corpus complet au moment de générer :

```bash
uv run python scripts/generate_offline.py \
  --model qwen2.5:7b-instruct \
  --corpus-path data/corpus/articles.json.gz \
  --write-baseline
```

Les fixtures CI MVP restent alignées sur le **subset** + configs `chunk_500` /
`chunk_1000` (hybrid e5 injecté par le CLI).

## 1) Fixtures 7B — Windows + WSL (16 GB VRAM)

### Prérequis

- Windows 10/11 + **WSL2** (Ubuntu)
- NVIDIA driver Windows à jour + GPU ~**16 GB VRAM**
- Dans WSL : `nvidia-smi` OK, Python ≥ 3.11, [uv](https://github.com/astral-sh/uv)
- [Ollama](https://ollama.com) dans WSL (recommandé)

### Setup WSL (une fois)

```bash
cd /path/to/evals-rag-juridique-fr
uv sync --extra dev
curl -fsSL https://ollama.com/install.sh | sh
ollama serve   # terminal 1
```

```bash
ollama pull qwen2.5:7b-instruct
nvidia-smi
```

### Commande exacte (run du dimanche)

```bash
uv sync --extra dev
ollama pull qwen2.5:7b-instruct

uv run python scripts/generate_offline.py \
  --config configs/default.yaml \
  --model qwen2.5:7b-instruct \
  --write-baseline
```

Écrit :

- `data/fixtures/generations_chunk_500.json`
- `data/fixtures/generations_chunk_1000.json`
- `data/fixtures/baseline_metrics.json` (scores par question pour le gate)

Sans écraser les fixtures 3B CI :

```bash
uv run python scripts/generate_offline.py \
  --model qwen2.5:7b-instruct \
  --suffix _7b \
  --write-baseline
```

### Vérification

```bash
uv run pytest -q
uv run rag-eval --use-fixtures --check-baseline
```

### Dépannage VRAM 16 Go

```bash
export OLLAMA_NUM_PARALLEL=1
uv run python scripts/generate_offline.py --model qwen2.5:7b-instruct --chunk-sizes 500
uv run python scripts/generate_offline.py --model qwen2.5:7b-instruct --chunk-sizes 1000 --write-baseline
```

## 2) Retrieval lourd — Talos (`RAG_HEAVY=1`)

Les configs `retrieval.configs` (bge-m3, rerank, graph, …) hors MVP e5
nécessitent les vrais encodeurs. Sans `RAG_HEAVY`, le registry utilise un
HashEncoder (recall non significatif).

Sur Talos (ou toute machine GPU avec assez de VRAM / disque HF) :

```bash
uv sync --extra dev
export RAG_HEAVY=1
# optionnel : corpus complet + versions/crossrefs déjà sous data/corpus/
python -m rag_juridique.retrieval.eval_recall --all
```

Configs listées dans `configs/default.yaml` → `retrieval.configs`, par ex. :

- `hybrid_bge_m3__fixed_500` / `fixed_1000` / `per_article` / `structural`
- `hybrid_bge_m3_rerank__…`
- `hybrid_bge_m3_graph__…`
- `dense_bge_m3__…`, `bm25__…`, `hybrid_e5__…`

Modèles (téléchargés localement, pas d’API payante) :

- `BAAI/bge-m3` (`retrieval.dense_model`)
- `BAAI/bge-reranker-v2-m3` (`retrieval.reranker_model`)

Le harness CI (`rag-eval --use-fixtures`) reste sur **e5 + subset** et ne
charge pas bge-m3.

## NLI claim-level (optionnel, lourd)

```bash
uv sync --extra nli
# configs/default.yaml : metrics.nli_enabled: true
uv run rag-eval --use-fixtures
```

Modèle : `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`.
En CI : `nli_enabled: false` (fallback overlap).
