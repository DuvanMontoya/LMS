# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from domain.courses.models import Course

from .canonical import canonical_json_bytes
from .models import CoursePublication, CourseRelease
from .schemas import CURRENT_RELEASE_SCHEMA_VERSION, validate_release_snapshot
from .snapshots import snapshot_metrics


@dataclass(frozen=True)
class IntegrityIssue:
    code: str
    release_number: int | None
    detail: str


@dataclass(frozen=True)
class IntegrityResult:
    valid: bool
    checked_releases: int
    issues: tuple[IntegrityIssue, ...]


def verify_release(release: CourseRelease) -> IntegrityResult:
    issues: list[IntegrityIssue] = []

    def add(code: str, detail: str) -> None:
        issues.append(IntegrityIssue(code, release.number, detail))

    if release.schema_version != CURRENT_RELEASE_SCHEMA_VERSION:
        add("schema_unsupported", "La versión del schema no está soportada.")
    try:
        validate_release_snapshot(release.snapshot)
    except Exception:
        add("snapshot_invalid", "El snapshot no cumple el contrato.")
        return IntegrityResult(False, 1, tuple(issues))
    canonical = canonical_json_bytes(release.snapshot)
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != release.snapshot_digest:
        add("digest_mismatch", "El digest almacenado no coincide.")
    if len(canonical) != release.snapshot_size_bytes:
        add("size_mismatch", "El tamaño canónico no coincide.")
    snapshot = release.snapshot
    course = snapshot["course"]
    if (
        snapshot["release_number"] != release.number
        or course["id"] != str(release.course_id)
        or course["source_revision_id"] != str(release.source_revision_id)
    ):
        add("source_mismatch", "Los IDs fuente o el número no coinciden.")
    metrics = snapshot_metrics(snapshot)
    if (
        release.title != course["title"]
        or release.summary != course["summary"]
        or release.language_code != course["language_code"]
        or release.estimated_duration_minutes != course["estimated_duration_minutes"]
        or release.module_count != metrics["module_count"]
        or release.unit_count != metrics["unit_count"]
        or release.word_count != metrics["word_count"]
    ):
        add("index_mismatch", "Los metadatos indexados no coinciden.")
    expected_previous = (
        release.previous_release.snapshot_digest if release.previous_release else None
    )
    if snapshot["previous_release_digest"] != expected_previous:
        add("previous_digest_mismatch", "El vínculo de digest anterior no coincide.")
    if release.source_revision.course_id != release.course_id:
        add("revision_course_mismatch", "La revisión fuente pertenece a otro curso.")
    return IntegrityResult(not issues, 1, tuple(issues))


def verify_release_chain(course: Course) -> IntegrityResult:
    releases = list(
        CourseRelease.objects.filter(course=course)
        .select_related("previous_release", "source_revision")
        .order_by("number")
    )
    issues: list[IntegrityIssue] = []
    for index, release in enumerate(releases, start=1):
        if release.number != index:
            issues.append(
                IntegrityIssue(
                    "number_gap", release.number, "La numeración no es contigua."
                )
            )
        expected_previous = releases[index - 2] if index > 1 else None
        if release.previous_release_id != (
            expected_previous.id if expected_previous else None
        ):
            issues.append(
                IntegrityIssue(
                    "previous_link_invalid",
                    release.number,
                    "El enlace al release anterior es inválido.",
                )
            )
        result = verify_release(release)
        issues.extend(result.issues)
    publication = (
        CoursePublication.objects.filter(course=course)
        .select_related("current_release")
        .first()
    )
    if publication is not None:
        expected_current = releases[-1] if releases else None
        if (
            expected_current is None
            or publication.current_release_id != expected_current.id
        ):
            issues.append(
                IntegrityIssue(
                    "current_release_invalid",
                    publication.current_release.number,
                    "La publicación no apunta al último release.",
                )
            )
    previous_counts: dict[object, int] = {}
    for release in releases:
        if release.previous_release_id:
            previous_counts[release.previous_release_id] = (
                previous_counts.get(release.previous_release_id, 0) + 1
            )
    for previous_id, count in previous_counts.items():
        if count > 1:
            previous = next(row for row in releases if row.id == previous_id)
            issues.append(
                IntegrityIssue(
                    "chain_fork",
                    previous.number,
                    "La cadena contiene una bifurcación.",
                )
            )
    return IntegrityResult(not issues, len(releases), tuple(issues))
