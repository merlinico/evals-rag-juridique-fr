# Batch de revue humaine (40 questions)

Toutes les questions du jeu d'or restent `validated: false` jusqu'à revue.
Ce batch est **stratifié** sur les 5 `QuestionType` et **inclut** les items
de `SAMPLE_TO_REVIEW.md`.

> **Correctifs (v0.3.3)** : réponses `multi_hop` mh01–mh39 réécrites à la main (lien réel entre articles, sans troncature ni passe-partout) ; questions reformulées lorsque le gabarit ne collait pas au renvoi.

Légende du verdict : **OK** / **À corriger** / **À reformuler**.

## Index

| id | type | topic | verdict |
|---|---|---|---|
| q08 | `direct` | garantie de conformité | |
| q11 | `direct` | présomption de non-conformité | |
| q14 | `direct` | rétractation | |
| q06 | `direct` | délivrance | |
| q05 | `direct` | clauses abusives | |
| q23 | `direct` | médiation | |
| q21 | `direct` | durée de validité offre de crédit | |
| q18 | `direct` | exclusions rétractation | |
| u01 | `unanswerable` | hors corpus (construction) | |
| u05 | `unanswerable` | hors corpus (fiscalité) | |
| mh15 | `multi_hop` | crossref:civil:renvoi | |
| mh28 | `multi_hop` | crossref:travail:renvoi | |
| mh01 | `multi_hop` | crossref:consommation:renvoi | |
| t10 | `temporal` | temporal:civil | |
| t15 | `temporal` | temporal:travail | |
| t01 | `temporal` | temporal:consommation | |
| ac01 | `apparent_contradiction` | retractation vs exclusions | |
| q01 | `direct` | information précontractuelle | |
| q26 | `multi_hop` | territorialité pratiques trompeuses | |
| t02 | `temporal` | temporal:consommation | |
| u03 | `unanswerable` | hors corpus (contrôle auto post-élargissement) | |
| ac02 | `apparent_contradiction` | garantie vs présomption | |
| q02 | `direct` | affichage des prix | |
| mh02 | `multi_hop` | crossref:consommation:renvoi | |
| t03 | `temporal` | temporal:consommation | |
| u04 | `unanswerable` | hors corpus (urbanisme) | |
| ac03 | `apparent_contradiction` | délivrance info vs délai | |
| q03 | `direct` | pratiques déloyales | |
| mh03 | `multi_hop` | crossref:consommation:renvoi | |
| t04 | `temporal` | temporal:consommation | |
| u06 | `unanswerable` | hors corpus (contrôle auto post-élargissement) | |
| ac04 | `apparent_contradiction` | prix vs clause abusive | |
| q04 | `direct` | pratiques trompeuses | |
| mh04 | `multi_hop` | crossref:consommation:renvoi | |
| t05 | `temporal` | temporal:consommation | |
| u07 | `unanswerable` | hors corpus (contrôle auto post-élargissement) | |
| ac05 | `apparent_contradiction` | déloyale champ L.121-5 | |
| q07 | `direct` | transfert des risques | |
| mh05 | `multi_hop` | crossref:consommation:renvoi | |
| t06 | `temporal` | temporal:consommation | |

## Détail pour validation rapide

### 1. `q08` — `direct`

**Question :** Quelle est la durée de la garantie légale de conformité pour un bien neuf ?

**Articles gold :** L. 217-3

**Ids LEGIARTI :** `LEGIARTI000044142579`

**Réponse attendue :** Le vendeur répond des défauts de conformité qui apparaissent dans un délai de deux ans à compter de la délivrance du bien.

**Extraits corpus :**

- **L. 217-3** (`LEGIARTI000044142579`) — Le vendeur délivre un bien conforme au contrat ainsi qu'aux critères énoncés à l'article L. 217-5. Il répond des défauts de conformité existant au moment de la délivrance du bien au sens de l'article L. 216-1, qui apparaissent dans un délai de deux ans à compter de celle-ci. Dans le cas d'un contrat de vente d'un bien…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 2. `q11` — `direct`

**Question :** Pendant combien de temps un défaut de conformité est-il présumé exister dès la délivrance pour un bien neuf ?

**Articles gold :** L. 217-7

**Ids LEGIARTI :** `LEGIARTI000044152587`

**Réponse attendue :** Les défauts apparaissant dans les vingt-quatre mois suivant la délivrance sont présumés exister au moment de la délivrance, sauf preuve contraire. Pour les biens d'occasion, ce délai est de douze mois.

**Extraits corpus :**

- **L. 217-7** (`LEGIARTI000044152587`) — Les défauts de conformité qui apparaissent dans un délai de vingt-quatre mois à compter de la délivrance du bien, y compris du bien comportant des éléments numériques, sont, sauf preuve contraire, présumés exister au moment de la délivrance, à moins que cette présomption ne soit incompatible avec la nature du bien ou…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 3. `q14` — `direct`

**Question :** Quel est le délai de rétractation pour un contrat conclu à distance ?

**Articles gold :** L. 221-18

**Ids LEGIARTI :** `LEGIARTI000032226842`

**Réponse attendue :** Le consommateur dispose de quatorze jours pour se rétracter, sans motiver sa décision, sous réserve des coûts prévus aux articles L. 221-23 à L. 221-25.

**Extraits corpus :**

- **L. 221-18** (`LEGIARTI000032226842`) — Le consommateur dispose d'un délai de quatorze jours pour exercer son droit de rétractation d'un contrat conclu à distance, à la suite d'un démarchage téléphonique ou hors établissement, sans avoir à motiver sa décision ni à supporter d'autres coûts que ceux prévus aux articles L. 221-23 à L. 221-25. Le délai…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 4. `q06` — `direct`

**Question :** Quel est le délai maximal de délivrance d'un bien lorsqu'aucune date n'a été convenue ?

**Articles gold :** L. 216-1

**Ids LEGIARTI :** `LEGIARTI000044142498`

**Réponse attendue :** À défaut d'indication ou d'accord, le professionnel délivre le bien sans retard injustifié et au plus tard trente jours après la conclusion du contrat.

**Extraits corpus :**

- **L. 216-1** (`LEGIARTI000044142498`) — Le professionnel délivre le bien ou fournit le service à la date ou dans le délai indiqué au consommateur, conformément au 3° de l'article L. 111-1, sauf si les parties en conviennent autrement. Pour l'application du présent titre, on entend par délivrance d'un bien, le transfert au consommateur de la possession…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 5. `q05` — `direct`

