"""Generate gold-question candidates (templated / scripted; no paid APIs)."""

from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from rag_juridique.contracts.corpus import Article
from rag_juridique.contracts.gold import Question, QuestionType
from rag_juridique.gold.crossrefs import ResolvedEdge, resolve_cross_refs
from rag_juridique.gold.textutil import first_sentence, normalize_ws

_DURATION_RE = re.compile(
    r"(\d+)\s*(jours?|mois|ans?|années?)",
    re.IGNORECASE,
)


def _q(
    *,
    id: str,
    question: str,
    type: QuestionType,
    ids: list[str] | None = None,
    nums: list[str] | None = None,
    answer: str | None = None,
    as_of: date | None = None,
    topic: str | None = None,
    notes: str | None = None,
    unanswerable: bool = False,
) -> Question:
    return Question(
        id=id,
        question=normalize_ws(question),
        type=type,
        expected_article_ids=list(ids or []),
        expected_article_nums=list(nums or []),
        reference_answer=answer,
        as_of=as_of,
        unanswerable=unanswerable or type == QuestionType.UNANSWERABLE,
        validated=False,
        topic=topic,
        notes=notes,
    )


def migrate_mvp_questions(raw_questions: list[dict]) -> list[Question]:
    """Upgrade legacy MVP rows with explicit QuestionType."""
    out: list[Question] = []
    for item in raw_questions:
        data = dict(item)
        if data.get("unanswerable"):
            data["type"] = QuestionType.UNANSWERABLE.value
        else:
            # q26 is already multi-article — mark multi_hop.
            ids = data.get("expected_article_ids") or []
            if len(ids) >= 2:
                data["type"] = QuestionType.MULTI_HOP.value
            else:
                data["type"] = QuestionType.DIRECT.value
        data["validated"] = False
        out.append(Question.model_validate(data))
    return out


