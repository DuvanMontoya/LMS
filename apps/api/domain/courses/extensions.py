from __future__ import annotations

from collections.abc import Callable

from .models import CourseRevision

OutlineEnricher = Callable[[CourseRevision], None]
_OUTLINE_ENRICHERS: dict[str, OutlineEnricher] = {}


def register_outline_enricher(name: str, enricher: OutlineEnricher) -> None:
    normalized = name.strip()
    if not normalized:
        raise ValueError("El nombre del enriquecedor de outline es obligatorio.")
    if normalized in _OUTLINE_ENRICHERS:
        raise ValueError(f"El enriquecedor de outline '{normalized}' ya existe.")
    _OUTLINE_ENRICHERS[normalized] = enricher


def enrich_outline(revision: CourseRevision) -> CourseRevision:
    for name in sorted(_OUTLINE_ENRICHERS):
        _OUTLINE_ENRICHERS[name](revision)
    return revision