**Question :** Qu'est-ce qu'une clause abusive dans un contrat conclu entre un professionnel et un consommateur ?

**Articles gold :** L. 212-1

**Ids LEGIARTI :** `LEGIARTI000032890812`

**Réponse attendue :** Sont abusives les clauses qui créent, au détriment du consommateur, un déséquilibre significatif entre les droits et obligations des parties. L'appréciation ne porte ni sur l'objet principal du contrat ni sur l'adéquation du prix.

**Extraits corpus :**

- **L. 212-1** (`LEGIARTI000032890812`) — Dans les contrats conclus entre professionnels et consommateurs, sont abusives les clauses qui ont pour objet ou pour effet de créer, au détriment du consommateur, un déséquilibre significatif entre les droits et obligations des parties au contrat. Sans préjudice des règles d'interprétation prévues aux articles 1188,…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 6. `q23` — `direct`

**Question :** Le consommateur a-t-il droit à un médiateur de la consommation ?

**Articles gold :** L. 612-1

**Ids LEGIARTI :** `LEGIARTI000032224805`

**Réponse attendue :** Oui. Tout consommateur a le droit de recourir gratuitement à un médiateur de la consommation ; le professionnel garantit un recours effectif à un dispositif de médiation.

**Extraits corpus :**

- **L. 612-1** (`LEGIARTI000032224805`) — Tout consommateur a le droit de recourir gratuitement à un médiateur de la consommation en vue de la résolution amiable du litige qui l'oppose à un professionnel. A cet effet, le professionnel garantit au consommateur le recours effectif à un dispositif de médiation de la consommation.Le professionnel peut mettre en…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 7. `q21` — `direct`

**Question :** Combien de temps le prêteur doit-il maintenir les conditions d'une offre de crédit à la consommation ?

**Articles gold :** L. 312-18

**Ids LEGIARTI :** `LEGIARTI000035731428`

**Réponse attendue :** La remise ou l'envoi de l'offre oblige le prêteur à en maintenir les conditions pendant une durée minimale de quinze jours.

**Extraits corpus :**

- **L. 312-18** (`LEGIARTI000035731428`) — L'offre de contrat de crédit est établie sur support papier ou sur un autre support durable. Elle est fournie en autant d'exemplaires que de parties et, le cas échéant, à chacune des cautions. La remise ou l'envoi de l'offre de contrat de crédit à l'emprunteur oblige le prêteur à en maintenir les conditions pendant…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 8. `q18` — `direct`

**Question :** Quels contrats sont exclus du droit de rétractation ?

**Articles gold :** L. 221-28

**Ids LEGIARTI :** `LEGIARTI000044563170`

**Réponse attendue :** L'article L. 221-28 exclut notamment les services pleinement exécutés avec accord exprès, les biens confectionnés selon les spécifications du consommateur, les biens périssables, et d'autres cas limitativement énumérés.

**Extraits corpus :**

- **L. 221-28** (`LEGIARTI000044563170`) — Le droit de rétractation ne peut être exercé pour les contrats : 1° De fourniture de services pleinement exécutés avant la fin du délai de rétractation et, si le contrat soumet le consommateur à une obligation de payer, dont l'exécution a commencé avec son accord préalable et exprès et avec la reconnaissance par lui…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 9. `u01` — `unanswerable`

**Question :** Quel est le montant maximal de l'amende encourue par un bailleur pour un logement indigne au sens du Code de la construction ?

**Articles gold :** — (unanswerable / hors corpus)

**Réponse attendue :** je ne sais pas

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 10. `u05` — `unanswerable`

**Question :** Quel est le taux de TVA normal applicable aux prestations de restauration sur place en France métropolitaine ?

**Articles gold :** — (unanswerable / hors corpus)

**Réponse attendue :** je ne sais pas

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 11. `mh15` — `multi_hop`

**Question :** Avant d'exécuter un testament olographe ou mystique, quelles vérifications le notaire doit-il faire au regard de l'article 1006 du Code civil, selon l'article 1007 ?

**Articles gold :** 1007, 1006

**Ids LEGIARTI :** `LEGIARTI000039368517, LEGIARTI000006434591`

**Réponse attendue :** L'article 1007 impose, avant toute exécution, le dépôt du testament olographe ou mystique entre les mains d'un notaire, qui dresse procès-verbal d'ouverture et d'état du testament. Dans le cas prévu à l'article 1006 — absence d'héritiers réservataires, le légataire universel étant alors saisi de plein droit par la mort du testateur sans avoir à demander la délivrance — le notaire vérifie le caractère universel de la vocation et l'absence d'héritiers réservataires, porte ces vérifications sur le procès-verbal, et tout intéressé peut s'opposer dans le mois suivant la réception des pièces au greffe, auquel cas le légataire se fera envoyer en possession.

**Extraits corpus :**

- **1007** (`LEGIARTI000039368517`) — Tout testament olographe ou mystique sera, avant d'être mis à exécution, déposé entre les mains d'un notaire. Le testament sera ouvert s'il est cacheté. Le notaire dressera sur-le-champ procès-verbal de l'ouverture et de l'état du testament, en précisant les circonstances du dépôt. Dans le cas prévu à l'article 1006,…
- **1006** (`LEGIARTI000006434591`) — Lorsqu'au décès du testateur il n'y aura pas d'héritiers auxquels une quotité de ses biens soit réservée par la loi, le légataire universel sera saisi de plein droit par la mort du testateur, sans être tenu de demander la délivrance.

*Notes :* CrossRef réel renvoi LEGIARTI000039368517→LEGIARTI000006434591 (corpus codes-v0.2-2025-07-13) | quality-pass v0.3.2 | quality-pass v0.3.2 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 12. `mh28` — `multi_hop`

**Question :** Les titulaires d'un contrat initiative-emploi comptent-ils dans les effectifs de l'entreprise, et à quelle aide l'article L. 1111-3 du Code du travail renvoie-t-il (article L. 5134-72) ?

**Articles gold :** L. 1111-3, L. 5134-72

**Ids LEGIARTI :** `LEGIARTI000031565369, LEGIARTI000026549836`

