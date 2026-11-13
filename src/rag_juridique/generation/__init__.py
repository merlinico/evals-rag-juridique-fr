from rag_juridique.generation.ollama import OllamaGenerator, GenerationResult
from rag_juridique.generation.prompt import build_rag_prompt, ABSTENTION_PHRASE

__all__ = [
    "OllamaGenerator",
    "GenerationResult",
    "build_rag_prompt",
    "ABSTENTION_PHRASE",
]
