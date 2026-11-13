# Rapport de régression RAG — Code de la consommation

Comparaison de deux tailles de chunks (fusion hybride BM25 + embeddings).

Métrique de rappel : **passage recall@5** (ids d'articles).
Fidélité : citation obligatoire + article cité présent dans le contexte + chevauchement lexical.

## Tableau

| Config | chunk_size | recall@k | faithfulness | abstention correcte (unans.) | fausse abstention (ans.) |
|---|---:|---:|---:|---:|---:|
| chunk_500 | 500 | 0.950 | 0.886 | 1.000 | 0.200 |
| chunk_1000 | 1000 | 0.967 | 0.771 | 1.000 | 0.067 |

## Commentaire

- Meilleur rappel : **chunk_1000** (0.967).
- Meilleure fidélité (citation + overlap) : **chunk_500** (0.886).
- Écart de recall@5 (chunk_1000 − chunk_500) : +0.017.
- Les deux chunk sizes sont proches sur ce petit corpus gelé ; des écarts plus nets sont attendus avec un corpus plus large ou un reranker.

## Limites

- Jeu d'or non encore validé humainement (`validated: false`).
- Fidélité fondée sur des heuristiques (pas de LLM-as-judge).
- Générateur local petit : les fixtures CI figent ses sorties.
