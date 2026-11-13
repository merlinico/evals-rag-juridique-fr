from rag_juridique.generation.ollama import GenerationResult, OllamaGenerator
from rag_juridique.generation.prompt import ABSTENTION_PHRASE, build_rag_prompt

__all__ = [
    "ABSTENTION_PHRASE",
    "GenerationResult",
    "OllamaGenerator",
    "build_rag_prompt",
]