def curated_extra_questions(by_num: dict[str, Article]) -> list[Question]:
    """High-signal hand-authored candidates anchored on the MVP corpus."""

    def art(*nums: str) -> tuple[list[str], list[str]]:
        ids, ns = [], []
        for n in nums:
            a = by_num[n]
            ids.append(a.id)
            ns.append(a.num)
        return ids, ns

    qs: list[Question] = []

    # ---- multi_hop (cross-refs) ----
    multi = [
        (
            "mh01",
            "Quelles informations sur les prix l'obligation générale d'information "
            "précontractuelle (L. 111-1) renvoie-t-elle aux articles sur l'affichage "
            "des prix, et que dit L. 112-1 ?",
            ["L. 111-1", "L. 112-1"],
            "L. 111-1 renvoie aux articles L. 112-1 à L. 112-4-1 pour le prix ; "
            "L. 112-1 impose d'informer le consommateur sur les prix par marquage, "
            "étiquetage, affichage ou procédé approprié.",
            "info prix via renvoi",
        ),
        (
            "mh02",
            "Comment L. 111-2 s'articule-t-il avec L. 111-1 pour un contrat de services ?",
            ["L. 111-2", "L. 111-1"],
            "Outre les mentions de L. 111-1, le professionnel doit communiquer avant "
            "conclusion (ou avant exécution sans contrat écrit) des informations "
            "complémentaires sur ses coordonnées, son activité et les conditions "
            "contractuelles.",
            "info services",
        ),
        (
            "mh03",
            "Une pratique contraire à L. 121-2 à L. 121-4 est-elle déloyale au sens "
            "de L. 121-1, et que prévoit L. 121-5 ?",
            ["L. 121-1", "L. 121-5"],
            "Oui : L. 121-1 interdit les pratiques déloyales et renvoie notamment aux "
            "pratiques trompeuses et agressives ; L. 121-5 précise qu'une pratique "
            "conforme à L. 121-2 à L. 121-4 est déloyale.",
            "pratiques déloyales",
        ),
        (
            "mh04",
            "Quels délais et points de départ du droit de rétractation résultent de "
            "L. 221-18, et quels coûts L. 221-25 peut-il encore imposer ?",
            ["L. 221-18", "L. 221-25"],
            "L. 221-18 ouvre un délai de quatorze jours sans motiver la décision, sous "
            "réserve des coûts prévus aux articles L. 221-23 à L. 221-25 ; L. 221-25 "
            "traite notamment de la responsabilité des frais de renvoi lorsque le "
            "professionnel en a informé le consommateur.",
            "rétractation coûts",
        ),
        (
            "mh05",
            "Le vendeur répond-il des défauts de conformité au regard de L. 217-3 et "
            "des critères objectifs de L. 217-5 ?",
            ["L. 217-3", "L. 217-5"],
            "Oui : L. 217-3 impose de délivrer un bien conforme au contrat et aux "
            "critères de L. 217-5, et d'assurer la garantie pendant deux ans à compter "
            "de la délivrance.",
            "garantie conformité",
        ),
        (
            "mh06",
            "Comment la notion de délivrance (L. 216-1) intervient-elle dans le point "
            "de départ de la garantie de conformité (L. 217-3) ?",
            ["L. 216-1", "L. 217-3"],
            "L. 217-3 fait courir le délai de deux ans à compter de la délivrance au "
            "sens de L. 216-1 (transfert de la possession physique ou du contrôle du bien).",
            "délivrance et garantie",
        ),
        (
            "mh07",
            "Quelle est la différence de régime entre la définition des clauses abusives "
            "(L. 212-1) et leur sanction (L. 241-1) ?",
            ["L. 212-1", "L. 241-1"],
            "L. 212-1 définit comme abusives les clauses créant un déséquilibre "
            "significatif au détriment du consommateur ; L. 241-1 les répute non écrites "
            "tout en maintenant le reste du contrat s'il peut subsister.",
            "clauses abusives",
        ),
        (
            "mh08",
            "L. 216-6 renvoie à quel manquement à L. 216-1 et quelles options ouvre-t-il "
            "au consommateur ?",
            ["L. 216-6", "L. 216-1"],
            "En cas de manquement à l'obligation de délivrance de L. 216-1, L. 216-6 "
            "permet au consommateur d'enjoindre au professionnel d'exécuter, puis le "
            "cas échéant de résoudre le contrat.",
            "inexécution délivrance",
        ),
        (
            "mh09",
            "Comment L. 132-1 et L. 121-2 s'articulent-ils pour le délit de pratique "
            "commerciale trompeuse ?",
            ["L. 132-1", "L. 121-2"],
            "L. 121-2 définit les pratiques trompeuses ; L. 132-1 précise que le délit "
            "est constitué dès lors que la pratique est mise en œuvre ou produit ses "
            "effets en France.",
            "pratiques trompeuses",
        ),
        (
            "mh10",
            "Que doit contenir l'offre de crédit (L. 312-18) et sous quelle forme le "
            "contrat est-il ensuite établi (L. 312-28) ?",
            ["L. 312-18", "L. 312-28"],
            "L. 312-18 impose une offre sur support durable maintenue au moins quinze "
            "jours ; L. 312-28 exige un contrat sur support papier ou durable, distinct "
            "de la publicité, avec un encadré des caractéristiques essentielles.",
            "crédit forme",
        ),
        (
            "mh11",
            "Quelles informations L. 221-5 exige-t-il avant un contrat à distance, et "
            "quel délai de rétractation L. 221-18 ouvre-t-il ensuite ?",
            ["L. 221-5", "L. 221-18"],
            "L. 221-5 impose des informations précontractuelles spécifiques lisibles et "
            "compréhensibles ; L. 221-18 ouvre ensuite un délai de quatorze jours pour "
            "se rétracter.",
            "distance info+retractation",
        ),
        (
            "mh12",
            "L. 212-2 renvoie-t-il à L. 212-1 pour l'appréciation des clauses des "
            "contrats de vente de biens et de fourniture de services numériques ?",
            ["L. 212-2", "L. 212-1"],
            "Oui : L. 212-2 prévoit que pour ces contrats, le caractère abusif s'apprécie "
            "notamment au regard de L. 212-1.",
            "clauses abusives numériques",
        ),
    ]
    for qid, question, nums, answer, topic in multi:
        try:
            ids, ns = art(*nums)
        except KeyError:
            continue
        qs.append(
            _q(
                id=qid,
                question=question,
                type=QuestionType.MULTI_HOP,
                ids=ids,
                nums=ns,
                answer=answer,
                topic=topic,
                notes="multi_hop via renvoi / articulation d'articles",
            )
        )

    # ---- temporal (as_of) — designed to extend when ArticleVersion arrives ----
    temporal = [
        (
            "t01",
            "Au 1er janvier 2023, quelle durée de garantie légale de conformité "
            "s'appliquait pour un bien neuf au sens de L. 217-3 ?",
            "L. 217-3",
            date(2023, 1, 1),
            "Deux ans à compter de la délivrance du bien.",
            "La rédaction gelée du snapshot répond déjà ; lorsque les versions LEGI "
            "seront chargées, résoudre la version en vigueur à as_of.",
        ),
        (
            "t02",
            "En vigueur au 15 juin 2022, quel était le délai de rétractation pour un "
            "contrat conclu à distance ?",
            "L. 221-18",
            date(2022, 6, 15),
            "Quatorze jours.",
            None,
        ),
        (
            "t03",
            "À la date du 1er mars 2024, pendant combien de temps un défaut de "
            "conformité sur un bien neuf était-il présumé exister dès la délivrance ?",
            "L. 217-7",
            date(2024, 3, 1),
            "Vingt-quatre mois (douze mois pour les biens d'occasion).",
            None,
        ),
        (
            "t04",
            "Selon le droit applicable au 1er septembre 2021, quel délai maximal de "
            "délivrance s'imposait à défaut d'accord sur la date ?",
            "L. 216-1",
            date(2021, 9, 1),
            "Sans retard injustifié et au plus tard trente jours après la conclusion "
            "du contrat.",
            None,
        ),
        (
            "t05",
            "Au 1er janvier 2020, combien de temps le prêteur devait-il maintenir les "
            "conditions d'une offre de crédit à la consommation ?",
            "L. 312-18",
            date(2020, 1, 1),
            "Une durée minimale de quinze jours à compter de la remise ou de l'envoi.",
            None,
        ),
        (
            "t06",
            "En vigueur le 10 octobre 2019, une clause créant un déséquilibre "
            "significatif au détriment du consommateur était-elle abusive ?",
            "L. 212-1",
            date(2019, 10, 10),
            "Oui, dans les contrats conclus entre professionnels et consommateurs.",
            None,
        ),
        (
            "t07",
            "Au 1er juillet 2023, le consommateur avait-il droit de recourir "
            "gratuitement à un médiateur de la consommation ?",
            "L. 612-1",
            date(2023, 7, 1),
            "Oui ; le professionnel garantit un recours effectif à un dispositif de "
            "médiation.",
            None,
        ),
        (
            "t08",
            "Selon les dispositions en vigueur au 5 mai 2021, à quel moment le risque "
            "de perte du bien était-il transféré au consommateur ?",
            "L. 216-2",
            date(2021, 5, 5),
            "Lorsqu'il prend physiquement possession du bien, ou lorsqu'un tiers qu'il "
            "a désigné (autre que le transporteur) le fait.",
            None,
        ),
        (
            "t09",
            "Au 1er janvier 2025, les clauses abusives étaient-elles réputées non écrites ?",
            "L. 241-1",
            date(2025, 1, 1),
            "Oui ; le contrat demeure pour le reste s'il peut subsister sans elles.",
            None,
        ),
        (
            "t10",
            "En vigueur au 12 décembre 2022, les pratiques commerciales déloyales "
            "étaient-elles interdites ?",
            "L. 121-1",
            date(2022, 12, 12),
            "Oui, lorsqu'elles sont contraires à la diligence professionnelle et "
            "altèrent le comportement économique du consommateur.",
            None,
        ),
        (
            "t11",
            "À la date du 1er février 2018, le professionnel devait-il informer le "
            "consommateur sur les prix avant conclusion ?",
            "L. 112-1",
            date(2018, 2, 1),
            "Oui, par marquage, étiquetage, affichage ou tout autre procédé approprié.",
            None,
        ),
        (
            "t12",
            "Au 20 août 2024, quel délai de présomption de non-conformité s'appliquait "
            "aux biens d'occasion ?",
            "L. 217-7",
            date(2024, 8, 20),
            "Douze mois à compter de la délivrance.",
            None,
        ),
        (
            "t13",
            "Selon le droit au 1er juin 2016, les sommes versées d'avance étaient-elles "
            "des arrhes sauf stipulation contraire ?",
            "L. 214-1",
            date(2016, 6, 1),
            "Oui : le consommateur qui se désiste les perd ; le professionnel qui se "
            "désiste les restitue au double.",
            None,
        ),
        (
            "t14",
            "En vigueur le 3 mars 2022, le délai de rétractation pour une prestation de "
            "services à distance courait-il dès la conclusion du contrat ?",
            "L. 221-18",
            date(2022, 3, 3),
            "Oui, pour les contrats de prestation de services le délai court à compter "
            "de la conclusion du contrat.",
            None,
        ),
        (
            "t15",
            "Au 1er novembre 2021, le vendeur pouvait-il refuser réparation ou "
            "remplacement s'ils entraînaient des coûts disproportionnés ?",
            "L. 217-12",
            date(2021, 11, 1),
            "Oui, si la mise en conformité choisie est impossible ou disproportionnée "
            "au regard notamment de la valeur du bien et de l'importance du défaut.",
            None,
        ),
    ]
    for qid, question, num, as_of, answer, notes in temporal:
        if num not in by_num:
            continue
        a = by_num[num]
        qs.append(
            _q(
                id=qid,
                question=question,
                type=QuestionType.TEMPORAL,
                ids=[a.id],
                nums=[a.num],
                answer=answer,
                as_of=as_of,
                topic="temporal",
                notes=notes
                or (
                    "as_of renseigné ; résolution de version déléguée au corpus "
                    "(ArticleVersion) lorsqu'il sera disponible"
                ),
            )
        )

    # ---- apparent_contradiction traps ----
    traps = [
        (
            "ac01",
            "Le consommateur dispose de quatorze jours pour se rétracter (L. 221-18), "
            "mais certains contrats semblent totalement exclus : y a-t-il contradiction "
            "avec L. 221-28 ?",
            ["L. 221-18", "L. 221-28"],
            "Non : L. 221-18 pose le principe ; L. 221-28 énumère des exclusions "
            "légales (services pleinement exécutés avec accord, biens personnalisés, "
            "etc.). Les deux textes s'articulent, ils ne se contredisent pas.",
            "retractation vs exclusions",
        ),
        (
            "ac02",
            "La garantie de conformité dure deux ans (L. 217-3) alors que la "
            "présomption ne dure que douze mois pour un bien d'occasion (L. 217-7) : "
            "la garantie est-elle réduite à un an ?",
            ["L. 217-3", "L. 217-7"],
            "Non : le délai de garantie de deux ans (L. 217-3) n'est pas confondu avec "
            "le délai de présomption d'existence du défaut (vingt-quatre mois / douze "
            "mois pour l'occasion, L. 217-7).",
            "garantie vs présomption",
        ),
        (
            "ac03",
            "L. 216-1 impose une délivrance sous trente jours à défaut d'accord, mais "
            "L. 111-1 parle d'indiquer une date ou un délai : le professionnel peut-il "
            "ignorer toute date ?",
            ["L. 216-1", "L. 111-1"],
            "Non : L. 111-1 impose d'informer sur la date ou le délai ; L. 216-1 fixe "
            "ensuite la règle subsidiaire (sans retard injustifié, au plus tard trente "
            "jours) si rien n'a été convenu.",
            "délivrance info vs délai",
        ),
        (
            "ac04",
            "Les clauses abusives sont réputées non écrites (L. 241-1) alors que "
            "L. 212-1 dit qu'on n'apprécie pas l'objet principal ni l'adéquation du "
            "prix : le prix peut-il être déclaré abusif ?",
            ["L. 212-1", "L. 241-1"],
            "L'appréciation du caractère abusif ne porte ni sur l'objet principal ni "
            "sur l'adéquation prix/service (L. 212-1) ; la sanction du réputé non "
            "écrit (L. 241-1) s'applique aux clauses abusives ainsi définies, pas au "
            "prix lui-même en tant qu'adéquation.",
            "prix vs clause abusive",
        ),
        (
            "ac05",
            "L. 121-1 interdit les pratiques commerciales déloyales à l'égard des "
            "consommateurs, tandis que L. 121-5 étend L. 121-2 à L. 121-4 aux pratiques "
            "qui visent les professionnels et les non-professionnels : y a-t-il "
            "contradiction sur le champ d'application ?",
            ["L. 121-1", "L. 121-5"],
            "Non : L. 121-1 définit et interdit les pratiques déloyales visant le "
            "consommateur ; L. 121-5 étend le régime des articles L. 121-2 à L. 121-4 "
            "aux pratiques qui visent les professionnels et les non-professionnels, "
            "sans créer d'antinomie.",
            "déloyale champ L.121-5",
        ),
        (
            "ac06",
            "Le consommateur choisit librement réparation ou remplacement (L. 217-9), "
            "mais le vendeur peut refuser (L. 217-12) : le choix du consommateur est-il "
            "illusoire ?",
            ["L. 217-9", "L. 217-12"],
            "Non : le principe du choix appartient au consommateur (L. 217-9) ; le "
            "refus du vendeur n'est ouvert que si la mise en conformité choisie est "
            "impossible ou disproportionnée (L. 217-12).",
            "choix vs refus",
        ),
        (
            "ac07",
            "L. 221-18 dit qu'on se rétracte sans motiver ni supporter d'autres coûts, "
            "mais mentionne les coûts des articles L. 221-23 à L. 221-25 : y a-t-il "
            "contradiction ?",
            ["L. 221-18", "L. 221-25"],
            "Non : le principe est l'absence de coûts autres que ceux expressément "
            "prévus ; L. 221-25 précise des coûts limités (ex. frais de renvoi) lorsque "
            "les conditions d'information sont remplies.",
            "gratuité relative",
        ),
        (
            "ac08",
            "L. 111-1 liste des informations précontractuelles, L. 111-2 en ajoute "
            "pour les services : L. 111-1 suffit-il toujours seul ?",
            ["L. 111-1", "L. 111-2"],
            "Non pour les contrats de services : L. 111-2 impose des informations "
            "complémentaires « outre » celles de L. 111-1.",
            "info générale vs services",
        ),
        (
            "ac09",
            "Le risque est transféré à la prise de possession (L. 216-2) alors que la "
            "délivrance peut intervenir plus tard selon L. 216-1 : le consommateur "
            "supporte-t-il le risque avant délivrance ?",
            ["L. 216-2", "L. 216-1"],
            "Non en principe : le transfert du risque est lié à la prise de possession "
            "physique (L. 216-2), qui correspond à la délivrance au sens de L. 216-1.",
            "risque vs délivrance",
        ),
        (
            "ac10",
            "L. 312-1 fixe un champ d'application 200–75 000 €, tandis que L. 312-14 "
            "impose un devoir d'explication : ce devoir s'applique-t-il hors de ces "
            "montants ?",
            ["L. 312-1", "L. 312-14"],
            "Le devoir d'explication de L. 312-14 s'inscrit dans le chapitre dont le "
            "champ est borné par L. 312-1 ; hors de ce champ, ce régime spécifique ne "
            "s'applique pas tel quel.",
            "champ crédit",
        ),
        (
            "ac11",
            "L. 612-1 garantit un médiateur gratuit, mais L. 616-1 ne parle que "
            "d'information sur les coordonnées : le professionnel peut-il se contenter "
            "d'afficher un numéro sans médiation réelle ?",
            ["L. 612-1", "L. 616-1"],
            "Non : L. 612-1 impose un recours effectif à un dispositif de médiation ; "
            "L. 616-1 ajoute l'obligation d'informer sur les coordonnées du médiateur, "
            "y compris après réclamation infructueuse.",
            "médiation effective",
        ),
        (
            "ac12",
            "L. 217-4 pose des critères subjectifs de conformité et L. 217-5 des "
            "critères objectifs : un bien conforme au contrat peut-il quand même être "
            "non conforme ?",
            ["L. 217-4", "L. 217-5"],
            "Oui : la conformité s'apprécie au regard du contrat (L. 217-4) et des "
            "critères objectifs supplémentaires (L. 217-5) ; l'un ne suffit pas à "
            "écarter l'autre.",
            "conformité subjective/objective",
        ),
        (
            "ac13",
            "L. 221-19 prolonge parfois le délai de L. 221-18 : cela signifie-t-il "
            "que le délai de quatorze jours est abandonné ?",
            ["L. 221-18", "L. 221-19"],
            "Non : L. 221-18 fixe le délai de principe ; L. 221-19 organise des "
            "prolongations lorsque l'information sur le droit de rétractation n'a pas "
            "été fournie, sans supprimer le régime de base.",
            "délai vs prolongation",
        ),
        (
            "ac14",
            "L. 221-20 et L. 221-18 semblent dupliquer le droit de rétractation : y "
            "a-t-il redondance contradictoire ?",
            ["L. 221-20", "L. 221-18"],
            "Non : L. 221-18 pose le droit et le délai ; L. 221-20 précise des "
            "modalités complémentaires liées notamment à l'information de L. 221-5, "
            "sans inventer un régime opposé.",
            "retractation modalités",
        ),
        (
            "ac15",
            "L. 111-5 renvoie à plusieurs articles d'information (L. 111-1, L. 111-2, "
            "etc.) : leur cumul crée-t-il des obligations mutuellement exclusives ?",
            ["L. 111-5", "L. 111-1"],
            "Non : le renvoi organise un cumul d'informations selon les situations ; "
            "L. 111-1 demeure le socle, complété le cas échéant.",
            "cumul info",
        ),
        (
            "ac16",
            "L. 312-21 renvoie à L. 312-19 sur la rétractation du crédit : le délai "
            "de rétractation du crédit annule-t-il celui des contrats à distance ?",
            ["L. 312-21", "L. 312-19"],
            "Non : il s'agit du régime propre au crédit à la consommation, distinct "
            "du droit de rétractation des contrats à distance du livre II.",
            "crédits vs distance",
        ),
        (
            "ac17",
            "L. 112-5 renvoie à L. 112-1 à L. 112-4 tout en visant d'autres textes : "
            "ces renvois s'annulent-ils ?",
            ["L. 112-5", "L. 112-1"],
            "Non : L. 112-5 articule le champ d'application et des renvois ; L. 112-1 "
            "conserve sa portée sur l'information relative aux prix.",
            "affichage prix champ",
        ),
        (
            "ac18",
            "L. 217-3 impose deux ans de garantie alors que L. 216-1 parle de trente "
            "jours pour délivrer : la garantie serait-elle limitée à trente jours ?",
            ["L. 217-3", "L. 216-1"],
            "Non : les trente jours concernent le délai de délivrance à défaut "
            "d'accord ; les deux ans concernent la garantie de conformité après "
            "délivrance.",
            "délivrance vs garantie",
        ),
    ]
    for qid, question, nums, answer, topic in traps:
        try:
            ids, ns = art(*nums)
        except KeyError:
            continue
        qs.append(
            _q(
                id=qid,
                question=question,
                type=QuestionType.APPARENT_CONTRADICTION,
                ids=ids,
                nums=ns,
                answer=answer,
                topic=topic,
                notes="piège d'apparente contradiction ; les textes s'articulent",
            )
        )

    # ---- extra direct (articles peu couverts par le MVP) ----
    directs = [
        (
            "d31",
            "Que doit indiquer le professionnel lorsqu'une publicité mentionne une "
            "réduction de prix ?",
            "L. 112-1-1",
            "Il indique le prix antérieur pratiqué avant la réduction, selon les "
            "modalités prévues par le texte.",
        ),
        (
            "d32",
            "Dans quels cas une pratique commerciale est-elle agressive ?",
            "L. 121-6",
            None,  # may not be in corpus — skip if missing
        ),
        (
            "d33",
            "Qu'est-ce qu'un contrat hors établissement ?",
            "L. 221-1",
            "Un contrat conclu entre un professionnel et un consommateur dans "
            "simultanément présents physiquement dans un lieu qui n'est pas "
            "l'établissement commercial du professionnel, notamment.",
        ),
        (
            "d34",
            "Le professionnel doit-il rembourser le consommateur après rétractation ?",
            "L. 221-21",  # check - may be repayment article; use L.221-24 if needed
            None,
        ),
        (
            "d35",
            "Quelles sont les conditions de conformité d'un bien aux critères "
            "subjectifs du contrat ?",
            "L. 217-4",
            "Le bien doit notamment correspondre à la description, au type, à la "
            "quantité et à la qualité prévues au contrat, et être délivré avec les "
            "accessoires et instructions.",
        ),
        (
            "d36",
            "Qui a la charge de la preuve du défaut de conformité ?",
            "L. 217-8",
            "Il appartient au vendeur de prouver que le défaut de conformité n'existait "
            "pas au moment de la délivrance, sous les conditions du texte.",
        ),
        (
            "d37",
            "Dans quel délai la mise en conformité doit-elle intervenir ?",
            "L. 217-10",
            "Elle a lieu dans un délai raisonnable suivant la demande du consommateur, "
            "sans frais et sans inconvénient majeur pour celui-ci.",
        ),
        (
            "d38",
            "Le consommateur peut-il obtenir une réduction du prix ou la résolution "
            "en cas de non-conformité ?",
            "L. 217-13",  # verify
            None,
        ),
        (
            "d39",
            "Quelle est la durée de la garantie commerciale lorsqu'elle est consentie ?",
            "L. 217-28",
            None,
        ),
        (
            "d40",
            "Que doit contenir la publicité relative à un crédit à la consommation ?",
            "L. 312-5",  # may be missing
            None,
        ),
        (
            "d41",
            "L'emprunteur dispose-t-il d'un délai de rétractation pour un crédit à la "
            "consommation ?",
            "L. 312-19",
            "Oui ; le texte organise le droit de rétractation de l'emprunteur après "
            "acceptation de l'offre.",
        ),
        (
            "d42",
            "Quelles sanctions sont prévues en cas de clause abusive ?",
            "L. 241-1",
            "Les clauses abusives sont réputées non écrites ; le contrat reste "
            "applicable pour le reste s'il peut subsister.",
        ),
        (
            "d43",
            "Qui peut engager une action en suppression de clauses abusives ?",
            "L. 621-2",  # may be missing
            None,
        ),
        (
            "d44",
            "Le professionnel doit-il remédier gratuitement à un défaut de conformité ?",
            "L. 217-11",  # may be missing - check L.217-9/10
            None,
        ),
        (
            "d45",
            "Quelles informations le professionnel doit-il fournir sur les garanties "
            "légales avant la conclusion du contrat ?",
            "L. 111-1",
            "Il informe notamment sur l'existence et les modalités de mise en œuvre "
            "des garanties légales de conformité et des vices cachés, et des garanties "
            "commerciales éventuelles.",
        ),
    ]
    # Fix directs that referenced missing/uncertain nums — only emit if present
    # and we have a usable answer (derive from first sentence if answer is None).
    for qid, question, num, answer in directs:
        if num not in by_num:
            continue
        a = by_num[num]
        ref = answer or first_sentence(a.text, 320)
        qs.append(
            _q(
                id=qid,
                question=question,
                type=QuestionType.DIRECT,
                ids=[a.id],
                nums=[a.num],
                answer=ref,
                topic="direct",
            )
        )

    # ---- unanswerable (domains hors phase-2 prévue civil/travail/conso) ----
    unans = [
        ("u06", "Quelle est la durée maximale de la garde à vue de droit commun ?",
         "hors corpus (procédure pénale)"),
        ("u07", "Quel est le quantum de la peine encourue pour escroquerie simple ?",
         "hors corpus (pénal)"),
        ("u08", "Dans quel délai doit être déclarée une naissance à l'état civil ?",
         "hors corpus (état civil)"),
        ("u09", "Quelle majorité est requise pour modifier les statuts d'une SAS ?",
         "hors corpus (droit des sociétés)"),
        ("u10", "Quel est le délai de recours contre un permis de construire ?",
         "hors corpus (urbanisme)"),
        ("u11", "Quelle est la durée de validité d'une carte nationale d'identité "
         "délivrée à un majeur ?",
         "hors corpus (droit administratif / CNI)"),
        ("u12", "Quel est le plafond du livret A fixé par la réglementation bancaire ?",
         "hors corpus (réglementation bancaire)"),
        ("u13", "Quelle est la durée du préavis de licenciement pour un salarié "
         "cadre au sens de la convention collective Syntec ?",
         "hors corpus (convention collective — hors snapshot)"),
        ("u14", "Quel tribunal est compétent pour un divorce par consentement mutuel "
         "dématérialisé ?",
         "hors corpus (procédure familiale)"),
        ("u15", "Quel est le montant du SMIC horaire brut au 1er janvier 2024 ?",
         "hors corpus (montant réglementaire travail — hors texte LEGI figé ici)"),
        ("u16", "Quelle amende sanitaire est prévue pour un débit de tabac vendant "
         "à un mineur ?",
         "hors corpus (santé publique)"),
        ("u17", "Quel est le délai de prescription de l'action publique pour un délit ?",
         "hors corpus (procédure pénale)"),
        ("u18", "Comment se calcule l'impôt sur la fortune immobilière (IFI) ?",
         "hors corpus (fiscalité)"),
        ("u19", "Quelle est la durée maximale d'un bail meublé mobilité ?",
         "hors corpus (bail habitation — hors Code de la consommation snapshot)"),
        ("u20", "Quel est le seuil de revente à perte interdit pour un distributeur "
         "alimentaire hors règles conso figées ici ?",
         "hors corpus (autre régime / hors snapshot)"),
        ("u21", "Qui nomme les membres du Conseil constitutionnel ?",
         "hors corpus (droit constitutionnel)"),
        ("u22", "Quel est le délai pour contester une décision implicite de rejet "
         "d'une demande administrative ?",
         "hors corpus (contentieux administratif)"),
        ("u23", "Quelle est la distance minimale légale de plantation d'arbres "
         "par rapport à la limite séparative ?",
         "hors corpus (code civil voisinage — hors snapshot MVP)"),
        ("u24", "Quel est le taux du droit de mutation à titre onéreux sur un immeuble ?",
         "hors corpus (fiscalité / DMTO)"),
        ("u25", "Quelle est la composition du conseil de prud'hommes ?",
         "hors corpus (organisation judiciaire travail)"),
        ("u26", "Quel est le délai pour déposer une marque à l'INPI après un dépôt "
         "à l'étranger (priorité) ?",
         "hors corpus (propriété intellectuelle)"),
        ("u27", "Quelle autorité délivre l'autorisation environnementale pour une ICPE ?",
         "hors corpus (environnement)"),
        ("u28", "Quel est le régime de la communauté réduite aux acquêts pour les "
         "dettes ménagères ?",
         "hors corpus (régimes matrimoniaux — hors snapshot)"),
        ("u29", "Quelle est la durée du service national universel obligatoire ?",
         "hors corpus (défense / SNU)"),
        ("u30", "Quel est le plafond de la micro-entreprise pour les prestations de "
         "services en N-1 ?",
         "hors corpus (fiscalité / URSSAF)"),
    ]
    for qid, question, topic in unans:
        qs.append(
            _q(
                id=qid,
                question=question,
                type=QuestionType.UNANSWERABLE,
                answer="je ne sais pas",
                topic=topic,
                unanswerable=True,
                notes="Hors snapshot ; à re-vérifier si le corpus s'étend au-delà "
                "de consommation/civil/travail.",
            )
        )

    return qs


