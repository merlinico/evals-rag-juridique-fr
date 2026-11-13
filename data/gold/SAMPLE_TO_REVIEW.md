# Échantillon à valider (historique MVP — 10 questions)

> **Phase 2 :** le batch de revue humaine à traiter en priorité est
> [`REVIEW_BATCH_40.md`](./REVIEW_BATCH_40.md) (40 questions stratifiées sur les 5 types).
> Les 10 items ci-dessous y sont **inclus**.

Toutes les questions du jeu d'or sont marquées `validated: false`.
Merci de vérifier cet échantillon (fidélité à l'article, formulation, abstention).

Légende : **OK** / **À corriger** / **À reformuler**.

| id | Type | Question | Article(s) attendu(s) | Verdict |
|---|---|---|---|---|
| q08 | direct | Quelle est la durée de la garantie légale de conformité pour un bien neuf ? | L. 217-3 | |
| q11 | direct | Pendant combien de temps un défaut de conformité est-il présumé exister dès la délivrance pour un bien neuf ? | L. 217-7 | |
| q14 | direct | Quel est le délai de rétractation pour un contrat conclu à distance ? | L. 221-18 | |
| q06 | direct | Quel est le délai maximal de délivrance d'un bien lorsqu'aucune date n'a été convenue ? | L. 216-1 | |
| q05 | direct | Qu'est-ce qu'une clause abusive dans un contrat conclu entre un professionnel et un consommateur ? | L. 212-1 | |
| q23 | direct | Le consommateur a-t-il droit à un médiateur de la consommation ? | L. 612-1 | |
| q21 | direct | Combien de temps le prêteur doit-il maintenir les conditions d'une offre de crédit à la consommation ? | L. 312-18 | |
| q18 | direct | Quels contrats sont exclus du droit de rétractation ? | L. 221-28 | |
| u01 | unanswerable | Quel est le montant maximal de l'amende encourue par un bailleur pour un logement indigne au sens du Code de la construction ? | — (hors corpus) | |
| u05 | unanswerable | Quel est le taux de TVA normal applicable aux prestations de restauration sur place en France métropolitaine ? | — (hors corpus) | |

## Checklist de validation

1. La réponse de référence est bien supportée par le(s) article(s) gelé(s) dans `data/corpus/articles.json`.
2. Aucune ambiguïté majeure (plusieurs articles également valides non listés).
3. Les questions « unanswerable » ne sont **pas** répondables avec le sous-corpus figé.
4. Passer `validated: true` question par question dans `questions.json` après revue.