**Réponse attendue :** L'article L. 1111-3 exclut du calcul des effectifs, notamment, les titulaires d'un contrat initiative-emploi pendant la durée d'attribution de l'aide financière mentionnée à l'article L. 5134-72 (ainsi que d'autres catégories : apprentis, contrats d'accompagnement dans l'emploi, contrats de professionnalisation, sous les réserves du texte). L'article L. 5134-72 précise que cette aide à l'insertion professionnelle au titre d'un contrat initiative-emploi peut être modulée selon la catégorie et le secteur d'activité de l'employeur, les actions d'accompagnement et d'insertion durable, les conditions économiques locales et les difficultés d'accès à l'emploi antérieurement rencontrées par le salarié.

**Extraits corpus :**

- **L. 1111-3** (`LEGIARTI000031565369`) — Ne sont pas pris en compte dans le calcul des effectifs de l'entreprise : 1° Les apprentis ; 2° Les titulaires d'un contrat initiative-emploi, pendant la durée d'attribution de l'aide financière mentionnée à l'article L. 5134-72 ; 3° (Abrogé) ; 4° Les titulaires d'un contrat d'accompagnement dans l'emploi pendant la…
- **L. 5134-72** (`LEGIARTI000026549836`) — L'aide à l'insertion professionnelle attribuée au titre d'un contrat initiative-emploi peut être modulée en fonction : 1° De la catégorie et du secteur d'activité de l'employeur ; 2° Des actions prévues en matière d'accompagnement professionnel et des actions visant à favoriser l'insertion durable du salarié ; 3° Des…

*Notes :* CrossRef réel renvoi LEGIARTI000031565369→LEGIARTI000026549836 (corpus codes-v0.2-2025-07-13) | quality-pass v0.3.2 | quality-pass v0.3.2 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 13. `mh01` — `multi_hop`

**Question :** Un professionnel a obtenu une prise de position formelle de l'administration sur ses modalités d'information des prix (article L. 112-5 du Code de la consommation) : dans quels cas cette garantie prend-elle fin selon l'article L. 112-6 ?

**Articles gold :** L. 112-6, L. 112-5

**Ids LEGIARTI :** `LEGIARTI000032227321, LEGIARTI000032227323`

**Réponse attendue :** L'article L. 112-5 permet à tout professionnel de demander à l'autorité administrative chargée de la concurrence et de la consommation de prendre formellement position sur la conformité, aux articles L. 112-1 à L. 112-4 et à leurs mesures réglementaires, des modalités d'information sur les prix de vente au consommateur qu'il envisage ; cette prise de position vise à le prémunir d'un changement d'appréciation exposant aux sanctions des articles L. 131-5 et L. 131-6. L'article L. 112-6 fixe la fin de cette garantie : lorsque la situation du professionnel n'est plus identique à celle présentée dans la demande, lorsqu'une modification législative ou réglementaire affecte la validité de la garantie, ou à compter du jour où l'autorité notifie au professionnel la modification de son appréciation, après information préalable.

**Extraits corpus :**

- **L. 112-6** (`LEGIARTI000032227321`) — La garantie mentionnée à l'article L. 112-5 prend fin : 1° A la date à laquelle la situation du professionnel n'est plus identique à celle présentée dans la demande ; les modalités de constatation de cette situation et d'information du professionnel sont précisées par décret en Conseil d'Etat ; 2° A la date à laquelle…
- **L. 112-5** (`LEGIARTI000032227323`) — Tout professionnel peut demander à l'autorité administrative chargée de la concurrence et de la consommation de prendre formellement position sur la conformité aux articles L. 112-1 à L. 112-4 et aux mesures réglementaires prises pour leur application, des modalités de l'information sur les prix de vente au…

*Notes :* CrossRef réel renvoi LEGIARTI000032227321→LEGIARTI000032227323 (corpus codes-v0.2-2025-07-13) | quality-pass v0.3.2 | quality-pass v0.3.2 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 14. `t10` — `temporal`

**Question :** Que disait l'article 2423 du Code civil en vigueur au 2012-01-01 ?

**as_of :** `2012-01-01`

**Articles gold :** 2423

**Ids LEGIARTI :** `LEGIARTI000044072020`

**Réponse attendue :** Au 2012-01-01, l'article 2423 prévoyait que l'hypothèque est toujours consentie, pour le capital, à hauteur d'une somme déterminée que l'acte notarié mentionne à peine de nullité. Le cas échéant, les parties évaluent à cette fin les rentes, prestations et droits indéterminés, éventuels ou conditionnels. Par rapport à la version aujourd'hui en vigueur, là où le texte prévoyait que l'hypothèque est toujours consentie, pour le capital, à hauteur d'une somme déterminée que l'acte notarié mentionne à peine de nullité, la version courante dispose que l'inscription des hypothèques est opérée par le service chargé de la publicité foncière sur le dépôt de deux bordereaux datés.

**Extraits corpus :**

- **2423** (`LEGIARTI000044072020`) — L'inscription des hypothèques est opérée par le service chargé de la publicité foncière sur le dépôt de deux bordereaux datés, signés et certifiés conformes entre eux par le signataire du certificat d'identité prévu aux articles 5 et 6 du décret du 4 janvier 1955 ; un décret en Conseil d'Etat détermine les conditions…

*Notes :* version_at(2012-01-01)=LEGIARTI000006449673 ≠ tip LEGIARTI000044072020; debut=2006-03-24 fin=2022-01-01 | quality-pass v0.3.2 | quality-pass v0.3.2

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 15. `t15` — `temporal`

**Question :** Que disait l'article L. 6123-5 du Code du travail en vigueur au 2023-01-01 ?

**as_of :** `2023-01-01`

**Articles gold :** L. 6123-5

**Ids LEGIARTI :** `LEGIARTI000048700924`

**Réponse attendue :** Au 2023-01-01, l'article L. 6123-5 prévoyait que France compétences est une institution nationale publique dotée de la personnalité morale et de l'autonomie financière. Par rapport à la version aujourd'hui en vigueur, la version courante modifie le passage « la formation des demandeurs d'emploi, dans la limite d'un montant fixé chaque année par le conseil d'administration de France compétences » (auparavant : « la formation des demandeurs d'emploi ; c) Aux opérateurs de compétences »).

**Extraits corpus :**

- **L. 6123-5** (`LEGIARTI000048700924`) — France compétences est une institution nationale publique dotée de la personnalité morale et de l'autonomie financière. Elle a pour mission : 1° De verser aux opérateurs de compétences mentionnés à l'article L. 6332-1 des fonds pour un financement complémentaire des contrats d'apprentissage et de professionnalisation…

*Notes :* version_at(2023-01-01)=LEGIARTI000045178424 ≠ tip LEGIARTI000048700924; debut=2022-09-01 fin=2023-04-16 | quality-pass v0.3.2 | quality-pass v0.3.2

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 16. `t01` — `temporal`

**Question :** Au 2012-01-01, quelle règle résultait de l'article L. 121-4 du Code de la consommation ?

**as_of :** `2012-01-01`

**Articles gold :** L. 121-4

**Ids LEGIARTI :** `LEGIARTI000044563107`

**Réponse attendue :** Au 2012-01-01, l'article L. 121-4 prévoyait qu'en cas de condamnation, le tribunal ordonne la publication du jugement. Il peut, de plus, ordonner la diffusion, aux frais du condamné, d'une ou de plusieurs annonces rectificatives. Par rapport à la version aujourd'hui en vigueur, là où le texte prévoyait que en cas de condamnation, le tribunal ordonne la publication du jugement, la version courante dispose que sont réputées trompeuses, au sens des articles L. 121-2 et L. 121-3, les pratiques commerciales qui ont pour objet : 1° Pour un professionnel, de se prétendre signataire d'un code de conduite alors qu'il ne l'est pas.

**Extraits corpus :**

- **L. 121-4** (`LEGIARTI000044563107`) — Sont réputées trompeuses, au sens des articles L. 121-2 et L. 121-3, les pratiques commerciales qui ont pour objet : 1° Pour un professionnel, de se prétendre signataire d'un code de conduite alors qu'il ne l'est pas ; 2° D'afficher un certificat, un label de qualité ou un équivalent sans avoir obtenu l'autorisation…

*Notes :* version_at(2012-01-01)=LEGIARTI000018048136 ≠ tip LEGIARTI000044563107; debut=2008-01-05 fin=2014-03-19 | quality-pass v0.3.2 | quality-pass v0.3.2

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 17. `ac01` — `apparent_contradiction`

**Question :** Le consommateur dispose de quatorze jours pour se rétracter (L. 221-18), mais certains contrats semblent totalement exclus : y a-t-il contradiction avec L. 221-28 ?

**Articles gold :** L. 221-18, L. 221-28

**Ids LEGIARTI :** `LEGIARTI000032226842, LEGIARTI000044563170`

**Réponse attendue :** Non : L. 221-18 pose le principe ; L. 221-28 énumère des exclusions légales (services pleinement exécutés avec accord, biens personnalisés, etc.). Les deux textes s'articulent, ils ne se contredisent pas.

**Extraits corpus :**

- **L. 221-18** (`LEGIARTI000032226842`) — Le consommateur dispose d'un délai de quatorze jours pour exercer son droit de rétractation d'un contrat conclu à distance, à la suite d'un démarchage téléphonique ou hors établissement, sans avoir à motiver sa décision ni à supporter d'autres coûts que ceux prévus aux articles L. 221-23 à L. 221-25. Le délai…
- **L. 221-28** (`LEGIARTI000044563170`) — Le droit de rétractation ne peut être exercé pour les contrats : 1° De fourniture de services pleinement exécutés avant la fin du délai de rétractation et, si le contrat soumet le consommateur à une obligation de payer, dont l'exécution a commencé avec son accord préalable et exprès et avec la reconnaissance par lui…

*Notes :* piège d'apparente contradiction ; les textes s'articulent

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 18. `q01` — `direct`

**Question :** Quelles informations essentielles le professionnel doit-il communiquer au consommateur avant la conclusion d'un contrat à titre onéreux ?

**Articles gold :** L. 111-1

**Ids LEGIARTI :** `LEGIARTI000044142438`

**Réponse attendue :** Avant d'être lié, le consommateur doit recevoir de manière lisible et compréhensible notamment les caractéristiques essentielles du bien ou service, le prix, la date ou le délai de délivrance, et les autres informations prévues à l'article L. 111-1.

**Extraits corpus :**

- **L. 111-1** (`LEGIARTI000044142438`) — Avant que le consommateur ne soit lié par un contrat à titre onéreux, le professionnel communique au consommateur, de manière lisible et compréhensible, les informations suivantes : 1° Les caractéristiques essentielles du bien ou du service, ainsi que celles du service numérique ou du contenu numérique, compte tenu de…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 19. `q26` — `multi_hop`

**Question :** Les pratiques commerciales trompeuses sont-elles interdites même si elles n'ont produit leurs effets qu'en France ?

**Articles gold :** L. 132-1, L. 121-2

**Ids LEGIARTI :** `LEGIARTI000032227122, LEGIARTI000044563114`

**Réponse attendue :** Oui. Le délit de pratique commerciale trompeuse est constitué dès lors que la pratique est mise en œuvre ou produit ses effets en France (L. 132-1), les pratiques trompeuses étant définies notamment aux articles L. 121-2 et suivants.

**Extraits corpus :**

- **L. 132-1** (`LEGIARTI000032227122`) — Le délit de pratique commerciale trompeuse défini aux articles L. 121-2 à L. 121-4 est constitué dès lors que la pratique est mise en œuvre ou qu'elle produit ses effets en France.
- **L. 121-2** (`LEGIARTI000044563114`) — Une pratique commerciale est trompeuse si elle est commise dans l'une des circonstances suivantes : 1° Lorsqu'elle crée une confusion avec un autre bien ou service, une marque, un nom commercial ou un autre signe distinctif d'un concurrent ; 2° Lorsqu'elle repose sur des allégations, indications ou présentations…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 20. `t02` — `temporal`

**Question :** Que disait l'article L. 111-4 du Code de la consommation en vigueur au 2015-06-01 ?

**as_of :** `2015-06-01`

**Articles gold :** L. 111-4

**Ids LEGIARTI :** `LEGIARTI000044330854`

**Réponse attendue :** Au 2015-06-01, l'article L. 111-4 prévoyait que I.-En cas de litige relatif à l'application des articles L. 111-1 à L. 111-3, il appartient au professionnel de prouver qu'il a exécuté ses obligations. Par rapport à la version aujourd'hui en vigueur, là où le texte prévoyait que I.-En cas de litige relatif à l'application des articles L. 111-1 à L. 111-3, il appartient au professionnel de prouver qu'il a exécuté ses obligations, la version courante dispose que le fabricant ou l'importateur de biens meubles informe le vendeur professionnel de la disponibilité ou de la non-disponibilité des pièces détachées indispensables à l'utilisation des biens concernés et, le cas échéant.

**Extraits corpus :**

- **L. 111-4** (`LEGIARTI000044330854`) — Le fabricant ou l'importateur de biens meubles informe le vendeur professionnel de la disponibilité ou de la non-disponibilité des pièces détachées indispensables à l'utilisation des biens concernés et, le cas échéant, de la période pendant laquelle ou de la date jusqu'à laquelle ces pièces sont disponibles sur le…

*Notes :* quality-pass v0.3.2 replace L. 771-2→L. 111-4; version_at(2015-06-01)=LEGIARTI000028742286 | quality-pass v0.3.2

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 21. `u03` — `unanswerable`

**Question :** Quel est le quantum de la peine d'emprisonnement encourue pour un assassinat selon le Code pénal ?

**Articles gold :** — (unanswerable / hors corpus)

**Réponse attendue :** je ne sais pas

*Notes :* Remplacé car l'ancienne formulation était désormais couverte

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 22. `ac02` — `apparent_contradiction`

**Question :** La garantie de conformité dure deux ans (L. 217-3) alors que la présomption ne dure que douze mois pour un bien d'occasion (L. 217-7) : la garantie est-elle réduite à un an ?

**Articles gold :** L. 217-3, L. 217-7

**Ids LEGIARTI :** `LEGIARTI000044142579, LEGIARTI000044152587`

**Réponse attendue :** Non : le délai de garantie de deux ans (L. 217-3) n'est pas confondu avec le délai de présomption d'existence du défaut (vingt-quatre mois / douze mois pour l'occasion, L. 217-7).

**Extraits corpus :**

- **L. 217-3** (`LEGIARTI000044142579`) — Le vendeur délivre un bien conforme au contrat ainsi qu'aux critères énoncés à l'article L. 217-5. Il répond des défauts de conformité existant au moment de la délivrance du bien au sens de l'article L. 216-1, qui apparaissent dans un délai de deux ans à compter de celle-ci. Dans le cas d'un contrat de vente d'un bien…
- **L. 217-7** (`LEGIARTI000044152587`) — Les défauts de conformité qui apparaissent dans un délai de vingt-quatre mois à compter de la délivrance du bien, y compris du bien comportant des éléments numériques, sont, sauf preuve contraire, présumés exister au moment de la délivrance, à moins que cette présomption ne soit incompatible avec la nature du bien ou…

*Notes :* piège d'apparente contradiction ; les textes s'articulent

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 23. `q02` — `direct`

**Question :** Comment le vendeur doit-il informer le consommateur sur les prix ?

**Articles gold :** L. 112-1

**Ids LEGIARTI :** `LEGIARTI000032227331`

**Réponse attendue :** Tout vendeur ou prestataire informe le consommateur sur les prix et conditions particulières par marquage, étiquetage, affichage ou tout autre procédé approprié, selon des modalités fixées par arrêté.

**Extraits corpus :**

- **L. 112-1** (`LEGIARTI000032227331`) — Tout vendeur de produit ou tout prestataire de services informe le consommateur, par voie de marquage, d'étiquetage, d'affichage ou par tout autre procédé approprié, sur les prix et les conditions particulières de la vente et de l'exécution des services, selon des modalités fixées par arrêtés du ministre chargé de…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 24. `mh02` — `multi_hop`

**Question :** Quelle sanction administrative frappe le manquement à l'obligation d'information sur les pièces détachées de l'article L. 111-4, et en quoi consiste cette obligation (articles L. 131-2 et L. 111-4 du Code de la consommation) ?

**Articles gold :** L. 131-2, L. 111-4

**Ids LEGIARTI :** `LEGIARTI000032227140, LEGIARTI000044330854`

**Réponse attendue :** L'article L. 111-4 oblige le fabricant ou l'importateur de biens meubles à informer le vendeur professionnel de la disponibilité ou de la non-disponibilité des pièces détachées indispensables à l'utilisation des biens et, le cas échéant, de la période ou de la date jusqu'à laquelle ces pièces sont disponibles ; ces informations sont ensuite délivrées au consommateur avant la conclusion du contrat. L'article L. 131-2 sanctionne tout manquement à cette obligation d'informer sur la durée de disponibilité des pièces détachées d'une amende administrative d'au plus 3 000 euros pour une personne physique et 15 000 euros pour une personne morale, prononcée dans les conditions du chapitre II du titre II du livre V.

**Extraits corpus :**

- **L. 131-2** (`LEGIARTI000032227140`) — Tout manquement à l'obligation d'informer sur la durée de disponibilité des pièces détachées mentionnée à l'article L. 111-4 est passible d'une amende administrative dont le montant ne peut excéder 3 000 euros pour une personne physique et 15 000 euros pour une personne morale. Cette amende est prononcée dans les…
- **L. 111-4** (`LEGIARTI000044330854`) — Le fabricant ou l'importateur de biens meubles informe le vendeur professionnel de la disponibilité ou de la non-disponibilité des pièces détachées indispensables à l'utilisation des biens concernés et, le cas échéant, de la période pendant laquelle ou de la date jusqu'à laquelle ces pièces sont disponibles sur le…

*Notes :* CrossRef réel renvoi LEGIARTI000032227140→LEGIARTI000044330854 (corpus codes-v0.2-2025-07-13) | quality-pass v0.3.2 | quality-pass v0.3.2 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 25. `t03` — `temporal`

**Question :** Selon le droit applicable le 2016-10-01, que prévoyait l'article L. 412-1 (Code de la consommation) ?

**as_of :** `2016-10-01`

**Articles gold :** L. 412-1

**Ids LEGIARTI :** `LEGIARTI000041985019`

**Réponse attendue :** Au 2016-10-01, l'article L. 412-1 prévoyait que des décrets en Conseil d'État déterminent les règles auxquelles doivent satisfaire les produits et services, notamment en ce qui concerne :1° La fabrication, l'importation, la vente, la mise en vente, l'exposition. Par rapport à la version aujourd'hui en vigueur, là où le texte prévoyait que des décrets en Conseil d'État déterminent les règles auxquelles doivent satisfaire les produits et services, notamment en ce qui concerne :1° La fabrication, la version courante dispose que I.-Des décrets en Conseil d'État définissent les règles auxquelles doivent satisfaire les marchandises.

**Extraits corpus :**

- **L. 412-1** (`LEGIARTI000041985019`) — I.-Des décrets en Conseil d'Etat définissent les règles auxquelles doivent satisfaire les marchandises. Ils déterminent notamment : 1° Les conditions dans lesquelles l'exportation, l'offre, la vente, la distribution à titre gratuit, la détention, l'étiquetage, le conditionnement ou le mode d'utilisation des…

*Notes :* version_at(2016-10-01)=LEGIARTI000032225492 ≠ tip LEGIARTI000041985019; debut=2016-07-01 fin=2017-02-23 | quality-pass v0.3.2 | quality-pass v0.3.2

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 26. `u04` — `unanswerable`

**Question :** Dans quel délai un permis de construire tacite est-il acquis en zone urbaine ?

**Articles gold :** — (unanswerable / hors corpus)

**Réponse attendue :** je ne sais pas

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 27. `ac03` — `apparent_contradiction`

**Question :** L. 216-1 impose une délivrance sous trente jours à défaut d'accord, mais L. 111-1 parle d'indiquer une date ou un délai : le professionnel peut-il ignorer toute date ?

**Articles gold :** L. 216-1, L. 111-1

**Ids LEGIARTI :** `LEGIARTI000044142498, LEGIARTI000044142438`

**Réponse attendue :** Non : L. 111-1 impose d'informer sur la date ou le délai ; L. 216-1 fixe ensuite la règle subsidiaire (sans retard injustifié, au plus tard trente jours) si rien n'a été convenu.

**Extraits corpus :**

- **L. 216-1** (`LEGIARTI000044142498`) — Le professionnel délivre le bien ou fournit le service à la date ou dans le délai indiqué au consommateur, conformément au 3° de l'article L. 111-1, sauf si les parties en conviennent autrement. Pour l'application du présent titre, on entend par délivrance d'un bien, le transfert au consommateur de la possession…
- **L. 111-1** (`LEGIARTI000044142438`) — Avant que le consommateur ne soit lié par un contrat à titre onéreux, le professionnel communique au consommateur, de manière lisible et compréhensible, les informations suivantes : 1° Les caractéristiques essentielles du bien ou du service, ainsi que celles du service numérique ou du contenu numérique, compte tenu de…

*Notes :* piège d'apparente contradiction ; les textes s'articulent

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 28. `q03` — `direct`

**Question :** Quand une pratique commerciale est-elle considérée comme déloyale ?

**Articles gold :** L. 121-1

**Ids LEGIARTI :** `LEGIARTI000032227301`

**Réponse attendue :** Une pratique est déloyale si elle est contraire à la diligence professionnelle et altère ou est susceptible d'altérer de manière substantielle le comportement économique du consommateur normalement informé et raisonnablement attentif.

**Extraits corpus :**

- **L. 121-1** (`LEGIARTI000032227301`) — Les pratiques commerciales déloyales sont interdites. Une pratique commerciale est déloyale lorsqu'elle est contraire aux exigences de la diligence professionnelle et qu'elle altère ou est susceptible d'altérer de manière substantielle le comportement économique du consommateur normalement informé et raisonnablement…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 29. `mh03` — `multi_hop`

**Question :** Quelle est l'obligation d'information de l'article L. 111-6 du Code de la consommation sur les mises à jour logicielles, et quelle amende l'article L. 131-3-1 prévoit-il en cas de manquement ?

**Articles gold :** L. 131-3-1, L. 111-6

**Ids LEGIARTI :** `LEGIARTI000044526142, LEGIARTI000044564977`

**Réponse attendue :** L'article L. 111-6 impose au producteur de biens comportant des éléments numériques d'informer le vendeur professionnel de la durée pendant laquelle les mises à jour logicielles qu'il fournit restent compatibles avec les fonctionnalités du bien ; le vendeur met ces informations à la disposition du consommateur, et le producteur informe aussi le consommateur des caractéristiques essentielles de chaque mise à jour. L'article L. 131-3-1 punit le manquement à cette obligation d'information d'une amende administrative plafonnée à 3 000 euros pour une personne physique et 15 000 euros pour une personne morale.

**Extraits corpus :**

- **L. 131-3-1** (`LEGIARTI000044526142`) — Tout manquement à l'obligation d'information mentionnée à l'article L. 111-6 est passible d'une amende administrative dont le montant ne peut excéder 3 000 euros pour une personne physique et 15 000 euros pour une personne morale. Cette amende est prononcée dans les conditions prévues au chapitre II du titre II du…
- **L. 111-6** (`LEGIARTI000044564977`) — Le producteur de biens comportant des éléments numériques informe le vendeur professionnel de la durée au cours de laquelle les mises à jour logicielles, que le producteur fournit, restent compatibles avec les fonctionnalités du bien. Le vendeur met ces informations à la disposition du consommateur. Le producteur…

*Notes :* CrossRef réel renvoi LEGIARTI000044526142→LEGIARTI000044564977 (corpus codes-v0.2-2025-07-13) | quality-pass v0.3.2 | quality-pass v0.3.2 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 30. `t04` — `temporal`

**Question :** Que disait l'article L. 511-7 du Code de la consommation en vigueur au 2023-01-01 ?

**as_of :** `2023-01-01`

**Articles gold :** L. 511-7

**Ids LEGIARTI :** `LEGIARTI000051558799`

**Réponse attendue :** Au 2023-01-01, l'article L. 511-7 prévoyait que les agents sont habilités à rechercher et à constater les infractions ou les manquements aux dispositions : 1° Du règlement (CE) n° 1371/2007 du Parlement européen et du Conseil du 23 octobre 2007 sur les droits et obligations des voyageurs ferroviaires. Par rapport à la version aujourd'hui en vigueur, la version courante modifie le passage « aux dispositions : 1° Du règlement (UE) 2021/782 du Parlement européen et du Conseil du 29 avril 2021 sur les droits et obligations des voyageurs ferroviaires » (auparavant : « aux dispositions : 1° Du règlement (CE) n° 1371/2007 du Parlement européen et du Conseil du 23 octobre 2007 sur les droits et obligations »).

**Extraits corpus :**

- **L. 511-7** (`LEGIARTI000051558799`) — Les agents sont habilités à rechercher et à constater les infractions ou les manquements aux dispositions : 1° Du règlement (UE) 2021/782 du Parlement européen et du Conseil du 29 avril 2021 sur les droits et obligations des voyageurs ferroviaires ; 2° De l'article 23 du règlement (CE) n° 1008/2008 du Parlement…

*Notes :* version_at(2023-01-01)=LEGIARTI000043984101 ≠ tip LEGIARTI000051558799; debut=2023-01-01 fin=2023-06-07 | quality-pass v0.3.2 | quality-pass v0.3.2

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 31. `u06` — `unanswerable`

**Question :** Quel est le quantum de la peine d'emprisonnement encourue pour un assassinat selon le Code pénal ?

**Articles gold :** — (unanswerable / hors corpus)

**Réponse attendue :** je ne sais pas

*Notes :* Remplacé car l'ancienne formulation était désormais couverte

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 32. `ac04` — `apparent_contradiction`

**Question :** Les clauses abusives sont réputées non écrites (L. 241-1) alors que L. 212-1 dit qu'on n'apprécie pas l'objet principal ni l'adéquation du prix : le prix peut-il être déclaré abusif ?

**Articles gold :** L. 212-1, L. 241-1

**Ids LEGIARTI :** `LEGIARTI000032890812, LEGIARTI000032226417`

**Réponse attendue :** L'appréciation du caractère abusif ne porte ni sur l'objet principal ni sur l'adéquation prix/service (L. 212-1) ; la sanction du réputé non écrit (L. 241-1) s'applique aux clauses abusives ainsi définies, pas au prix lui-même en tant qu'adéquation.

**Extraits corpus :**

- **L. 212-1** (`LEGIARTI000032890812`) — Dans les contrats conclus entre professionnels et consommateurs, sont abusives les clauses qui ont pour objet ou pour effet de créer, au détriment du consommateur, un déséquilibre significatif entre les droits et obligations des parties au contrat. Sans préjudice des règles d'interprétation prévues aux articles 1188,…
- **L. 241-1** (`LEGIARTI000032226417`) — Les clauses abusives sont réputées non écrites.Le contrat reste applicable dans toutes ses dispositions autres que celles jugées abusives s'il peut subsister sans ces clauses.Les dispositions du présent article sont d'ordre public.

*Notes :* piège d'apparente contradiction ; les textes s'articulent

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 33. `q04` — `direct`

**Question :** Dans quels cas une pratique commerciale est-elle trompeuse ?

**Articles gold :** L. 121-2

**Ids LEGIARTI :** `LEGIARTI000044563114`

**Réponse attendue :** Elle est trompeuse notamment si elle crée une confusion avec un concurrent ou repose sur des allégations fausses ou trompeuses portant sur l'existence, les caractéristiques essentielles, le prix ou d'autres éléments du bien ou service.

**Extraits corpus :**

- **L. 121-2** (`LEGIARTI000044563114`) — Une pratique commerciale est trompeuse si elle est commise dans l'une des circonstances suivantes : 1° Lorsqu'elle crée une confusion avec un autre bien ou service, une marque, un nom commercial ou un autre signe distinctif d'un concurrent ; 2° Lorsqu'elle repose sur des allégations, indications ou présentations…

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 34. `mh04` — `multi_hop`

**Question :** En cas de pratique commerciale agressive suivie de la conclusion d'un contrat, comment l'article L. 132-11-1 du Code de la consommation aggrave-t-il la peine d'emprisonnement de l'article L. 132-11 ?

**Articles gold :** L. 132-11-1, L. 132-11

**Ids LEGIARTI :** `LEGIARTI000046190610, LEGIARTI000037556685`

**Réponse attendue :** L'article L. 132-11 punit les pratiques commerciales agressives mentionnées aux articles L. 121-6 et L. 121-7 d'un emprisonnement de deux ans et d'une amende de 300 000 euros (pouvant être portée à 10 % du chiffre d'affaires moyen annuel). Lorsque ces pratiques ont été suivies de la conclusion d'un ou de plusieurs contrats, l'article L. 132-11-1 porte la peine d'emprisonnement prévue à l'article L. 132-11 à trois ans.

**Extraits corpus :**

- **L. 132-11-1** (`LEGIARTI000046190610`) — Lorsque les pratiques commerciales agressives mentionnées aux articles L. 121-6 et L. 121-7 ont été suivies de la conclusion d'un ou de plusieurs contrats, la peine d'emprisonnement prévue à l'article L. 132-11 est portée à trois ans.
- **L. 132-11** (`LEGIARTI000037556685`) — Les pratiques commerciales agressives mentionnées aux articles L. 121-6 et L. 121-7 sont punies d'un emprisonnement de deux ans et d'une amende de 300 000 euros. Le montant de l'amende peut être porté, de manière proportionnée aux avantages tirés du délit, à 10 % du chiffre d'affaires moyen annuel, calculé sur les…

*Notes :* CrossRef réel renvoi LEGIARTI000046190610→LEGIARTI000037556685 (corpus codes-v0.2-2025-07-13) | quality-pass v0.3.2 | quality-pass v0.3.2 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 35. `t05` — `temporal`

**Question :** Au 2012-01-01, quelle règle résultait de l'article L. 311-1 du Code de la consommation ?

**as_of :** `2012-01-01`

**Articles gold :** L. 311-1

**Ids LEGIARTI :** `LEGIARTI000034072668`

**Réponse attendue :** Au 2012-01-01, l'article L. 311-1 prévoyait qu'au sens du présent chapitre, sont considérés comme : 1° Prêteur, toute personne qui consent ou s'engage à consentir un crédit mentionné. Par rapport à la version aujourd'hui en vigueur, là où le texte prévoyait que au sens du présent chapitre, sont considérés comme : 1° Prêteur, toute personne qui consent ou s'engage à consentir un crédit mentionné, la version courante dispose que pour l'application des dispositions du présent titre, sont considérés comme : 1° Prêteur, toute personne qui consent ou s'engage à consentir un crédit mentionné au présent titre dans le cadre de l'exercice de ses activités commerciales ou professionnelles.

**Extraits corpus :**

- **L. 311-1** (`LEGIARTI000034072668`) — Pour l'application des dispositions du présent titre, sont considérés comme : 1° Prêteur, toute personne qui consent ou s'engage à consentir un crédit mentionné au présent titre dans le cadre de l'exercice de ses activités commerciales ou professionnelles ; 2° Emprunteur ou consommateur, toute personne physique qui…

*Notes :* version_at(2012-01-01)=LEGIARTI000022431920 ≠ tip LEGIARTI000034072668; debut=2011-05-01 fin=2016-07-01 | quality-pass v0.3.2 | quality-pass v0.3.2

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 36. `u07` — `unanswerable`

**Question :** Dans quel délai un recours pour excès de pouvoir doit-il être formé contre une décision administrative ?

**Articles gold :** — (unanswerable / hors corpus)

**Réponse attendue :** je ne sais pas

*Notes :* Remplacé car l'ancienne formulation était désormais couverte

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 37. `ac05` — `apparent_contradiction`

**Question :** L. 121-1 interdit les pratiques commerciales déloyales à l'égard des consommateurs, tandis que L. 121-5 étend L. 121-2 à L. 121-4 aux pratiques qui visent les professionnels et les non-professionnels : y a-t-il contradiction sur le champ d'application ?

**Articles gold :** L. 121-1, L. 121-5

**Ids LEGIARTI :** `LEGIARTI000032227301, LEGIARTI000034072564`

**Réponse attendue :** Non : L. 121-1 définit et interdit les pratiques déloyales visant le consommateur ; L. 121-5 ne requalifie pas toute pratique conforme à L. 121-2 à L. 121-4 en pratique déloyale, il étend seulement le régime des articles L. 121-2 à L. 121-4 aux pratiques qui visent les professionnels et les non-professionnels. Les deux textes ont des champs distincts et s'articulent.

**Extraits corpus :**

- **L. 121-1** (`LEGIARTI000032227301`) — Les pratiques commerciales déloyales sont interdites. Une pratique commerciale est déloyale lorsqu'elle est contraire aux exigences de la diligence professionnelle et qu'elle altère ou est susceptible d'altérer de manière substantielle le comportement économique du consommateur normalement informé et raisonnablement…
- **L. 121-5** (`LEGIARTI000034072564`) — Les dispositions des articles L. 121-2 à L. 121-4 sont également applicables aux pratiques qui visent les professionnels et les non-professionnels.

*Notes :* Corrigé : L. 121-5 = extension aux professionnels / non-professionnels

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 38. `q07` — `direct`

**Question :** À quel moment le risque de perte ou d'endommagement du bien est-il transféré au consommateur ?

**Articles gold :** L. 216-2

**Ids LEGIARTI :** `LEGIARTI000044142491`

**Réponse attendue :** Le risque est transféré au consommateur lorsqu'il prend physiquement possession du bien, ou lorsqu'un tiers qu'il a désigné le fait.

**Extraits corpus :**

- **L. 216-2** (`LEGIARTI000044142491`) — Tout risque de perte ou d'endommagement du bien est transféré au consommateur au moment où ce dernier ou un tiers désigné par lui prend physiquement possession de ces biens.

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 39. `mh05` — `multi_hop`

**Question :** Comment l'article L. 132-11-2 du Code de la consommation aggrave-t-il la peine d'emprisonnement de l'article L. 132-11 lorsque la pratique commerciale agressive est commise en bande organisée ?

**Articles gold :** L. 132-11-2, L. 132-11

**Ids LEGIARTI :** `LEGIARTI000046190612, LEGIARTI000037556685`

**Réponse attendue :** L'article L. 132-11 fixe la peine de base des pratiques commerciales agressives des articles L. 121-6 et L. 121-7 à deux ans d'emprisonnement et 300 000 euros d'amende. L'article L. 132-11-2 dispose que, lorsque ces pratiques ont été commises en bande organisée, la peine d'emprisonnement prévue à l'article L. 132-11 est portée à sept ans.

**Extraits corpus :**

- **L. 132-11-2** (`LEGIARTI000046190612`) — Lorsque les pratiques commerciales agressives mentionnées aux articles L. 121-6 et L. 121-7 ont été commises en bande organisée, la peine d'emprisonnement prévue à l'article L. 132-11 est portée à sept ans.
- **L. 132-11** (`LEGIARTI000037556685`) — Les pratiques commerciales agressives mentionnées aux articles L. 121-6 et L. 121-7 sont punies d'un emprisonnement de deux ans et d'une amende de 300 000 euros. Le montant de l'amende peut être porté, de manière proportionnée aux avantages tirés du délit, à 10 % du chiffre d'affaires moyen annuel, calculé sur les…

*Notes :* CrossRef réel renvoi LEGIARTI000046190612→LEGIARTI000037556685 (corpus codes-v0.2-2025-07-13) | quality-pass v0.3.2 | quality-pass v0.3.2 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3 | handwrite-mh-answers v0.3.3

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

### 40. `t06` — `temporal`

**Question :** Que disait l'article L. 224-3 du Code de la consommation en vigueur au 2016-10-01 ?

**as_of :** `2016-10-01`

**Articles gold :** L. 224-3

**Ids LEGIARTI :** `LEGIARTI000046197680`

**Réponse attendue :** Au 2016-10-01, l'article L. 224-3 prévoyait que l'offre de fourniture d'électricité ou de gaz naturel précise, dans des termes clairs et compréhensibles, les informations suivantes. Par rapport à la version aujourd'hui en vigueur, la version courante modifie le passage « l'adresse de son siège social, son numéro unique d'identification ainsi que la mention RCS suivie du nom de la ville où se trouve le greffe où il est immatriculé ou tout document équivalent pour les sociétés situées hors de France et pour les opérateurs qui » (auparavant : « l'adresse de son siège social et son numéro d'inscription au registre du commerce et des sociétés ou tout document équivalent pour »).

**Extraits corpus :**

- **L. 224-3** (`LEGIARTI000046197680`) — L'offre de fourniture d'électricité ou de gaz naturel précise, dans des termes clairs et compréhensibles, les informations suivantes : 1° L'identité du fournisseur, l'adresse de son siège social, son numéro unique d'identification ainsi que la mention RCS suivie du nom de la ville où se trouve le greffe où il est…

*Notes :* version_at(2016-10-01)=LEGIARTI000032226733 ≠ tip LEGIARTI000046197680; debut=2016-07-01 fin=2018-01-01 | quality-pass v0.3.2 | quality-pass v0.3.2

Verdict : ☐ OK ☐ À corriger ☐ À reformuler

---

## Checklist

1. La réponse de référence est supportée par le(s) article(s) gelé(s).
2. Pas d'ambiguïté majeure (autres articles également valides non listés).
3. `multi_hop` : les deux (ou plus) articles sont nécessaires.
4. `temporal` : la réponse est correcte à la date `as_of`.
5. `unanswerable` : non répondable avec le snapshot courant.
6. `apparent_contradiction` : le « conflit » se résout par articulation des textes.
7. Passer `validated: true` question par question dans `questions.json` après revue.