def generate_direct_from_corpus(
    articles: list[Article],
    *,
    start_index: int = 100,
) -> list[Question]:
    """Template direct questions from duration / obligation patterns in articles."""
    qs: list[Question] = []
    n = start_index
    for art in articles:
        # Duration facts
        for m in _DURATION_RE.finditer(art.text):
            value, unit = m.group(1), m.group(2).lower()
            span = m.group(0)
            # Context window around match
            start = max(0, m.start() - 80)
            end = min(len(art.text), m.end() + 80)
            ctx = normalize_ws(art.text[start:end])
            question = (
                f"Selon l'article {art.num}, quelle durée est prévue lorsqu'il est "
                f"question de « {span} » dans le régime concerné ?"
            )
            answer = (
                f"L'article {art.num} prévoit une durée de {value} {unit} "
                f"dans le contexte suivant : {ctx}"
            )
            qs.append(
                _q(
                    id=f"d{n}",
                    question=question,
                    type=QuestionType.DIRECT,
                    ids=[art.id],
                    nums=[art.num],
                    answer=answer,
                    topic="durée",
                    notes="template durée",
                )
            )
            n += 1
            if n > start_index + 80:
                return qs

        # Obligation template once per article
        if "professionnel" in art.text.lower() and "consommateur" in art.text.lower():
            qs.append(
                _q(
                    id=f"d{n}",
                    question=(
                        f"Quelles obligations l'article {art.num} met-il à la charge "
                        f"du professionnel à l'égard du consommateur ?"
                    ),
                    type=QuestionType.DIRECT,
                    ids=[art.id],
                    nums=[art.num],
                    answer=first_sentence(art.text, 360),
                    topic="obligation",
                    notes="template obligation",
                )
            )
            n += 1
    return qs


def generate_multi_hop_from_edges(
    edges: list[ResolvedEdge],
    by_id: dict[str, Article],
    *,
    start_index: int = 50,
    limit: int = 50,
) -> list[Question]:
    qs: list[Question] = []
    n = start_index
    for edge in edges:
        if len(qs) >= limit:
            break
        src = by_id[edge.source_id]
        tgt = by_id[edge.target_id]
        qs.append(
            _q(
                id=f"mh{n}",
                question=(
                    f"L'article {src.num} renvoie à l'article {tgt.num} : "
                    f"que dispose {src.num}, et que précise {tgt.num} sur ce point ?"
                ),
                type=QuestionType.MULTI_HOP,
                ids=[src.id, tgt.id],
                nums=[src.num, tgt.num],
                answer=(
                    f"{src.num} : {first_sentence(src.text, 200)} "
                    f"{tgt.num} : {first_sentence(tgt.text, 200)}"
                ),
                topic="renvoi",
                notes=f"edge:{edge.origin}:{edge.kind.value}",
            )
        )
        n += 1
    return qs


def generate_temporal_variants(
    articles: list[Article],
    *,
    start_index: int = 50,
    limit: int = 25,
) -> list[Question]:
    """Additional temporal questions with varied as_of dates."""
    dates = [
        date(2017, 1, 1),
        date(2019, 6, 1),
        date(2020, 12, 15),
        date(2021, 4, 1),
        date(2022, 1, 1),
        date(2023, 6, 15),
        date(2024, 1, 10),
        date(2025, 3, 1),
    ]
    qs: list[Question] = []
    n = start_index
    # Prefer articles with clear normative content
    preferred_nums = {
        "L. 111-1",
        "L. 112-1",
        "L. 121-1",
        "L. 121-2",
        "L. 212-1",
        "L. 216-1",
        "L. 216-2",
        "L. 217-3",
        "L. 217-7",
        "L. 221-1",
        "L. 221-18",
        "L. 221-28",
        "L. 241-1",
        "L. 312-1",
        "L. 312-18",
        "L. 612-1",
    }
    pool = [a for a in articles if a.num in preferred_nums] or list(articles)
    for i, art in enumerate(pool):
        if len(qs) >= limit:
            break
        as_of = dates[i % len(dates)]
        qs.append(
            _q(
                id=f"t{n}",
                question=(
                    f"Selon le droit en vigueur au {as_of.isoformat()}, que dispose "
                    f"l'article {art.num} du Code de la consommation ?"
                ),
                type=QuestionType.TEMPORAL,
                ids=[art.id],
                nums=[art.num],
                answer=first_sentence(art.text, 320),
                as_of=as_of,
                topic="temporal-template",
                notes="Prototype temporal sur snapshot courant ; versions LEGI à venir",
            )
        )
        n += 1
    return qs


