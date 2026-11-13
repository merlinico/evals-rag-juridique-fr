# Regen fixtures 7B — Windows + WSL (16 GB VRAM)

Script hors CI : génère des `GenerationRecord` via Ollama (`qwen2.5:7b-instruct`)
sur une machine GPU, une fois (cible : dimanche). Pas de clé d’API payante.

## Prérequis

- Windows 10/11 + **WSL2** (Ubuntu)
- NVIDIA driver Windows à jour + GPU ~**16 GB VRAM**
- Dans WSL : `nvidia-smi` OK, Python ≥ 3.11, [uv](https://github.com/astral-sh/uv)
- [Ollama](https://ollama.com) installé **dans WSL** (recommandé) ou Windows avec
  `OLLAMA_HOST` joignable depuis WSL

## Setup WSL (une fois)

```bash
# dans Ubuntu WSL
cd /path/to/evals-rag-juridique-fr
uv sync --extra dev

# Ollama (si pas déjà installé dans WSL)
curl -fsSL https://ollama.com/install.sh | sh
ollama serve   # laisser tourner dans un terminal
```

Autre terminal :

```bash
ollama pull qwen2.5:7b-instruct
nvidia-smi     # vérifier la VRAM libre (~8–10 Go pour le 7B Q4/Q5)
```

Si Ollama tourne sous Windows (pas WSL) :

```bash
export OLLAMA_HOST=http://$(cat /etc/resolv.conf | awk '/nameserver/{print $2}'):11434
# ou : export OLLAMA_HOST=http://127.0.0.1:11434  si port forwardé
```

## Commande exacte (run du dimanche)

Depuis la racine du repo, dans WSL :

```bash
uv sync --extra dev
ollama pull qwen2.5:7b-instruct

uv run python scripts/generate_offline.py \
  --config configs/default.yaml \
  --model qwen2.5:7b-instruct \
  --write-baseline
```

Cela écrit :

- `data/fixtures/generations_chunk_500.json`
- `data/fixtures/generations_chunk_1000.json`
- `data/fixtures/baseline_metrics.json` (avec scores par question pour le gate)

Pour **ne pas** écraser les fixtures CI 3B, ajoutez un suffixe :

```bash
uv run python scripts/generate_offline.py \
  --model qwen2.5:7b-instruct \
  --suffix _7b \
  --write-baseline
```

→ `generations_chunk_500_7b.json`, etc.

## Vérification après regen

```bash
uv run pytest -q
uv run rag-eval --use-fixtures --check-baseline
```

Puis commit + push des fixtures / baseline / `reports/regression.md` si les
scores changent.

## NLI claim-level (optionnel, lourd)

Hors CI, pour la faithfulness NLI FR/multilingue :

```bash
uv sync --extra nli
# dans configs/default.yaml : metrics.nli_enabled: true
uv run rag-eval --use-fixtures
```

Modèle par défaut : `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`.
En CI, laisser `nli_enabled: false` (fallback overlap).

## Dépannage VRAM 16 Go

- Préférer `qwen2.5:7b-instruct` (quantisé par Ollama) plutôt qu’un 14B.
- Fermer les apps GPU Windows (jeux, autre LLM).
- Si OOM : `OLLAMA_NUM_PARALLEL=1` et ne lancer qu’un chunk size à la fois :

```bash
uv run python scripts/generate_offline.py --model qwen2.5:7b-instruct --chunk-sizes 500
uv run python scripts/generate_offline.py --model qwen2.5:7b-instruct --chunk-sizes 1000 --write-baseline
```
