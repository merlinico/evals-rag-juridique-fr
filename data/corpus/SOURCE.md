# Source du corpus

## Provenance

- **Producteur** : DILA (Direction de l'information légale et administrative)
- **Jeu** : LEGI — Codes, lois et règlements consolidés
- **Textes** :
  - Code civil (`LEGITEXT000006070721`)
  - Code de la consommation (`LEGITEXT000006069565`)
  - Code du travail (`LEGITEXT000006072050`)
- **Fichier source (articles)** : `Freemium_legi_global_20250713-140000.tar.gz` (2025-07-13)
- **URL de téléchargement** : https://echanges.dila.gouv.fr/OPENDATA/LEGI/Freemium_legi_global_20250713-140000.tar.gz
- **Catalogue** : https://www.data.gouv.fr/datasets/legi-codes-lois-et-reglements-consolides
- **Historique de versions** : enrichi depuis
  `Freemium_legi_global_20261108-140000.tar.gz`
  (https://echanges.dila.gouv.fr/OPENDATA/LEGI/Freemium_legi_global_20261108-140000.tar.gz)
  — voir `version_dump_*` / `version_limits` dans `articles.json.gz` → `source`.

## Licence

Licence Ouverte / Open Licence 2.0 (Etalab) :
https://www.etalab.gouv.fr/licence-ouverte-open-licence/

Réutilisation libre avec mention de la paternité (DILA), de l'URL de téléchargement,
du nom du fichier et de sa date.

## Instantané

- Snapshot id : `codes-v0.2-2025-07-13`
- Contenu : articles en vigueur des trois codes ci-dessus
- Fichiers versionnés (compressés) :
  - `articles.json.gz` — unités `Article` (hiérarchie livre / titre / chapitre ;
    la section reste dans `contexte`)
  - `versions.json.gz` — `ArticleVersion` (intervalle `[debut, fin)`)
  - `crossrefs.json.gz` — graphe `CrossRef` (citations / renvois parsés)
  - `eval_subset.json.gz` — sous-ensemble CI / harness (= gold MVP, recall stable)
  - `mvp_seed.json.gz` — graine de stabilité des ids LEGIARTI MVP pour le rebuild
  - `manifest.json` — compteurs rapides
- Extraction articles : jeu Hugging Face `VinceGx33/legi-french-law-2025`
  (licence etalab-2.0), dérivé du dump LEGI officiel du 2025-07-13.
- **Stabilité** : les ids `LEGIARTI` du gold MVP (Code de la consommation) sont
  conservés tels quels.

## Limites

- Pas une base juridique opposable ; figé pour l'évaluation RAG.
- Historique `ArticleVersion` : tip pour tous les articles ; versions antérieures
  limitées (défaut : max 8 par article, `debut >= 2000-01-01`) pour garder une
  taille git raisonnable — voir `source.version_limits`.
- Le graphe `CrossRef` est heuristique (regex sur le texte) : seules les cibles
  résolues vers un id du snapshot sont conservées.
- Le dump Freemium 2025-07-13 n'est plus listé sur le serveur DILA ; le rebuild
  articles passe par le dataset HF dérivé. L'historique peut provenir d'un stock
  Freemium plus récent (`--dump`).

## Rebuild

```bash
# 1. Parquet HF (articles en vigueur)
uv run python -c "from huggingface_hub import hf_hub_download; \
  print(hf_hub_download('VinceGx33/legi-french-law-2025','legi_french_law.parquet', \
  repo_type='dataset', local_dir='/tmp/legi-build'))"

# 2. (Optionnel) stock Freemium pour l'historique de versions
# curl -L -o /tmp/legi-build/Freemium_legi_global_YYYYMMDD-HHMMSS.tar.gz \
#   https://echanges.dila.gouv.fr/OPENDATA/LEGI/Freemium_legi_global_YYYYMMDD-HHMMSS.tar.gz

uv run python scripts/build_corpus.py \
  --parquet /tmp/legi-build/legi_french_law.parquet \
  --mvp data/corpus/mvp_seed.json.gz \
  --dump /tmp/legi-build/Freemium_legi_global_YYYYMMDD-HHMMSS.tar.gz
```

Dépendances one-shot du script : `pandas`, `pyarrow`, `huggingface_hub`
(`uv pip install pandas pyarrow huggingface_hub`).

Le harness CI lit `eval_subset.json.gz` via `configs/default.yaml` ; l'API
`load_corpus()` sans chemin charge le snapshot multi-codes complet.
