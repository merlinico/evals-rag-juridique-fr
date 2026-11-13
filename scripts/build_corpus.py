#!/usr/bin/env python3
"""Build the frozen multi-code LEGI corpus snapshot (reproducible).

Sources (Licence Ouverte 2.0 / Etalab — attribute DILA):
  * Hugging Face ``VinceGx33/legi-french-law-2025`` (derived from Freemium LEGI
    dump 2025-07-13) for articles currently in force.
  * Optional Freemium LEGI tar.gz for ``ArticleVersion`` history (VERSIONS /
    LIEN_ART + historical article XML).

Usage
-----
  uv run python scripts/build_corpus.py \\
      --parquet /tmp/legi-build/legi_french_law.parquet \\
      --dump /tmp/legi-build/Freemium_legi_global_20261108-140000.tar.gz

Without ``--dump``, tip versions are still emitted from parquet date_debut /
date_fin so ``Corpus.version_at`` works for the current interval.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import tarfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_juridique.contracts.corpus import Article, ArticleVersion
from rag_juridique.corpus.hierarchy import (
    normalize_article_num,
    parse_contexte,
)
from rag_juridique.corpus.loader import write_corpus_snapshot
from rag_juridique.corpus.refs import build_crossrefs
from rag_juridique.corpus.versions import parse_legi_date

CODE_META = {
    "civil": {
        "title": "Code civil",
        "texte_cid": "LEGITEXT000006070721",
    },
    "consommation": {
        "title": "Code de la consommation",
        "texte_cid": "LEGITEXT000006069565",
    },
    "travail": {
        "title": "Code du travail",
        "texte_cid": "LEGITEXT000006072050",
    },
}
TITLE_TO_CODE = {v["title"]: k for k, v in CODE_META.items()}
CID_TO_CODE = {v["texte_cid"]: k for k, v in CODE_META.items()}

SNAPSHOT_ID = "codes-v0.2-2025-07-13"
DUMP_FILE_HF = "Freemium_legi_global_20250713-140000.tar.gz"
DUMP_URL_HF = (
    "https://echanges.dila.gouv.fr/OPENDATA/LEGI/"
    "Freemium_legi_global_20250713-140000.tar.gz"
)
HF_DATASET = "VinceGx33/legi-french-law-2025"


def _strip_html(text: str) -> str:
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _load_mvp_overrides(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    if str(path).endswith(".gz"):
        import gzip

        with gzip.open(path, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))
    return {a["id"]: a for a in raw.get("articles", [])}


def build_articles_from_parquet(
    parquet_path: Path,
    mvp_path: Path,
) -> tuple[list[Article], list[ArticleVersion], dict]:
    import pandas as pd

    df = pd.read_parquet(parquet_path)
    mask = df["texte_titre"].isin(TITLE_TO_CODE)
    sub = df[mask].copy()
    mvp = _load_mvp_overrides(mvp_path)

    articles: list[Article] = []
    tip_versions: list[ArticleVersion] = []
    seen_ids: set[str] = set()

    for row in sub.itertuples(index=False):
        article_id = str(row.article_id)
        if article_id in seen_ids:
            continue
        seen_ids.add(article_id)
        code = TITLE_TO_CODE[str(row.texte_titre)]
        texte_cid = CODE_META[code]["texte_cid"]
        contexte = str(row.texte_contexte or "")
        hier = parse_contexte(contexte)
        text = str(row.article_contenu_text or "").strip()
        raw_num = str(row.article_num or "").strip()
        num = normalize_article_num(raw_num) or raw_num

        # Keep MVP LEGIARTI ids + surface nums stable for gold / CI.
        if article_id in mvp:
            prev = mvp[article_id]
            num = prev.get("num") or num
            text = prev.get("text") or text
            contexte = prev.get("contexte") or contexte
            hier = parse_contexte(contexte)

        title = f"Article {num}" if num else f"Article {article_id}"
        art = Article(
            id=article_id,
            num=num,
            title=title,
            text=text,
            texte_cid=texte_cid,
            etat=str(row.article_etat or "VIGUEUR"),
            contexte=contexte,
            code=code,
            livre=hier.livre,
            titre=hier.titre,
            chapitre=hier.chapitre,
        )
        articles.append(art)

        debut = parse_legi_date(getattr(row, "date_debut", None))
        fin = parse_legi_date(getattr(row, "date_fin", None))
        tip_versions.append(
            ArticleVersion(
                version_id=article_id,
                article_id=article_id,
                num=num,
                text=text,
                etat=str(row.article_etat or "VIGUEUR"),
                debut=debut,
                fin=fin,
                titre=title,
            )
        )

    # Ensure every MVP id remains even if parquet filtering missed it.
    by_id = {a.id: a for a in articles}
    for mid, prev in mvp.items():
        if mid in by_id:
            continue
        hier = parse_contexte(prev.get("contexte") or "")
        art = Article(
            id=mid,
            num=prev["num"],
            title=prev.get("title") or f"Article {prev['num']}",
            text=prev["text"],
            texte_cid=prev.get("texte_cid") or CODE_META["consommation"]["texte_cid"],
            etat=prev.get("etat") or "VIGUEUR",
            contexte=prev.get("contexte") or "",
            code="consommation",
            livre=hier.livre,
            titre=hier.titre,
            chapitre=hier.chapitre,
        )
        articles.append(art)
        tip_versions.append(
            ArticleVersion(
                version_id=mid,
                article_id=mid,
                num=art.num,
                text=art.text,
                etat=art.etat,
                debut=None,
                fin=None,
                titre=art.title,
            )
        )

    articles.sort(key=lambda a: (a.code or "", a.num, a.id))
    tip_versions.sort(key=lambda v: (v.article_id, v.debut or date.min, v.version_id))

    source = {
        "producer": "DILA (Direction de l'information légale et administrative)",
        "dataset": "LEGI — Codes, lois et règlements consolidés",
        "textes": [
            {
                "code": code,
                "titre": meta["title"],
                "texte_cid": meta["texte_cid"],
            }
            for code, meta in CODE_META.items()
        ],
        "licence": "Licence Ouverte / Open Licence 2.0 (Etalab)",
        "licence_url": "https://www.etalab.gouv.fr/licence-ouverte-open-licence/",
        "download_url": DUMP_URL_HF,
        "dump_file": DUMP_FILE_HF,
        "dump_date": "2025-07-13",
        "data_gouv": (
            "https://www.data.gouv.fr/datasets/legi-codes-lois-et-reglements-consolides"
        ),
        "derived_via": (
            f"Hugging Face dataset {HF_DATASET} (etalab-2.0), "
            "filtré (civil / consommation / travail) puis gelé"
        ),
        "snapshot_id": SNAPSHOT_ID,
        "freeze_date": date.today().isoformat(),
        "n_articles": len(articles),
        "note": (
            "Snapshot figé à des fins d'évaluation RAG. "
            "Ne constitue pas une base juridique opposable. "
            "Ids LEGIARTI du gold MVP conservés."
        ),
    }
    return articles, tip_versions, source


def _xml_text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return "".join(el.itertext())


def parse_article_xml(xml_bytes: bytes) -> dict | None:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    meta = root.find("./META/META_COMMUN")
    if meta is None:
        return None
    article_id = (meta.findtext("ID") or "").strip()
    if not article_id.startswith("LEGIARTI"):
        return None
    cid = (meta.findtext("CID") or article_id).strip()
    etat = (meta.findtext("ETAT") or "").strip() or "VIGUEUR"
    num = (root.findtext("./META/META_SPEC/META_ARTICLE/NUM") or "").strip()
    debut = parse_legi_date(root.findtext("./META/META_SPEC/META_ARTICLE/DATE_DEBUT"))
    fin = parse_legi_date(root.findtext("./META/META_SPEC/META_ARTICLE/DATE_FIN"))
    texte_cid = None
    contexte_el = root.find("./CONTEXTE/TEXTE")
    if contexte_el is not None:
        texte_cid = (
            contexte_el.attrib.get("cid")
            or contexte_el.attrib.get("cidTexte")
            or contexte_el.attrib.get("cidtexte")
            or (contexte_el.findtext("CID") or "").strip()
            or None
        )

    contenu = root.find("./BLOC_TEXTUEL/CONTENU")
    text = _strip_html(_xml_text(contenu)) if contenu is not None else ""

    version_links: list[dict] = []
    for version in root.findall("./VERSIONS/VERSION"):
        lien = version.find("LIEN_ART")
        if lien is None:
            continue
        version_links.append(
            {
                "version_id": lien.attrib.get("id") or "",
                "num": lien.attrib.get("num") or num,
                "etat": lien.attrib.get("etat") or version.attrib.get("etat") or "",
                "debut": parse_legi_date(lien.attrib.get("debut")),
                "fin": parse_legi_date(lien.attrib.get("fin")),
            }
        )

    return {
        "id": article_id,
        "cid": cid,
        "num": num,
        "etat": etat,
        "debut": debut,
        "fin": fin,
        "texte_cid": texte_cid,
        "text": text,
        "version_links": version_links,
    }


def enrich_versions_from_dump(
    dump_path: Path,
    tip_articles: list[Article],
    tip_versions: list[ArticleVersion],
    *,
    max_versions_per_article: int = 8,
    min_history_date: date = date(2000, 1, 1),
) -> list[ArticleVersion]:
    """Stream Freemium tar.gz and collect historical versions for our tips.

    Limits (documented in SOURCE.md): keep tip + up to
    ``max_versions_per_article - 1`` prior versions with debut >= min_history_date
    (or undated), to keep the git snapshot small.
    """
    tip_ids = {a.id for a in tip_articles}
    tip_by_id = {a.id: a for a in tip_articles}
    # Map any historical version id → tip article id once we see VERSIONS blocks
    version_to_tip: dict[str, str] = {a.id: a.id for a in tip_articles}
    # Also match by (texte_cid, normalized num) → tip id
    tip_by_key: dict[tuple[str, str], str] = {}
    for a in tip_articles:
        if a.texte_cid:
            tip_by_key[(a.texte_cid, normalize_article_num(a.num))] = a.id

    parsed_by_id: dict[str, dict] = {}
    wanted_cids = set(CID_TO_CODE)
    # Path fragments for the three codes (LEGI store splits CID into dirs).
    path_needles = tuple(wanted_cids) + tuple(
        "/".join((cid[8:10], cid[10:12], cid[12:14], cid[14:16], cid[16:18], cid[18:20]))
        for cid in wanted_cids
    )

    def _path_interesting(name: str) -> bool:
        if not name.endswith(".xml"):
            return False
        lower = name.lower()
        if "article" not in lower and "legiarti" not in lower:
            return False
        return any(n in name for n in path_needles)

    print(f"Streaming LEGI dump for versions: {dump_path}", flush=True)
    n_seen = 0
    with tarfile.open(dump_path, "r:gz") as tar:
        for member in tar:
            name = member.name
            if not _path_interesting(name):
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            parsed = parse_article_xml(extracted.read())
            n_seen += 1
            if n_seen % 2000 == 0:
                print(f"  …parsed {n_seen} candidate XML files", flush=True)
            if not parsed:
                continue
            texte_cid = parsed.get("texte_cid")
            if (
                texte_cid not in wanted_cids
                and parsed["id"] not in tip_ids
                and not any(v.get("version_id") in tip_ids for v in parsed["version_links"])
            ):
                continue

            parsed_by_id[parsed["id"]] = parsed
            tip_id = None
            for link in parsed["version_links"]:
                vid = link.get("version_id") or ""
                if vid in tip_ids:
                    tip_id = vid
                    break
            if tip_id is None and parsed["id"] in tip_ids:
                tip_id = parsed["id"]
            if tip_id is None and texte_cid:
                key = (texte_cid, normalize_article_num(parsed["num"]))
                tip_id = tip_by_key.get(key)
            if tip_id is None:
                continue
            version_to_tip[parsed["id"]] = tip_id
            for link in parsed["version_links"]:
                vid = link.get("version_id") or ""
                if vid:
                    version_to_tip[vid] = tip_id

    missing = set()
    for tip_id in tip_ids:
        parsed = parsed_by_id.get(tip_id)
        if not parsed:
            continue
        for link in parsed["version_links"]:
            vid = link.get("version_id") or ""
            if vid and vid not in parsed_by_id:
                missing.add(vid)

    if missing:
        print(f"Second pass for {len(missing)} linked historical versions…", flush=True)
        with tarfile.open(dump_path, "r:gz") as tar:
            for member in tar:
                if not member.name.endswith(".xml"):
                    continue
                base = Path(member.name).stem
                if base not in missing:
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                parsed = parse_article_xml(extracted.read())
                if parsed:
                    parsed_by_id[parsed["id"]] = parsed
    print(f"Parsed {n_seen} XML files; {len(parsed_by_id)} unique article ids", flush=True)

    # Assemble ArticleVersion list
    by_tip: dict[str, list[ArticleVersion]] = defaultdict(list)
    # Start with tip versions from parquet (authoritative text for tip ids)
    for ver in tip_versions:
        by_tip[ver.article_id].append(ver)

    for vid, tip_id in version_to_tip.items():
        if tip_id not in tip_ids:
            continue
        if vid == tip_id:
            continue  # tip already present
        parsed = parsed_by_id.get(vid)
        tip_art = tip_by_id[tip_id]
        if parsed is None:
            # metadata-only from tip's VERSIONS links
            tip_parsed = parsed_by_id.get(tip_id)
            link_meta = None
            if tip_parsed:
                link_meta = next(
                    (L for L in tip_parsed["version_links"] if L.get("version_id") == vid),
                    None,
                )
            if not link_meta:
                continue
            debut, fin = link_meta.get("debut"), link_meta.get("fin")
            if debut is not None and debut < min_history_date:
                continue
            by_tip[tip_id].append(
                ArticleVersion(
                    version_id=vid,
                    article_id=tip_id,
                    num=normalize_article_num(link_meta.get("num") or tip_art.num)
                    or tip_art.num,
                    text="",  # metadata-only placeholder omitted below if empty
                    etat=link_meta.get("etat") or "MODIFIE",
                    debut=debut,
                    fin=fin,
                    titre=f"Article {tip_art.num}",
                )
            )
            continue

        debut, fin = parsed["debut"], parsed["fin"]
        if debut is not None and debut < min_history_date and vid not in tip_ids:
            continue
        text = parsed["text"]
        if not text:
            continue
        by_tip[tip_id].append(
            ArticleVersion(
                version_id=vid,
                article_id=tip_id,
                num=normalize_article_num(parsed["num"]) or tip_art.num,
                text=text,
                etat=parsed["etat"],
                debut=debut,
                fin=fin,
                titre=f"Article {normalize_article_num(parsed['num']) or tip_art.num}",
            )
        )

    out: list[ArticleVersion] = []
    for tip_id, versions in by_tip.items():
        # Dedupe by version_id; prefer non-empty text
        best: dict[str, ArticleVersion] = {}
        for ver in versions:
            prev = best.get(ver.version_id)
            if prev is None or (not prev.text and ver.text):
                best[ver.version_id] = ver
        ordered = sorted(
            best.values(),
            key=lambda v: (v.debut or date.min, v.version_id),
            reverse=True,
        )
        # Always keep tip id first among retained
        tip = [v for v in ordered if v.version_id == tip_id]
        others = [v for v in ordered if v.version_id != tip_id and v.text]
        kept = tip + others[: max(0, max_versions_per_article - len(tip))]
        out.extend(kept)

    out.sort(key=lambda v: (v.article_id, v.debut or date.min, v.version_id))
    print(f"Versions after dump enrich: {len(out)}", flush=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parquet",
        type=Path,
        default=Path("/tmp/legi-build/legi_french_law.parquet"),
        help="Path to LEGI parquet (HF dataset)",
    )
    parser.add_argument(
        "--dump",
        type=Path,
        default=None,
        help="Optional Freemium LEGI tar.gz for version history",
    )
    parser.add_argument(
        "--mvp",
        type=Path,
        default=ROOT / "data" / "corpus" / "mvp_seed.json.gz",
        help="MVP seed (ids/text) to keep LEGIARTI ids stable",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "data" / "corpus",
        help="Output directory for snapshot files",
    )
    parser.add_argument(
        "--max-versions-per-article",
        type=int,
        default=8,
    )
    parser.add_argument(
        "--min-history-date",
        type=date.fromisoformat,
        default=date(2000, 1, 1),
    )
    args = parser.parse_args()

    if not args.parquet.is_file():
        print(f"Missing parquet: {args.parquet}", file=sys.stderr)
        return 1

    mvp_path = args.mvp
    if not mvp_path.is_file():
        # After first build, MVP may only exist as gz — try reading previous tips
        alt = args.out_dir / "articles.json"
        mvp_path = alt if alt.is_file() else mvp_path

    articles, tip_versions, source = build_articles_from_parquet(args.parquet, mvp_path)
    print(
        f"Articles: {len(articles)} "
        f"(civil={sum(a.code=='civil' for a in articles)}, "
        f"consommation={sum(a.code=='consommation' for a in articles)}, "
        f"travail={sum(a.code=='travail' for a in articles)})",
        flush=True,
    )

    versions = tip_versions
    if args.dump and args.dump.is_file():
        source["version_dump_file"] = args.dump.name
        source["version_dump_url"] = (
            f"https://echanges.dila.gouv.fr/OPENDATA/LEGI/{args.dump.name}"
        )
        source["version_limits"] = {
            "max_versions_per_article": args.max_versions_per_article,
            "min_history_date": args.min_history_date.isoformat(),
        }
        versions = enrich_versions_from_dump(
            args.dump,
            articles,
            tip_versions,
            max_versions_per_article=args.max_versions_per_article,
            min_history_date=args.min_history_date,
        )
    else:
        print("No dump provided — tip-only ArticleVersion rows from parquet.", flush=True)

    crossrefs = build_crossrefs(articles)
    print(f"CrossRefs: {len(crossrefs)}", flush=True)

    source["n_versions"] = len(versions)
    source["n_crossrefs"] = len(crossrefs)

    paths = write_corpus_snapshot(
        articles=articles,
        source=source,
        versions=versions,
        crossrefs=crossrefs,
        articles_path=args.out_dir / "articles.json.gz",
        versions_path=args.out_dir / "versions.json.gz",
        crossrefs_path=args.out_dir / "crossrefs.json.gz",
    )
    # Keep a tiny uncompressed manifest for humans / CI discovery
    manifest = {
        "snapshot_id": SNAPSHOT_ID,
        "files": {k: v.name for k, v in paths.items()},
        "n_articles": len(articles),
        "n_versions": len(versions),
        "n_crossrefs": len(crossrefs),
        "articles_by_code": {
            code: sum(1 for a in articles if a.code == code) for code in CODE_META
        },
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Wrote:", {k: str(v) for k, v in paths.items()}, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
