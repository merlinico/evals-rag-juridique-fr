"""Hand-authored multi_hop Q/A rewrite (mh01–mh39). Apply to gold set."""

from __future__ import annotations

import json
from pathlib import Path

from rag_juridique.contracts.gold import GoldSet, QuestionType
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.gold.loader import load_gold_set
from rag_juridique.gold.review import (
    SAMPLE_TO_REVIEW_IDS,
    select_review_batch,
    write_review_batch,
)

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data" / "gold" / "questions.json"
STATS_PATH = ROOT / "data" / "gold" / "filter_stats.json"
REVIEW_PATH = ROOT / "data" / "gold" / "REVIEW_BATCH_40.md"
CARD_PATH = ROOT / "data" / "gold" / "DATASET_CARD.md"

# question may be None → keep existing question
HAND = {
    "mh01": {
        "question": (
            "Un professionnel a obtenu une prise de position formelle de "
            "l'administration sur ses modalités d'information des prix "
            "(article L. 112-5 du Code de la consommation) : dans quels cas "
            "cette garantie prend-elle fin selon l'article L. 112-6 ?"
        ),
        "answer": (
            "L'article L. 112-5 permet à tout professionnel de demander à "
            "l'autorité administrative chargée de la concurrence et de la "
            "consommation de prendre formellement position sur la conformité, "
            "aux articles L. 112-1 à L. 112-4 et à leurs mesures "
            "réglementaires, des modalités d'information sur les prix de "
            "vente au consommateur qu'il envisage ; cette prise de position "
            "vise à le prémunir d'un changement d'appréciation exposant aux "
            "sanctions des articles L. 131-5 et L. 131-6. L'article L. 112-6 "
            "fixe la fin de cette garantie : lorsque la situation du "
            "professionnel n'est plus identique à celle présentée dans la "
            "demande, lorsqu'une modification législative ou réglementaire "
            "affecte la validité de la garantie, ou à compter du jour où "
            "l'autorité notifie au professionnel la modification de son "
            "appréciation, après information préalable."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh02": {
        "question": (
            "Quelle sanction administrative frappe le manquement à "
            "l'obligation d'information sur les pièces détachées de "
            "l'article L. 111-4, et en quoi consiste cette obligation "
            "(articles L. 131-2 et L. 111-4 du Code de la consommation) ?"
        ),
        "answer": (
            "L'article L. 111-4 oblige le fabricant ou l'importateur de biens "
            "meubles à informer le vendeur professionnel de la disponibilité "
            "ou de la non-disponibilité des pièces détachées indispensables "
            "à l'utilisation des biens et, le cas échéant, de la période ou "
            "de la date jusqu'à laquelle ces pièces sont disponibles ; ces "
            "informations sont ensuite délivrées au consommateur avant la "
            "conclusion du contrat. L'article L. 131-2 sanctionne tout "
            "manquement à cette obligation d'informer sur la durée de "
            "disponibilité des pièces détachées d'une amende administrative "
            "d'au plus 3 000 euros pour une personne physique et 15 000 euros "
            "pour une personne morale, prononcée dans les conditions du "
            "chapitre II du titre II du livre V."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh03": {
        "question": (
            "Quelle est l'obligation d'information de l'article L. 111-6 du "
            "Code de la consommation sur les mises à jour logicielles, et "
            "quelle amende l'article L. 131-3-1 prévoit-il en cas de "
            "manquement ?"
        ),
        "answer": (
            "L'article L. 111-6 impose au producteur de biens comportant des "
            "éléments numériques d'informer le vendeur professionnel de la "
            "durée pendant laquelle les mises à jour logicielles qu'il "
            "fournit restent compatibles avec les fonctionnalités du bien ; "
            "le vendeur met ces informations à la disposition du "
            "consommateur, et le producteur informe aussi le consommateur "
            "des caractéristiques essentielles de chaque mise à jour. "
            "L'article L. 131-3-1 punit le manquement à cette obligation "
            "d'information d'une amende administrative plafonnée à 3 000 "
            "euros pour une personne physique et 15 000 euros pour une "
            "personne morale."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh04": {
        "question": (
            "En cas de pratique commerciale agressive suivie de la conclusion "
            "d'un contrat, comment l'article L. 132-11-1 du Code de la "
            "consommation aggrave-t-il la peine d'emprisonnement de "
            "l'article L. 132-11 ?"
        ),
        "answer": (
            "L'article L. 132-11 punit les pratiques commerciales agressives "
            "mentionnées aux articles L. 121-6 et L. 121-7 d'un "
            "emprisonnement de deux ans et d'une amende de 300 000 euros "
            "(pouvant être portée à 10 % du chiffre d'affaires moyen annuel). "
            "Lorsque ces pratiques ont été suivies de la conclusion d'un ou "
            "de plusieurs contrats, l'article L. 132-11-1 porte la peine "
            "d'emprisonnement prévue à l'article L. 132-11 à trois ans."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh05": {
        "question": (
            "Comment l'article L. 132-11-2 du Code de la consommation "
            "aggrave-t-il la peine d'emprisonnement de l'article L. 132-11 "
            "lorsque la pratique commerciale agressive est commise en bande "
            "organisée ?"
        ),
        "answer": (
            "L'article L. 132-11 fixe la peine de base des pratiques "
            "commerciales agressives des articles L. 121-6 et L. 121-7 à "
            "deux ans d'emprisonnement et 300 000 euros d'amende. "
            "L'article L. 132-11-2 dispose que, lorsque ces pratiques ont "
            "été commises en bande organisée, la peine d'emprisonnement "
            "prévue à l'article L. 132-11 est portée à sept ans."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh06": {
        "question": (
            "Quelles sont les conséquences civiles d'une vente forcée sans "
            "commande préalable (article L. 121-12), selon l'article "
            "L. 132-16 du Code de la consommation ?"
        ),
        "answer": (
            "L'article L. 121-12 interdit d'exiger le paiement immédiat ou "
            "différé de biens ou services fournis par un professionnel, ou "
            "d'exiger le renvoi ou la conservation de biens, sans commande "
            "préalable du consommateur. L'article L. 132-16 en tire la "
            "nullité de tout contrat conclu à la suite de cette pratique "
            "illicite : le professionnel doit restituer les sommes indûment "
            "perçues sans engagement exprès et préalable du consommateur, "
            "productives d'intérêts au taux légal puis au taux légal majoré "
            "de moitié à compter de la demande de remboursement."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh07": {
        "question": (
            "Quelle peine pénale l'article L. 132-17 du Code de la "
            "consommation attache-t-il à la violation de l'interdiction de "
            "vente forcée de l'article L. 121-12 ?"
        ),
        "answer": (
            "L'article L. 121-12 interdit d'exiger le paiement de biens ou "
            "services, ou le renvoi ou la conservation de biens, sans "
            "commande préalable du consommateur. L'article L. 132-17 punit "
            "la violation de cette interdiction d'un emprisonnement de deux "
            "ans et d'une amende de 300 000 euros, pouvant être portée à "
            "10 % du chiffre d'affaires moyen annuel calculé sur les trois "
            "derniers exercices connus."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh08": {
        "question": (
            "Lorsque des pratiques commerciales trompeuses (L. 121-2 à "
            "L. 121-4) ont été suivies de la conclusion d'un contrat, "
            "comment l'article L. 132-2-1 aggrave-t-il la peine de "
            "l'article L. 132-2 du Code de la consommation ?"
        ),
        "answer": (
            "L'article L. 132-2 punit les pratiques commerciales trompeuses "
            "des articles L. 121-2 à L. 121-4 de deux ans d'emprisonnement "
            "et de 300 000 euros d'amende (avec majorations possibles liées "
            "au chiffre d'affaires, aux dépenses publicitaires ou au "
            "support numérique). L'article L. 132-2-1 porte cette peine "
            "d'emprisonnement à trois ans lorsque les pratiques ont été "
            "suivies de la conclusion d'un ou de plusieurs contrats."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh09": {
        "question": (
            "Lorsque des pratiques commerciales trompeuses sont commises en "
            "bande organisée, comment l'article L. 132-2-2 aggrave-t-il la "
            "peine d'emprisonnement de l'article L. 132-2 du Code de la "
            "consommation ?"
        ),
        "answer": (
            "L'article L. 132-2 fixe à deux ans d'emprisonnement et 300 000 "
            "euros d'amende la peine de base des pratiques trompeuses des "
            "articles L. 121-2 à L. 121-4. L'article L. 132-2-2 dispose que, "
            "lorsque ces pratiques ont été commises en bande organisée, la "
            "peine d'emprisonnement prévue à l'article L. 132-2 est portée "
            "à sept ans."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh10": {
        "question": (
            "En quoi consiste l'obligation de consentement exprès de "
            "l'article L. 121-17 du Code de la consommation, et quelle "
            "amende l'article L. 132-22 prévoit-il en cas de manquement ?"
        ),
        "answer": (
            "L'article L. 121-17 oblige le professionnel, avant la conclusion "
            "du contrat, à s'assurer du consentement exprès du consommateur "
            "pour tout paiement supplémentaire s'ajoutant au prix de "
            "l'objet principal ; un consentement par défaut (absence "
            "d'opposition à des options non sollicitées) ouvre droit au "
            "remboursement. L'article L. 132-22 sanctionne le manquement à "
            "cette obligation de recueil du consentement exprès d'une amende "
            "administrative d'au plus 3 000 euros pour une personne physique "
            "et 15 000 euros pour une personne morale."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh11": {
        "question": (
            "Que sanctionne pénalement l'article L. 132-23 du Code de la "
            "consommation au titre de l'interdiction de frais de "
            "recouvrement de l'article L. 121-21 ?"
        ),
        "answer": (
            "L'article L. 121-21 interdit à un professionnel de solliciter "
            "ou de percevoir d'un consommateur des frais de recouvrement "
            "dans des conditions contraires au deuxième alinéa de "
            "l'article L. 111-8 du code des procédures civiles d'exécution. "
            "L'article L. 132-23 punit la violation de cette interdiction "
            "d'un emprisonnement de deux ans et d'une amende de 300 000 "
            "euros, pouvant être portée à 10 % du chiffre d'affaires moyen "
            "annuel."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh12": {
        "question": (
            "Quelle publicité l'article L. 121-22 du Code de la consommation "
            "interdit-il, et quelle amende l'article L. 132-24 prévoit-il "
            "pour l'annonceur qui la diffuse ?"
        ),
        "answer": (
            "L'article L. 121-22 interdit toute publicité portant sur "
            "certaines opérations commerciales non autorisées ou non "
            "déclarées (notamment au titre de l'article L. 122-24 du présent "
            "code ou de dispositions du code de commerce et du code du "
            "travail), ainsi que sur certaines manifestations commerciales "
            "non déclarées. L'article L. 132-24 rend passible l'annonceur "
            "qui diffuse ou fait diffuser une telle publicité interdite "
            "d'une amende administrative d'au plus 15 000 euros pour une "
            "personne physique et 75 000 euros pour une personne morale."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh13": {
        "question": (
            "Quels pouvoirs d'instruction l'article L. 132-6 du Code de la "
            "consommation donne-t-il au tribunal en matière de pratiques "
            "trompeuses, et que sanctionne l'article L. 132-7 en cas de "
            "refus de communication ?"
        ),
        "answer": (
            "Pour l'application des articles L. 132-2 et L. 132-3, "
            "l'article L. 132-6 permet au tribunal de demander aux parties "
            "et à l'annonceur la communication de tous documents utiles ; "
            "en cas de refus, il peut ordonner la saisie ou toute mesure "
            "d'instruction et prononcer une astreinte pouvant atteindre "
            "4 500 euros par jour de retard. L'article L. 132-7 punit le "
            "refus de communication des éléments de justification ou des "
            "publicités diffusées dans ces conditions d'un emprisonnement "
            "de deux ans et d'une amende de 300 000 euros."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh14": {
        "question": (
            "Si le professionnel ne délivre pas le bien ou ne fournit pas le "
            "service à la date prévue par l'article L. 216-1, quels recours "
            "l'article L. 216-6 du Code de la consommation ouvre-t-il au "
            "consommateur ?"
        ),
        "answer": (
            "L'article L. 216-1 impose au professionnel de délivrer le bien "
            "ou de fournir le service à la date ou dans le délai indiqué au "
            "consommateur (ou, à défaut, sans retard injustifié et au plus "
            "tard trente jours après la conclusion du contrat) ; la "
            "délivrance s'entend du transfert de la possession physique ou "
            "du contrôle du bien. En cas de manquement à cette obligation, "
            "l'article L. 216-6 permet au consommateur de suspendre le "
            "paiement jusqu'à exécution, de résoudre le contrat après mise "
            "en demeure restée sans effet dans un délai supplémentaire "
            "raisonnable, ou de résoudre immédiatement le contrat lorsque "
            "le professionnel refuse d'exécuter, qu'il est manifeste qu'il "
            "ne s'exécutera pas, ou que la date ou le délai était une "
            "condition essentielle du contrat."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh15": {
        "question": (
            "Avant d'exécuter un testament olographe ou mystique, quelles "
            "vérifications le notaire doit-il faire au regard de "
            "l'article 1006 du Code civil, selon l'article 1007 ?"
        ),
        "answer": (
            "L'article 1007 impose, avant toute exécution, le dépôt du "
            "testament olographe ou mystique entre les mains d'un notaire, "
            "qui dresse procès-verbal d'ouverture et d'état du testament. "
            "Dans le cas prévu à l'article 1006 — absence d'héritiers "
            "réservataires, le légataire universel étant alors saisi de "
            "plein droit par la mort du testateur sans avoir à demander la "
            "délivrance — le notaire vérifie le caractère universel de la "
            "vocation et l'absence d'héritiers réservataires, porte ces "
            "vérifications sur le procès-verbal, et tout intéressé peut "
            "s'opposer dans le mois suivant la réception des pièces au "
            "greffe, auquel cas le légataire se fera envoyer en possession."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh16": {
        "question": (
            "Dans une libéralité graduelle, d'où le second gratifié et, le "
            "cas échéant, ses héritiers tiennent-ils leurs droits "
            "(articles 1051 et 1056 du Code civil) ?"
        ),
        "answer": (
            "L'article 1051 dispose que le second gratifié est réputé tenir "
            "ses droits de l'auteur de la libéralité, et qu'il en va de même "
            "de ses héritiers lorsqu'ils recueillent la libéralité dans les "
            "conditions de l'article 1056. L'article 1056 précise que si le "
            "second gratifié prédécède au grevé ou renonce, les biens "
            "dépendent de la succession du grevé, sauf si l'acte prévoit "
            "expressément que les héritiers du second gratifié pourront la "
            "recueillir ou désigne un autre second gratifié."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh17": {
        "question": (
            "Un grevé héritier réservataire peut-il accepter que la charge "
            "d'une libéralité graduelle greve sa réserve, et sous quelle "
            "forme d'acte (articles 1054 et 930 du Code civil) ?"
        ),
        "answer": (
            "L'article 1054 pose que si le grevé est héritier réservataire, "
            "la charge ne peut en principe être imposée que sur la quotité "
            "disponible ; le donataire peut toutefois accepter, dans l'acte "
            "de donation ou postérieurement dans un acte établi dans les "
            "conditions de l'article 930, que la charge greve tout ou partie "
            "de sa réserve. L'article 930 exige pour cette renonciation un "
            "acte authentique spécifique reçu par deux notaires, signé "
            "séparément par chaque renonçant en leur seule présence, et "
            "mentionnant précisément ses conséquences juridiques futures, "
            "à peine de nullité."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh18": {
        "question": (
            "Une donation de biens présents entre époux pendant le mariage "
            "est-elle librement révocable, ou seulement pour les causes de "
            "l'article 953 (article 1096 du Code civil) ?"
        ),
        "answer": (
            "L'article 1096 distingue : la donation de biens à venir entre "
            "époux pendant le mariage est toujours révocable, alors que la "
            "donation de biens présents prenant effet au cours du mariage "
            "n'est révocable que dans les conditions des articles 953 à 958. "
            "L'article 953 limite la révocation des donations entre vifs à "
            "trois causes : inexécution des conditions, ingratitude, et "
            "survenance d'enfants — cette dernière cause étant toutefois "
            "écartée pour les donations entre époux par l'article 1096 "
            "lui-même."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh19": {
        "question": (
            "En cas de révocation pour ingratitude d'une donation de biens "
            "présents entre époux, que prévoit l'article 958 du Code civil "
            "auxquels renvoie l'article 1096 ?"
        ),
        "answer": (
            "L'article 1096 soumet la révocation des donations de biens "
            "présents entre époux aux conditions des articles 953 à 958. "
            "L'article 958 précise que la révocation pour ingratitude ne "
            "préjudicie ni aux aliénations ni aux hypothèques et autres "
            "charges réelles antérieures à la publication de la demande au "
            "fichier immobilier ; le donataire doit alors restituer la "
            "valeur des objets aliénés au temps de la demande, ainsi que "
            "les fruits à compter de ce jour."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh20": {
        "question": (
            "Lorsqu'un écrit est exigé pour la validité d'un contrat, quelles "
            "conditions l'article 1366 du Code civil pose-t-il pour qu'un "
            "écrit électronique vaille, selon le renvoi de l'article 1174 ?"
        ),
        "answer": (
            "L'article 1174 permet d'établir et de conserver sous forme "
            "électronique l'écrit exigé pour la validité d'un contrat, dans "
            "les conditions des articles 1366 et 1367. L'article 1366 "
            "reconnaît à l'écrit électronique la même force probante que "
            "l'écrit papier, sous réserve que la personne dont il émane "
            "puisse être dûment identifiée et que l'écrit soit établi et "
            "conservé dans des conditions garantissant son intégrité."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh21": {
        "question": (
            "Pour qu'un contrat dont la validité exige un écrit puisse être "
            "conclu électroniquement, que dit l'article 1367 du Code civil "
            "sur la signature électronique, au regard du renvoi de "
            "l'article 1174 ?"
        ),
        "answer": (
            "L'article 1174 autorise l'écrit électronique de validité dans "
            "les conditions des articles 1366 et 1367, et précise qu'une "
            "mention manuscrite exigée peut aussi être apposée "
            "électroniquement si elle ne peut être effectuée que par "
            "l'obligé. L'article 1367 définit la signature comme "
            "identifiant l'auteur et manifestant son consentement ; lorsqu'elle "
            "est électronique, elle repose sur un procédé fiable d'identification "
            "garantissant son lien avec l'acte, dont la fiabilité est présumée "
            "dans les conditions fixées par décret en Conseil d'État."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh22": {
        "question": (
            "Après annulation d'un contrat au sens de l'article 1178 du Code "
            "civil, comment s'opère la restitution d'une chose autre qu'une "
            "somme d'argent selon l'article 1352 ?"
        ),
        "answer": (
            "L'article 1178 dispose que le contrat qui ne remplit pas les "
            "conditions de validité est nul, qu'il est censé n'avoir jamais "
            "existé, et que les prestations exécutées donnent lieu à "
            "restitution dans les conditions des articles 1352 à 1352-9. "
            "L'article 1352 précise que la restitution d'une chose autre "
            "qu'une somme d'argent a lieu en nature ou, si cela est "
            "impossible, en valeur estimée au jour de la restitution."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh23": {
        "question": (
            "En cas de nullité du contrat (article 1178 du Code civil), que "
            "deviennent les sûretés selon l'article 1352-9 auquel renvoie le "
            "régime des restitutions ?"
        ),
        "answer": (
            "L'article 1178 renvoie, pour les restitutions consécutives à "
            "l'annulation, aux articles 1352 à 1352-9. L'article 1352-9 "
            "dispose que les sûretés constituées pour le paiement de "
            "l'obligation sont reportées de plein droit sur l'obligation de "
            "restituer, sans toutefois que la caution soit privée du bénéfice "
            "du terme."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh24": {
        "question": (
            "La caducité d'un contrat peut-elle donner lieu à restitution, "
            "et selon quelles modalités pour une chose autre qu'une somme "
            "d'argent (articles 1187 et 1352 du Code civil) ?"
        ),
        "answer": (
            "L'article 1187 dispose que la caducité met fin au contrat et "
            "qu'elle peut donner lieu à restitution dans les conditions des "
            "articles 1352 à 1352-9. L'article 1352 prévoit alors que la "
            "restitution d'une chose autre qu'une somme d'argent a lieu en "
            "nature ou, à défaut, en valeur estimée au jour de la "
            "restitution."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh25": {
        "question": (
            "En cas de caducité du contrat (article 1187 du Code civil), que "
            "prévoit l'article 1352-9 pour les sûretés liées à l'obligation "
            "de restituer ?"
        ),
        "answer": (
            "L'article 1187 ouvre la possibilité de restitutions après "
            "caducité selon les articles 1352 à 1352-9. L'article 1352-9 "
            "reporte de plein droit les sûretés constituées pour le paiement "
            "de l'obligation sur l'obligation de restituer, sans priver la "
            "caution du bénéfice du terme."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh26": {
        "question": (
            "En cas de force majeure définitive empêchant l'exécution "
            "(article 1218 du Code civil), dans quelle mesure le débiteur "
            "est-il libéré selon l'article 1351 ?"
        ),
        "answer": (
            "L'article 1218 définit la force majeure contractuelle et "
            "prévoit que si l'empêchement est définitif, le contrat est "
            "résolu de plein droit et les parties sont libérées dans les "
            "conditions des articles 1351 et 1351-1. L'article 1351 précise "
            "que l'impossibilité d'exécuter libère le débiteur à due "
            "concurrence lorsqu'elle procède d'un cas de force majeure "
            "définitive, sauf s'il a convenu de s'en charger ou s'il a été "
            "préalablement mis en demeure."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh27": {
        "question": (
            "Si la force majeure définitive tient à la perte de la chose due "
            "(articles 1218 et 1351-1 du Code civil), le débiteur mis en "
            "demeure est-il encore libéré ?"
        ),
        "answer": (
            "L'article 1218 renvoie, pour la libération des parties en cas "
            "d'empêchement définitif par force majeure, aux articles 1351 "
            "et 1351-1. L'article 1351-1 dispose que lorsque "
            "l'impossibilité résulte de la perte de la chose due, le "
            "débiteur mis en demeure est néanmoins libéré s'il prouve que "
            "la perte se serait pareillement produite si l'obligation avait "
            "été exécutée ; il doit alors céder au créancier les droits et "
            "actions attachés à la chose."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh28": {
        "question": (
            "Les titulaires d'un contrat initiative-emploi comptent-ils dans "
            "les effectifs de l'entreprise, et à quelle aide l'article "
            "L. 1111-3 du Code du travail renvoie-t-il (article L. 5134-72) ?"
        ),
        "answer": (
            "L'article L. 1111-3 exclut du calcul des effectifs, notamment, "
            "les titulaires d'un contrat initiative-emploi pendant la durée "
            "d'attribution de l'aide financière mentionnée à "
            "l'article L. 5134-72 (ainsi que d'autres catégories : "
            "apprentis, contrats d'accompagnement dans l'emploi, contrats "
            "de professionnalisation, sous les réserves du texte). "
            "L'article L. 5134-72 précise que cette aide à l'insertion "
            "professionnelle au titre d'un contrat initiative-emploi peut "
            "être modulée selon la catégorie et le secteur d'activité de "
            "l'employeur, les actions d'accompagnement et d'insertion "
            "durable, les conditions économiques locales et les difficultés "
            "d'accès à l'emploi antérieurement rencontrées par le salarié."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh29": {
        "question": (
            "Un salarié peut-il être sanctionné ou licencié pour avoir "
            "exercé normalement son droit de grève, au regard des "
            "articles L. 1132-2 et L. 1132-1 du Code du travail ?"
        ),
        "answer": (
            "L'article L. 1132-1 interdit toute mesure discriminatoire "
            "(sanction, licenciement, etc.) fondée sur les motifs qu'il "
            "énumère. L'article L. 1132-2 étend cette protection en "
            "prohibant toute sanction, licenciement ou mesure "
            "discriminatoire mentionnée à l'article L. 1132-1 en raison de "
            "l'exercice normal du droit de grève."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh30": {
        "question": (
            "Un salarié peut-il être sanctionné ou licencié pour avoir "
            "exercé les fonctions de juré ou de citoyen assesseur "
            "(articles L. 1132-3-1 et L. 1132-1 du Code du travail) ?"
        ),
        "answer": (
            "L'article L. 1132-3-1 interdit de sanctionner, de licencier ou "
            "de faire l'objet d'une mesure discriminatoire mentionnée à "
            "l'article L. 1132-1 un salarié en raison de l'exercice des "
            "fonctions de juré ou de citoyen assesseur. L'article L. 1132-1 "
            "définit le champ des mesures discriminatoires prohibées "
            "(recrutement, sanction, licenciement, rémunération, promotion, "
            "etc.) auxquelles ce renvoi se rattache."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh31": {
        "question": (
            "Un salarié peut-il être sanctionné pour avoir refusé, en raison "
            "de son orientation sexuelle, une mutation dans un État "
            "incriminant l'homosexualité (articles L. 1132-3-2 et L. 1132-1 "
            "du Code du travail) ?"
        ),
        "answer": (
            "L'article L. 1132-3-2 interdit de sanctionner, de licencier ou "
            "de faire l'objet d'une mesure discriminatoire mentionnée à "
            "l'article L. 1132-1 un salarié qui a refusé, en raison de son "
            "orientation sexuelle, une mutation géographique dans un État "
            "incriminant l'homosexualité. Le renvoi à l'article L. 1132-1 "
            "fixe le type de mesures discriminatoires ainsi prohibées."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh32": {
        "question": (
            "Dans quelles conditions un syndicat peut-il agir en justice "
            "pour discrimination au profit d'un salarié, et quel est le "
            "régime de preuve de l'article L. 1134-1 auquel renvoie "
            "l'article L. 1134-2 du Code du travail ?"
        ),
        "answer": (
            "L'article L. 1134-2 permet aux organisations syndicales "
            "représentatives d'exercer les actions issues du chapitre II "
            "relatif aux discriminations, y compris en faveur d'un "
            "candidat ou d'un salarié dans les conditions de "
            "l'article L. 1134-1, sans mandat dès lors que l'intéressé a "
            "été averti par écrit et ne s'y est pas opposé dans les quinze "
            "jours. L'article L. 1134-1 organise la charge de la preuve : "
            "le salarié présente des faits laissant supposer une "
            "discrimination ; il incombe alors au défendeur de prouver que "
            "sa décision repose sur des éléments objectifs étrangers à "
            "toute discrimination."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh33": {
        "question": (
            "Une association de lutte contre les discriminations peut-elle "
            "agir pour le compte d'un salarié, et selon quel régime de "
            "preuve (articles L. 1134-3 et L. 1134-1 du Code du travail) ?"
        ),
        "answer": (
            "L'article L. 1134-3 autorise les associations constituées "
            "depuis au moins cinq ans pour lutter contre les discriminations "
            "ou œuvrant dans le domaine du handicap à exercer les actions "
            "du chapitre II, y compris en faveur d'un candidat ou d'un "
            "salarié dans les conditions de l'article L. 1134-1, sous "
            "réserve d'un accord écrit de l'intéressé. L'article L. 1134-1 "
            "fixe le régime probatoire applicable à ces actions : "
            "présomption à partir d'éléments de fait présentés par "
            "l'intéressé, puis preuve contraire à la charge du défendeur."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh34": {
        "question": (
            "Lorsque l'index d'égalité professionnelle de l'article "
            "L. 1142-8 est en deçà du seuil réglementaire, quelles "
            "obligations de négociation et de correction l'article "
            "L. 1142-9 du Code du travail impose-t-il ?"
        ),
        "answer": (
            "L'article L. 1142-8 impose aux entreprises d'au moins cinquante "
            "salariés de publier chaque année les indicateurs relatifs aux "
            "écarts de rémunération entre les femmes et les hommes et aux "
            "actions mises en œuvre pour les supprimer. Lorsque ces "
            "résultats sont en deçà d'un niveau fixé par décret, "
            "l'article L. 1142-9 étend la négociation sur l'égalité "
            "professionnelle aux mesures de correction et, le cas échéant, "
            "à une programmation de rattrapage salarial ; à défaut "
            "d'accord, l'employeur fixe ces mesures après consultation du "
            "CSE et les publie."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh35": {
        "question": (
            "En l'absence d'accord sur les mesures de correction prévues "
            "par l'article L. 1142-9 du Code du travail, dans quelles "
            "conditions la décision de l'employeur est-elle déposée au "
            "regard de l'article L. 2242-3 ?"
        ),
        "answer": (
            "L'article L. 1142-9 prévoit qu'à défaut d'accord sur les "
            "mesures de correction liées à un index insuffisant, celles-ci "
            "sont déterminées par décision de l'employeur après "
            "consultation du CSE, et que cette décision est déposée auprès "
            "de l'autorité administrative dans les mêmes conditions que le "
            "plan d'action mentionné à l'article L. 2242-3. "
            "L'article L. 2242-3 impose, en l'absence d'accord relatif à "
            "l'égalité professionnelle, l'établissement d'un plan d'action "
            "annuel évaluant les objectifs passés, fixant les objectifs de "
            "progression et les actions associées, puis déposé auprès de "
            "l'autorité administrative."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh36": {
        "question": (
            "Lorsque les indicateurs d'égalité professionnelle de "
            "l'article L. 1142-8 sont insuffisants, que doit publier "
            "l'employeur selon l'article L. 1142-9-1 du Code du travail ?"
        ),
        "answer": (
            "L'article L. 1142-8 organise la publication annuelle des "
            "indicateurs d'écarts de rémunération femmes-hommes dans les "
            "entreprises d'au moins cinquante salariés. "
            "L'article L. 1142-9-1 ajoute que, lorsque ces résultats "
            "sont en deçà d'un niveau défini par décret, l'employeur fixe "
            "et publie les objectifs de progression de chacun de ces "
            "indicateurs, selon les modalités des articles L. 2242-1 et "
            "L. 2242-3 et dans les conditions du même décret."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh37": {
        "question": (
            "Un syndicat peut-il agir en justice pour harcèlement au profit "
            "d'un salarié, et selon quel régime de preuve "
            "(articles L. 1154-2 et L. 1154-1 du Code du travail) ?"
        ),
        "answer": (
            "L'article L. 1154-2 permet aux organisations syndicales "
            "représentatives dans l'entreprise d'exercer les actions "
            "issues des articles relatifs au harcèlement moral et sexuel, "
            "y compris en faveur d'un salarié dans les conditions de "
            "l'article L. 1154-1, sous réserve d'un accord écrit de "
            "l'intéressé. L'article L. 1154-1 fixe le régime probatoire : "
            "le salarié présente des faits laissant supposer un "
            "harcèlement ; il appartient au défendeur de prouver que les "
            "agissements ne sont pas constitutifs d'un harcèlement et que "
            "sa décision repose sur des éléments objectifs étrangers à "
            "tout harcèlement."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh38": {
        "question": (
            "Que sanctionne l'article L. 1155-1 du Code du travail s'agissant "
            "de la médiation en matière de harcèlement moral prévue à "
            "l'article L. 1152-6 ?"
        ),
        "answer": (
            "L'article L. 1152-6 organise une médiation pouvant être mise "
            "en œuvre par toute personne de l'entreprise s'estimant victime "
            "de harcèlement moral ou par la personne mise en cause, le "
            "médiateur étant choisi d'un commun accord et tentant de "
            "concilier les parties. L'article L. 1155-1 punit d'un an "
            "d'emprisonnement et de 3 750 euros d'amende le fait de porter "
            "ou de tenter de porter atteinte à l'exercice régulier des "
            "fonctions de ce médiateur."
        ),
        "reformulated": True,
        "weak": False,
    },
    "mh39": {
        "question": (
            "Quelle pénalité l'article L. 1221-11 du Code du travail attache-t-il "
            "au non-respect de la déclaration préalable à l'embauche, et "
            "quels agents peuvent le constater selon le renvoi à "
            "l'article L. 8271-7 ?"
        ),
        "answer": (
            "L'article L. 1221-11 prévoit que le non-respect de l'obligation "
            "de déclaration préalable à l'embauche, constaté par les agents "
            "mentionnés à l'article L. 8271-7, entraîne une pénalité égale "
            "à trois cents fois le taux horaire du minimum garanti de "
            "l'article L. 3231-12. L'article L. 8271-7, dans la rédaction "
            "du snapshot, se borne à indiquer que les infractions aux "
            "interdictions du travail dissimulé de l'article L. 8221-1 sont "
            "recherchées par les agents mentionnés à l'article L. 8271-1-2 : "
            "le renvoi est donc purement organique et n'expose pas, à "
            "lui seul, le régime de contrôle de la déclaration préalable."
        ),
        "reformulated": True,
        "weak": True,
        "weak_reason": (
            "Renvoi purement organique aux agents de constat ; le texte tip "
            "de L. 8271-7 porte sur le travail dissimulé (L. 8221-1) via "
            "L. 8271-1-2 et n'explicite pas le contrôle de la DPAE. Question "
            "peu informative pour un gold multi_hop."
        ),
    },
}

# Thin but still answerable (series renvoi 1352–1352-9 sliced to one tip article).
THIN = {
    "mh22": "1178 renvoie à toute la série 1352–1352-9 ; l'item ne cible que 1352.",
    "mh23": "1178 renvoie à toute la série 1352–1352-9 ; l'item ne cible que 1352-9.",
    "mh24": "1187 renvoie à toute la série 1352–1352-9 ; l'item ne cible que 1352.",
    "mh25": "1187 renvoie à toute la série 1352–1352-9 ; l'item ne cible que 1352-9.",
}


def apply() -> dict:
    corpus = load_corpus()
    gold = load_gold_set(GOLD_PATH)
    by_id = {q.id: q for q in gold.questions}
    changed: list[str] = []
    reformulated: list[str] = []
    weak: list[dict] = []

    out_questions = []
    for q in gold.questions:
        if q.id not in HAND:
            out_questions.append(q)
            continue
        spec = HAND[q.id]
        # Safety: never change gold articles
        new_q = q.model_copy(
            update={
                "question": spec["question"] if spec.get("question") else q.question,
                "reference_answer": spec["answer"],
                "validated": False,
                "notes": (
                    (q.notes or "").rstrip()
                    + " | handwrite-mh-answers v0.3.3"
                    + (" | weak-renvoi" if spec.get("weak") else "")
                ),
            }
        )
        out_questions.append(new_q)
        changed.append(q.id)
        # All hand-authored items intentionally ship a domain-specific question.
        if spec.get("reformulated"):
            reformulated.append(q.id)
        if spec.get("weak"):
            weak.append(
                {
                    "id": q.id,
                    "articles": q.expected_article_nums,
                    "reason": spec.get("weak_reason", ""),
                }
            )
        elif q.id in THIN:
            weak.append(
                {
                    "id": q.id,
                    "articles": q.expected_article_nums,
                    "reason": THIN[q.id],
                    "severity": "thin",
                }
            )

    # Verify no article drift
    for qid in HAND:
        assert by_id[qid].expected_article_ids == [
            q.expected_article_ids
            for q in out_questions
            if q.id == qid
        ][0]
        assert by_id[qid].expected_article_nums == [
            q.expected_article_nums
            for q in out_questions
            if q.id == qid
        ][0]

    gold_out = GoldSet(
        version="0.3.3",
        corpus_snapshot=corpus.snapshot_id,
        language="fr",
        validated=False,
        notes=(
            "Gold v0.3.3 — réponses multi_hop mh01–mh39 réécrites à la main "
            "(lien réel entre articles, sans troncature ni passe-partout). "
            "validated=false."
        ),
        questions=out_questions,
    )
    batch = select_review_batch(
        out_questions, size=40, must_include=SAMPLE_TO_REVIEW_IDS
    )

    stats = {
        "mode": "handwrite_mh_answers_v033",
        "corpus_snapshot": corpus.snapshot_id,
        "n_articles": len(corpus.articles),
        "n_crossrefs": len(corpus.crossrefs),
        "selected_total": len(out_questions),
        "selected_by_type": {
            t.value: sum(1 for q in out_questions if q.type == t)
            for t in QuestionType
        },
        "changed_ids": changed,
        "reformulated_question_ids": reformulated,
        "weak_items": weak,
        "review_batch_ids": [q.id for q in batch],
        "crossrefs_removed_prior": 1290,
        "validated": False,
    }

    GOLD_PATH.write_text(
        json.dumps(gold_out.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    note = (
        "> **Correctifs (v0.3.3)** : réponses `multi_hop` mh01–mh39 réécrites "
        "à la main (lien réel entre articles, sans troncature ni "
        "passe-partout) ; questions reformulées lorsque le gabarit "
        "ne collait pas au renvoi."
    )
    write_review_batch(REVIEW_PATH, batch, corpus.articles, header_note=note)

    # Light dataset card bump
    if CARD_PATH.exists():
        text = CARD_PATH.read_text(encoding="utf-8")
        text = text.replace("v0.3.2", "v0.3.3")
        if "handwrite" not in text:
            text = text.replace(
                "passe qualité v0.3.2 (réponses mh synthétisées, acteurs par domaine, diffs temporels concrets).",
                "passe qualité v0.3.2 ; réponses multi_hop mh01–mh39 réécrites à la main (v0.3.3).",
            )
        CARD_PATH.write_text(text, encoding="utf-8")

    return stats


if __name__ == "__main__":
    s = apply()
    print("changed", len(s["changed_ids"]))
    print("reformulated", s["reformulated_question_ids"])
    print("weak", s["weak_items"])
