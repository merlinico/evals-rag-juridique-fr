from rag_juridique.contracts.chunking import Chunk
from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef, CrossRefKind
from rag_juridique.corpus.chunking import FixedSizeChunker, chunk_articles
from rag_juridique.corpus.hierarchy import Hierarchy, normalize_article_num, parse_contexte
from rag_juridique.corpus.loader import Corpus, load_corpus, load_crossrefs, load_versions
from rag_juridique.corpus.refs import build_crossrefs, extract_reference_spans
from rag_juridique.corpus.versions import version_in_force

__all__ = [
    "Article",
    "ArticleVersion",
    "Chunk",
    "Corpus",
    "CrossRef",
    "CrossRefKind",
    "FixedSizeChunker",
    "Hierarchy",
    "build_crossrefs",
    "chunk_articles",
    "extract_reference_spans",
    "load_corpus",
    "load_crossrefs",
    "load_versions",
    "normalize_article_num",
    "parse_contexte",
    "version_in_force",
]
