# CONTRIBUTING — agents parallèles sans conflits

## Règle d'or

Les **contrats** (`src/rag_juridique/contracts/`, `schemas/`) sont gelés entre les modules.
Quatre agents phase 2 travaillent en parallèle : chacun reste dans ses chemins (voir `AGENTS.md`).

## Comment éviter les conflits

1. **Branchez depuis `master` à jour** ; une branche = un agent = un module.
2. **N'éditez que vos chemins d'ownership.** Lecture seule ailleurs.
3. **Ne modifiez pas les contrats** pour « débloquer » une feature. Si un champ manque :
   - documentez le besoin dans la PR / issue ;
   - livrez derrière une extension *additive* optionnelle seulement après un mini-PR d'interfaces.
4. **Données** : écrivez uniquement sous votre `data/<module>/`. Ne reformatez pas les JSON des autres.
5. **Imports** : consommez les types depuis `rag_juridique.contracts` (ou les re-exports stables des packages). Ne dupliquez pas de dataclasses parallèles.
6. **`configs/default.yaml`** : ajoutez des clés sous votre section ; ne renommez / ne cassez pas les clés MVP.
7. **Fixtures de génération** : hors CI, GPU local ; respectez `GenerationRecord` (`question_id`, `config_id`, `model`, `prompt_hash`, `answer`, `cited_ids`, `abstained`). Les fixtures MVP legacy restent lisibles (aliases).
8. **Tests** : ajoutez des tests sous `tests/` préfixés par module (`test_corpus_*`, `test_gold_*`, …) pour limiter les collisions de fichiers.
9. **Lockfile** : si `uv.lock` diverge, rebasez sur `master` et régénérez plutôt que de merger à la main.
10. **CI verte** : `pytest` + `rag-eval --use-fixtures --check-baseline` doivent passer ; ne régressez pas les baselines sans justification.

## PR d'interfaces (rare)

Réservé aux changements de forme partagée (nouveau champ obligatoire, nouveau protocole, rename).
Petit, reviewable, **sans** feature work — comme le freeze phase 2.