def generate_apparent_contradiction_templates(
    edges: list[ResolvedEdge],
    by_id: dict[str, Article],
    *,
    start_index: int = 50,
    limit: int = 30,
) -> list[Question]:
    patterns = [
        (
            "Si l'on lit {a} isolément puis {b}, on croit détecter un conflit de "
            "règles : ce conflit est-il réel ?",
            "Lecture isolée trompeuse",
        ),
        (
            "Un professionnel se prévaut de {a} pour écarter {b} : cette opposition "
            "est-elle juridiquement fondée ?",
            "opposition instrumentalisée",
        ),
        (
            "{a} paraît absolu, alors que {b} introduit une limite : faut-il y voir "
            "une antinomie du Code de la consommation ?",
            "principe vs limite",
        ),
        (
            "Peut-on soutenir que {b} annule le régime de {a}, ou les deux textes "
            "doivent-ils être combinés ?",
            "annulation apparente",
        ),
        (
            "Entre l'obligation décrite par {a} et le correctif de {b}, y a-t-il "
            "contradiction ou simple articulation ?",
            "obligation vs correctif",
        ),
        (
            "Le renvoi de {a} vers {b} crée-t-il une double contrainte incompatible "
            "pour le professionnel ?",
            "double contrainte",
        ),
    ]
    qs: list[Question] = []
    n = start_index
    seen_pairs: set[tuple[str, str]] = set()
    for i, edge in enumerate(edges):
        if len(qs) >= limit:
            break
        pair = (edge.source_id, edge.target_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        src = by_id[edge.source_id]
        tgt = by_id[edge.target_id]
        tmpl, topic = patterns[i % len(patterns)]
        question = tmpl.format(a=src.num, b=tgt.num)
        qs.append(
            _q(
                id=f"ac{n}",
                question=question,
                type=QuestionType.APPARENT_CONTRADICTION,
                ids=[src.id, tgt.id],
                nums=[src.num, tgt.num],
                answer=(
                    f"Pas de contradiction : {src.num} et {tgt.num} s'articulent. "
                    f"{src.num} : {first_sentence(src.text, 140)} "
                    f"{tgt.num} : {first_sentence(tgt.text, 140)}"
                ),
                topic=topic,
                notes="trap template on linked pair",
            )
        )
        n += 1
    return qs


def generate_candidates(
    articles: list[Article],
    *,
    mvp_raw: list[dict] | None = None,
    cross_refs_path=None,
) -> list[Question]:
    by_id = {a.id: a for a in articles}
    by_num = {a.num: a for a in articles}
    candidates: list[Question] = []

    if mvp_raw:
        candidates.extend(migrate_mvp_questions(mvp_raw))

    candidates.extend(curated_extra_questions(by_num))

    edges = resolve_cross_refs(articles, cross_refs_path=cross_refs_path)
    candidates.extend(generate_multi_hop_from_edges(edges, by_id))
    candidates.extend(generate_direct_from_corpus(articles))
    candidates.extend(generate_temporal_variants(articles))
    candidates.extend(generate_apparent_contradiction_templates(edges, by_id))

    # Dedup by id keeping first
    seen: set[str] = set()
    unique: list[Question] = []
    for q in candidates:
        if q.id in seen:
            continue
        seen.add(q.id)
        unique.append(q)
    return unique


def select_balanced(
    questions: list[Question],
    *,
    target_min: int = 150,
    target_max: int = 200,
    per_type_min: dict[str, int] | None = None,
) -> list[Question]:
    """Keep a stratified subset in [target_min, target_max]."""
    defaults = {
        QuestionType.DIRECT.value: 50,
        QuestionType.MULTI_HOP.value: 40,
        QuestionType.TEMPORAL.value: 30,
        QuestionType.UNANSWERABLE.value: 30,
        QuestionType.APPARENT_CONTRADICTION.value: 30,
    }
    goals = dict(defaults)
    if per_type_min:
        goals.update(per_type_min)

    # Prefer MVP + curated ids (short / non-template) first
    def rank(q: Question) -> tuple[int, str]:
        pref = 0
        if re.match(r"^(q|u)\d+$", q.id):
            pref = 0
        elif re.match(r"^(mh|t|ac|d)\d{2}$", q.id):
            pref = 1
        else:
            pref = 2
        return (pref, q.id)

    by_type: dict[str, list[Question]] = {t.value: [] for t in QuestionType}
    for q in sorted(questions, key=rank):
        by_type[q.type.value].append(q)

    selected: list[Question] = []
    for t, goal in goals.items():
        selected.extend(by_type.get(t, [])[:goal])

    # If under target_min, fill from leftovers preferring under-represented types
    if len(selected) < target_min:
        have_ids = {q.id for q in selected}
        leftovers = [q for q in sorted(questions, key=rank) if q.id not in have_ids]
        for q in leftovers:
            selected.append(q)
            if len(selected) >= target_min:
                break

    if len(selected) > target_max:
        # Trim templates first
        selected = sorted(selected, key=rank)[:target_max]

    return selected
