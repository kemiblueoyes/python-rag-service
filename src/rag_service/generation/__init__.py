"""Public answer-generation API.

Imports stay lazy so ``rag_service.generation.errors`` can load without
pulling in the OpenAI provider. That provider imports
``provider_failures``, which imports these error types.
"""

from typing import Any

__all__ = [
    "AnswerGenerator",
    "GeneratedAnswer",
    "create_answer_generator",
]


def __getattr__(name: str) -> Any:
    if name == "AnswerGenerator":
        from rag_service.generation.answer_generator import (
            AnswerGenerator,
        )

        return AnswerGenerator

    if name == "GeneratedAnswer":
        from rag_service.generation.models import GeneratedAnswer

        return GeneratedAnswer

    if name == "create_answer_generator":
        from rag_service.generation.factory import (
            create_answer_generator,
        )

        return create_answer_generator

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )
