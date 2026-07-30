# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false
from __future__ import annotations

import hashlib
import random
import secrets
from collections.abc import Iterable
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from domain.catalog.models import LearningObjective
from domain.learning.access import access_state
from domain.learning.choices import AccessState, EnrollmentStatus
from domain.learning.models import EnrollmentReleaseAssignment
from domain.organizations.choices import MembershipStatus
from domain.organizations.models import Organization
from domain.publishing.integrity import verify_release

from .canonical import canonical_json_bytes, content_digest, deep_json_copy
from .choices import (
    AssignmentStatus,
    AttemptEventType,
    AttemptStatus,
    AuthoringStatus,
    DeliveryStatus,
    LifecycleStatus,
    ResponseStatus,
)
from .exceptions import (
    AssessmentConflict,
    AssessmentForbidden,
    AssessmentInvalid,
    AssessmentNotReady,
    AttemptExpired,
    AttemptUnavailable,
)
from .models import (
    Assessment,
    AssessmentDelivery,
    AssessmentItem,
    AssessmentItemObjective,
    AssessmentRevision,
    AssessmentRevisionObjective,
    AssessmentRevisionTransition,
    AssessmentSection,
    AssessmentVersion,
    Attempt,
    AttemptEvent,
    AttemptItem,
    DeliveryAssignment,
    ManualGradeDecision,
    Question,
    QuestionBank,
    QuestionBankVersion,
    QuestionRevision,
    QuestionRevisionTransition,
    QuestionVersion,
    Response,
)
from .schemas import (
    CURRENT_ASSESSMENT_SCHEMA_VERSION,
    validate_assessment_snapshot,
    validate_public_question,
    validate_question_definition,
    validate_response,
)
from .scoring import basis_points, quantize_score, score_question

OPEN_AUTHORING_STATUSES = {
    AuthoringStatus.DRAFT,
    AuthoringStatus.IN_REVIEW,
    AuthoringStatus.CHANGES_REQUESTED,
}
EDITABLE_AUTHORING_STATUSES = {
    AuthoringStatus.DRAFT,
    AuthoringStatus.CHANGES_REQUESTED,
}


def _actor_id(actor: object) -> object:
    actor_id = getattr(actor, "pk", None)
    if actor_id is None:
        raise AssessmentForbidden("Se requiere un actor autenticado.")
    return actor_id


def _raise_validation(error: ValidationError) -> None:
    if hasattr(error, "message_dict"):
        first_field, messages = next(iter(error.message_dict.items()))
        message = messages[0] if messages else "El registro no es válido."
        raise AssessmentInvalid(str(message), path=first_field) from error
    raise AssessmentInvalid("; ".join(error.messages)) from error


def _clean_save(instance: Any, *, update_fields: list[str] | None = None) -> None:
    try:
        instance.full_clean()
    except ValidationError as error:
        _raise_validation(error)
    instance.save(update_fields=update_fields)


def _require_expected(actual: int, expected: int) -> None:
    if actual != expected:
        raise AssessmentConflict(
            "La versión esperada ya no coincide con el estado persistido."
        )


def _next_number(queryset: Any) -> int:
    current = queryset.aggregate(maximum=Max("number"))["maximum"]
    return int(current or 0) + 1


@transaction.atomic
def create_question_bank(
    *,
    actor: object,
    organization: Organization,
    name: str,
    slug: str,
    description: str = "",
) -> QuestionBank:
    bank = QuestionBank(
        organization=organization,
        name=name,
        slug=slug,
        description=description,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )
    _clean_save(bank)
    return bank


@transaction.atomic
def update_question_bank(
    *,
    actor: object,
    bank: QuestionBank,
    expected_version: int,
    name: str,
    description: str = "",
) -> QuestionBank:
    locked = QuestionBank.objects.select_for_update().get(pk=bank.pk)
    _require_expected(locked.lock_version, expected_version)
    if locked.status != LifecycleStatus.ACTIVE:
        raise AssessmentConflict("El banco archivado no admite cambios.")
    locked.name = name
    locked.description = description
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    _clean_save(locked)
    return locked


@transaction.atomic
def archive_question_bank(
    *, actor: object, bank: QuestionBank, expected_version: int
) -> QuestionBank:
    locked = QuestionBank.objects.select_for_update().get(pk=bank.pk)
    _require_expected(locked.lock_version, expected_version)
    if locked.status == LifecycleStatus.ARCHIVED:
        return locked
    now = timezone.now()
    locked.status = LifecycleStatus.ARCHIVED
    locked.archived_by_id = _actor_id(actor)
    locked.archived_at = now
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    _clean_save(locked)
    return locked


@transaction.atomic
def create_question(
    *,
    actor: object,
    bank: QuestionBank,
    code: str,
    question_type: str,
    definition: object,
) -> tuple[Question, QuestionRevision]:
    locked_bank = QuestionBank.objects.select_for_update().get(pk=bank.pk)
    if locked_bank.status != LifecycleStatus.ACTIVE:
        raise AssessmentInvalid("No se crean preguntas en un banco archivado.")
    validated = validate_question_definition(definition)
    if validated["type"] != question_type:
        raise AssessmentInvalid("El tipo no coincide con la definición.")
    now = timezone.now()
    question = Question(
        bank=locked_bank,
        code=code,
        created_by_id=_actor_id(actor),
    )
    _clean_save(question)
    revision = QuestionRevision(
        question=question,
        number=1,
        type=question_type,
        definition=validated,
        status_changed_by_id=_actor_id(actor),
        status_changed_at=now,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )
    _clean_save(revision)
    return question, revision


def _locked_question_revision(
    revision: QuestionRevision, expected_version: int
) -> QuestionRevision:
    locked = (
        QuestionRevision.objects.select_for_update(of=("self",))
        .select_related("question__bank__organization", "based_on_version")
        .get(pk=revision.pk)
    )
    _require_expected(locked.lock_version, expected_version)
    return locked


@transaction.atomic
def update_question_revision(
    *,
    actor: object,
    revision: QuestionRevision,
    expected_version: int,
    definition: object,
) -> QuestionRevision:
    locked = _locked_question_revision(revision, expected_version)
    if locked.status not in EDITABLE_AUTHORING_STATUSES:
        raise AssessmentConflict("La revisión no está en un estado editable.")
    validated = validate_question_definition(definition)
    locked.definition = validated
    locked.type = validated["type"]
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    _clean_save(locked)
    return locked


def _question_transition_allowed(from_status: str, to_status: str) -> bool:
    return (from_status, to_status) in {
        (AuthoringStatus.DRAFT, AuthoringStatus.IN_REVIEW),
        (AuthoringStatus.CHANGES_REQUESTED, AuthoringStatus.IN_REVIEW),
        (AuthoringStatus.IN_REVIEW, AuthoringStatus.CHANGES_REQUESTED),
        (AuthoringStatus.IN_REVIEW, AuthoringStatus.APPROVED),
    }


@transaction.atomic
def transition_question_revision(
    *,
    actor: object,
    revision: QuestionRevision,
    expected_version: int,
    to_status: str,
    note: str = "",
) -> tuple[QuestionRevision, QuestionVersion | None]:
    locked = _locked_question_revision(revision, expected_version)
    from_status = locked.status
    if not _question_transition_allowed(from_status, to_status):
        raise AssessmentConflict("La transición de pregunta no está permitida.")
    validated = validate_question_definition(locked.definition)
    version: QuestionVersion | None = None
    if to_status == "approved":
        version_number = _next_number(
            QuestionVersion.objects.select_for_update().filter(question=locked.question)
        )
        public = validate_public_question(validated["public"])
        version = QuestionVersion(
            question=locked.question,
            number=version_number,
            source_revision=locked,
            schema_version=CURRENT_ASSESSMENT_SCHEMA_VERSION,
            type=locked.type,
            public=public,
            grading=deep_json_copy(validated["grading"]),
            feedback=deep_json_copy(validated["feedback"]),
            definition_digest=content_digest(validated),
            public_digest=content_digest(public),
            created_by_id=_actor_id(actor),
        )
        _clean_save(version)
    now = timezone.now()
    locked.status = to_status
    locked.status_changed_by_id = _actor_id(actor)
    locked.status_changed_at = now
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    _clean_save(locked)
    transition = QuestionRevisionTransition(
        revision=locked,
        from_status=from_status,
        to_status=to_status,
        actor_id=_actor_id(actor),
        note=note.strip(),
    )
    _clean_save(transition)
    return locked, version


@transaction.atomic
def create_question_revision_from_version(
    *, actor: object, version: QuestionVersion
) -> QuestionRevision:
    question = Question.objects.select_for_update().get(pk=version.question_id)
    if question.status != LifecycleStatus.ACTIVE:
        raise AssessmentConflict("La pregunta está archivada.")
    if QuestionRevision.objects.filter(
        question=question, status__in=OPEN_AUTHORING_STATUSES
    ).exists():
        raise AssessmentConflict("La pregunta ya tiene una revisión abierta.")
    definition = {
        "schema_version": CURRENT_ASSESSMENT_SCHEMA_VERSION,
        "type": version.type,
        "public": deep_json_copy(version.public),
        "grading": deep_json_copy(version.grading),
        "feedback": deep_json_copy(version.feedback),
    }
    now = timezone.now()
    revision = QuestionRevision(
        question=question,
        number=_next_number(
            QuestionRevision.objects.select_for_update().filter(question=question)
        ),
        based_on_version=version,
        type=version.type,
        definition=definition,
        status_changed_by_id=_actor_id(actor),
        status_changed_at=now,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )
    _clean_save(revision)
    return revision


@transaction.atomic
def create_question_bank_version(
    *, actor: object, bank: QuestionBank
) -> QuestionBankVersion:
    locked = QuestionBank.objects.select_for_update().get(pk=bank.pk)
    questions = list(
        Question.objects.filter(bank=locked, status=LifecycleStatus.ACTIVE).order_by(
            "code", "id"
        )
    )
    entries: list[dict[str, Any]] = []
    for question in questions:
        version = question.versions.order_by("-number").first()
        if version is None:
            raise AssessmentNotReady(
                f"La pregunta {question.code} no tiene una versión aprobada."
            )
        entries.append(
            {
                "question_id": str(question.id),
                "code": question.code,
                "question_version_id": str(version.id),
                "version_number": version.number,
                "type": version.type,
                "public_digest": version.public_digest,
            }
        )
    snapshot = {
        "schema_version": CURRENT_ASSESSMENT_SCHEMA_VERSION,
        "bank_id": str(locked.id),
        "questions": entries,
    }
    digest = content_digest(snapshot)
    previous = (
        QuestionBankVersion.objects.select_for_update()
        .filter(bank=locked)
        .order_by("-number")
        .first()
    )
    if previous and previous.snapshot_digest == digest:
        raise AssessmentConflict("El banco no cambió desde su última versión.")
    version = QuestionBankVersion(
        bank=locked,
        number=(previous.number + 1 if previous else 1),
        previous_version=previous,
        snapshot=snapshot,
        snapshot_digest=digest,
        question_count=len(entries),
        created_by_id=_actor_id(actor),
    )
    _clean_save(version)
    return version


@transaction.atomic
def create_assessment(
    *,
    actor: object,
    organization: Organization,
    slug: str,
    title: str,
    description: str = "",
    instructions: str = "",
    time_limit_minutes: int | None = None,
    attempt_limit: int | None = None,
    pass_basis_points: int = 6_000,
    shuffle_sections: bool = False,
    shuffle_items: bool = False,
    feedback_mode: str = "full_after_grading",
) -> tuple[Assessment, AssessmentRevision]:
    assessment = Assessment(
        organization=organization,
        slug=slug,
        created_by_id=_actor_id(actor),
    )
    _clean_save(assessment)
    now = timezone.now()
    revision = AssessmentRevision(
        assessment=assessment,
        number=1,
        title=title,
        description=description,
        instructions=instructions,
        time_limit_minutes=time_limit_minutes,
        attempt_limit=attempt_limit,
        pass_basis_points=pass_basis_points,
        shuffle_sections=shuffle_sections,
        shuffle_items=shuffle_items,
        feedback_mode=feedback_mode,
        status_changed_by_id=_actor_id(actor),
        status_changed_at=now,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )
    _clean_save(revision)
    return assessment, revision


def _locked_assessment_revision(
    revision: AssessmentRevision, expected_version: int
) -> AssessmentRevision:
    locked = (
        AssessmentRevision.objects.select_for_update(of=("self",))
        .select_related("assessment__organization", "based_on_version")
        .get(pk=revision.pk)
    )
    _require_expected(locked.lock_version, expected_version)
    return locked


def _require_editable(revision: AssessmentRevision) -> None:
    if revision.status not in EDITABLE_AUTHORING_STATUSES:
        raise AssessmentConflict("La revisión no está en un estado editable.")


@transaction.atomic
def update_assessment_revision(
    *,
    actor: object,
    revision: AssessmentRevision,
    expected_version: int,
    values: dict[str, object],
) -> AssessmentRevision:
    locked = _locked_assessment_revision(revision, expected_version)
    _require_editable(locked)
    allowed = {
        "title",
        "description",
        "instructions",
        "time_limit_minutes",
        "attempt_limit",
        "pass_basis_points",
        "shuffle_sections",
        "shuffle_items",
        "feedback_mode",
    }
    for field, value in values.items():
        if field in allowed:
            setattr(locked, field, value)
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    _clean_save(locked)
    return locked


@transaction.atomic
def replace_assessment_objectives(
    *,
    actor: object,
    revision: AssessmentRevision,
    expected_version: int,
    objectives: Iterable[LearningObjective],
) -> AssessmentRevision:
    locked = _locked_assessment_revision(revision, expected_version)
    _require_editable(locked)
    unique: list[LearningObjective] = []
    seen: set[object] = set()
    for objective in objectives:
        if objective.pk in seen:
            continue
        if objective.organization.id != locked.organization.id:
            raise AssessmentInvalid("Un objetivo pertenece a otra organización.")
        seen.add(objective.pk)
        unique.append(objective)
    AssessmentRevisionObjective.objects.filter(revision=locked).delete()
    AssessmentRevisionObjective.objects.bulk_create(
        [
            AssessmentRevisionObjective(
                revision=locked,
                objective=objective,
                position=index,
                created_by_id=_actor_id(actor),
            )
            for index, objective in enumerate(unique, start=1)
        ]
    )
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    locked.save(update_fields=["updated_by", "lock_version", "updated_at"])
    return locked


@transaction.atomic
def add_assessment_section(
    *,
    actor: object,
    revision: AssessmentRevision,
    expected_version: int,
    title: str,
    instructions: str = "",
) -> tuple[AssessmentRevision, AssessmentSection]:
    locked = _locked_assessment_revision(revision, expected_version)
    _require_editable(locked)
    position = (
        locked.sections.select_for_update().aggregate(maximum=Max("position"))[
            "maximum"
        ]
        or 0
    ) + 1
    section = AssessmentSection(
        revision=locked,
        title=title,
        instructions=instructions,
        position=position,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )
    _clean_save(section)
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    locked.save(update_fields=["updated_by", "lock_version", "updated_at"])
    return locked, section


def _require_exact_order(
    *, submitted_ids: Iterable[object], existing_ids: Iterable[object], label: str
) -> list[object]:
    submitted = list(submitted_ids)
    existing = list(existing_ids)
    if (
        len(submitted) != len(existing)
        or len(set(submitted)) != len(submitted)
        or set(submitted) != set(existing)
    ):
        raise AssessmentInvalid(
            f"El orden de {label} debe incluir cada registro exactamente una vez."
        )
    return submitted


@transaction.atomic
def update_assessment_section(
    *,
    actor: object,
    revision: AssessmentRevision,
    section: AssessmentSection,
    expected_version: int,
    title: str,
    instructions: str,
) -> tuple[AssessmentRevision, AssessmentSection]:
    locked = _locked_assessment_revision(revision, expected_version)
    _require_editable(locked)
    locked_section = AssessmentSection.objects.select_for_update().get(pk=section.pk)
    if locked_section.revision_id != locked.id:
        raise AssessmentInvalid("La sección pertenece a otra revisión.")
    locked_section.title = title
    locked_section.instructions = instructions
    locked_section.updated_by_id = _actor_id(actor)
    _clean_save(locked_section)
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    locked.save(update_fields=["updated_by", "lock_version", "updated_at"])
    return locked, locked_section


@transaction.atomic
def reorder_assessment_sections(
    *,
    actor: object,
    revision: AssessmentRevision,
    expected_version: int,
    section_ids: Iterable[object],
) -> AssessmentRevision:
    locked = _locked_assessment_revision(revision, expected_version)
    _require_editable(locked)
    sections = list(locked.sections.select_for_update().order_by("position", "id"))
    ordered = _require_exact_order(
        submitted_ids=section_ids,
        existing_ids=(section.id for section in sections),
        label="secciones",
    )
    by_id = {section.id: section for section in sections}
    for position, section_id in enumerate(ordered, start=1):
        section = by_id[section_id]
        if section.position != position:
            section.position = position
            section.updated_by_id = _actor_id(actor)
            section.save(update_fields=["position", "updated_by", "updated_at"])
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    locked.save(update_fields=["updated_by", "lock_version", "updated_at"])
    return locked


@transaction.atomic
def add_assessment_item(
    *,
    actor: object,
    revision: AssessmentRevision,
    expected_version: int,
    section: AssessmentSection,
    question_version: QuestionVersion,
    points: Decimal,
    required: bool,
    objectives: Iterable[LearningObjective],
) -> tuple[AssessmentRevision, AssessmentItem]:
    locked = _locked_assessment_revision(revision, expected_version)
    _require_editable(locked)
    locked_section = AssessmentSection.objects.select_for_update().get(pk=section.pk)
    if locked_section.revision_id != locked.id:
        raise AssessmentInvalid("La sección pertenece a otra revisión.")
    if question_version.question.organization.id != locked.organization.id:
        raise AssessmentInvalid("La pregunta pertenece a otra organización.")
    if AssessmentItem.objects.filter(
        section__revision=locked, question_version=question_version
    ).exists():
        raise AssessmentInvalid(
            "Una versión de pregunta no puede repetirse en la evaluación."
        )
    position = (
        locked_section.items.select_for_update().aggregate(maximum=Max("position"))[
            "maximum"
        ]
        or 0
    ) + 1
    item = AssessmentItem(
        section=locked_section,
        question_version=question_version,
        position=position,
        points=quantize_score(points),
        required=required,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )
    _clean_save(item)
    allowed_objectives = {
        link.objective_id
        for link in locked.objective_links.select_related("objective").all()
    }
    objective_list: list[LearningObjective] = []
    seen: set[object] = set()
    for objective in objectives:
        if objective.pk in seen:
            continue
        if objective.pk not in allowed_objectives:
            raise AssessmentInvalid(
                "El objetivo del ítem no pertenece a la evaluación."
            )
        seen.add(objective.pk)
        objective_list.append(objective)
    AssessmentItemObjective.objects.bulk_create(
        [
            AssessmentItemObjective(
                item=item,
                objective=objective,
                position=index,
                created_by_id=_actor_id(actor),
            )
            for index, objective in enumerate(objective_list, start=1)
        ]
    )
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    locked.save(update_fields=["updated_by", "lock_version", "updated_at"])
    return locked, item


@transaction.atomic
def update_assessment_item(
    *,
    actor: object,
    revision: AssessmentRevision,
    item: AssessmentItem,
    expected_version: int,
    points: Decimal,
    required: bool,
    objectives: Iterable[LearningObjective],
) -> tuple[AssessmentRevision, AssessmentItem]:
    locked = _locked_assessment_revision(revision, expected_version)
    _require_editable(locked)
    locked_item = (
        AssessmentItem.objects.select_for_update()
        .select_related("section")
        .get(pk=item.pk)
    )
    if locked_item.section.revision_id != locked.id:
        raise AssessmentInvalid("El ítem pertenece a otra revisión.")
    allowed_objectives = set(
        locked.objective_links.values_list("objective_id", flat=True)
    )
    objective_list: list[LearningObjective] = []
    seen: set[object] = set()
    for objective in objectives:
        if objective.pk in seen:
            continue
        if objective.pk not in allowed_objectives:
            raise AssessmentInvalid(
                "El objetivo del ítem no pertenece a la evaluación."
            )
        seen.add(objective.pk)
        objective_list.append(objective)
    locked_item.points = quantize_score(points)
    locked_item.required = required
    locked_item.updated_by_id = _actor_id(actor)
    _clean_save(locked_item)
    AssessmentItemObjective.objects.filter(item=locked_item).delete()
    AssessmentItemObjective.objects.bulk_create(
        [
            AssessmentItemObjective(
                item=locked_item,
                objective=objective,
                position=position,
                created_by_id=_actor_id(actor),
            )
            for position, objective in enumerate(objective_list, start=1)
        ]
    )
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    locked.save(update_fields=["updated_by", "lock_version", "updated_at"])
    return locked, locked_item


@transaction.atomic
def reorder_assessment_items(
    *,
    actor: object,
    revision: AssessmentRevision,
    section: AssessmentSection,
    expected_version: int,
    item_ids: Iterable[object],
) -> AssessmentRevision:
    locked = _locked_assessment_revision(revision, expected_version)
    _require_editable(locked)
    locked_section = AssessmentSection.objects.select_for_update().get(pk=section.pk)
    if locked_section.revision_id != locked.id:
        raise AssessmentInvalid("La sección pertenece a otra revisión.")
    items = list(locked_section.items.select_for_update().order_by("position", "id"))
    ordered = _require_exact_order(
        submitted_ids=item_ids,
        existing_ids=(item.id for item in items),
        label="ítems",
    )
    by_id = {item.id: item for item in items}
    for position, item_id in enumerate(ordered, start=1):
        item = by_id[item_id]
        if item.position != position:
            item.position = position
            item.updated_by_id = _actor_id(actor)
            item.save(update_fields=["position", "updated_by", "updated_at"])
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    locked.save(update_fields=["updated_by", "lock_version", "updated_at"])
    return locked


def assessment_readiness(revision: AssessmentRevision) -> tuple[str, ...]:
    issues: list[str] = []
    if not revision.title.strip():
        issues.append("title_required")
    objective_ids = set(revision.objective_links.values_list("objective_id", flat=True))
    if not objective_ids:
        issues.append("assessment_objectives_required")
    sections = list(
        revision.sections.prefetch_related(
            "items__objective_links", "items__question_version"
        ).order_by("position")
    )
    if not sections:
        issues.append("section_required")
    seen_versions: set[object] = set()
    for section in sections:
        items = list(section.items.all())
        if not items:
            issues.append(f"section_empty:{section.id}")
        for item in items:
            if item.question_version_id in seen_versions:
                issues.append(f"question_version_repeated:{item.id}")
            seen_versions.add(item.question_version_id)
            item_objectives = {link.objective_id for link in item.objective_links.all()}
            if not item_objectives:
                issues.append(f"item_objectives_required:{item.id}")
            if not item_objectives.issubset(objective_ids):
                issues.append(f"item_objectives_outside_assessment:{item.id}")
    return tuple(issues)


def _objective_snapshot(objective: LearningObjective) -> dict[str, str]:
    return {
        "id": str(objective.id),
        "code": objective.code,
        "statement": objective.statement,
    }


def _build_assessment_snapshots(
    revision: AssessmentRevision,
) -> tuple[dict[str, Any], dict[str, Any], Decimal, int, int]:
    objective_links = list(
        revision.objective_links.select_related("objective").order_by("position")
    )
    objective_snapshots = [
        _objective_snapshot(link.objective) for link in objective_links
    ]
    sections = list(
        revision.sections.prefetch_related(
            "items__question_version",
            "items__objective_links__objective",
        ).order_by("position")
    )
    public_sections: list[dict[str, Any]] = []
    grading_items: list[dict[str, Any]] = []
    maximum = Decimal("0.000")
    item_count = 0
    for section in sections:
        public_items: list[dict[str, Any]] = []
        for item in section.items.all().order_by("position"):
            question = item.question_version
            validate_public_question(question.public)
            item_objectives = [
                _objective_snapshot(link.objective)
                for link in item.objective_links.all().order_by("position")
            ]
            points = quantize_score(item.points)
            maximum += points
            item_count += 1
            public_items.append(
                {
                    "id": str(item.id),
                    "question_version_id": str(question.id),
                    "position": item.position,
                    "points": format(points, "f"),
                    "required": item.required,
                    "question": deep_json_copy(question.public),
                    "objectives": item_objectives,
                }
            )
            grading_items.append(
                {
                    "assessment_item_id": str(item.id),
                    "question_version_id": str(question.id),
                    "type": question.type,
                    "grading": deep_json_copy(question.grading),
                    "feedback": deep_json_copy(question.feedback),
                    "question_digest": question.definition_digest,
                }
            )
        public_sections.append(
            {
                "id": str(section.id),
                "title": section.title,
                "instructions": section.instructions,
                "position": section.position,
                "items": public_items,
            }
        )
    public_snapshot = {
        "schema_version": CURRENT_ASSESSMENT_SCHEMA_VERSION,
        "assessment": {
            "id": str(revision.assessment_id),
            "slug": revision.assessment.slug,
            "title": revision.title,
            "description": revision.description,
        },
        "settings": {
            "time_limit_minutes": revision.time_limit_minutes,
            "attempt_limit": revision.attempt_limit,
            "pass_basis_points": revision.pass_basis_points,
            "shuffle_sections": revision.shuffle_sections,
            "shuffle_items": revision.shuffle_items,
            "feedback_mode": revision.feedback_mode,
        },
        "objectives": objective_snapshots,
        "sections": public_sections,
    }
    grading_snapshot = {
        "schema_version": CURRENT_ASSESSMENT_SCHEMA_VERSION,
        "assessment_id": str(revision.assessment_id),
        "items": grading_items,
    }
    validate_assessment_snapshot(public_snapshot)
    return (
        public_snapshot,
        grading_snapshot,
        quantize_score(maximum),
        len(public_sections),
        item_count,
    )


def _assessment_transition_allowed(from_status: str, to_status: str) -> bool:
    return (from_status, to_status) in {
        (AuthoringStatus.DRAFT, AuthoringStatus.IN_REVIEW),
        (AuthoringStatus.CHANGES_REQUESTED, AuthoringStatus.IN_REVIEW),
        (AuthoringStatus.IN_REVIEW, AuthoringStatus.CHANGES_REQUESTED),
        (AuthoringStatus.IN_REVIEW, AuthoringStatus.APPROVED),
    }


@transaction.atomic
def transition_assessment_revision(
    *,
    actor: object,
    revision: AssessmentRevision,
    expected_version: int,
    to_status: str,
    note: str = "",
) -> tuple[AssessmentRevision, AssessmentVersion | None]:
    locked = _locked_assessment_revision(revision, expected_version)
    from_status = locked.status
    if not _assessment_transition_allowed(from_status, to_status):
        raise AssessmentConflict("La transición de evaluación no está permitida.")
    version: AssessmentVersion | None = None
    if to_status in {AuthoringStatus.IN_REVIEW, AuthoringStatus.APPROVED}:
        issues = assessment_readiness(locked)
        if issues:
            raise AssessmentNotReady(
                "La evaluación no está lista: " + ", ".join(issues)
            )
    if to_status == "approved":
        (
            public_snapshot,
            grading_snapshot,
            maximum,
            section_count,
            item_count,
        ) = _build_assessment_snapshots(locked)
        previous = (
            AssessmentVersion.objects.select_for_update()
            .filter(assessment=locked.assessment)
            .order_by("-number")
            .first()
        )
        version_number = previous.number + 1 if previous else 1
        snapshot_digest = hashlib.sha256(
            canonical_json_bytes(
                {"public": public_snapshot, "grading": grading_snapshot}
            )
        ).hexdigest()
        version = AssessmentVersion(
            assessment=locked.assessment,
            number=version_number,
            source_revision=locked,
            previous_version=previous,
            schema_version=CURRENT_ASSESSMENT_SCHEMA_VERSION,
            public_snapshot=public_snapshot,
            grading_snapshot=grading_snapshot,
            snapshot_digest=snapshot_digest,
            title=locked.title,
            description=locked.description,
            section_count=section_count,
            item_count=item_count,
            maximum_score=maximum,
            time_limit_minutes=locked.time_limit_minutes,
            attempt_limit=locked.attempt_limit,
            pass_basis_points=locked.pass_basis_points,
            feedback_mode=locked.feedback_mode,
            created_by_id=_actor_id(actor),
        )
        _clean_save(version)
    now = timezone.now()
    locked.status = to_status
    locked.status_changed_by_id = _actor_id(actor)
    locked.status_changed_at = now
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    _clean_save(locked)
    transition = AssessmentRevisionTransition(
        revision=locked,
        from_status=from_status,
        to_status=to_status,
        actor_id=_actor_id(actor),
        note=note.strip(),
    )
    _clean_save(transition)
    return locked, version


@transaction.atomic
def create_assessment_revision_from_version(
    *, actor: object, version: AssessmentVersion
) -> AssessmentRevision:
    assessment = Assessment.objects.select_for_update().get(pk=version.assessment_id)
    if assessment.status != LifecycleStatus.ACTIVE:
        raise AssessmentConflict("La evaluación está archivada.")
    if AssessmentRevision.objects.filter(
        assessment=assessment, status__in=OPEN_AUTHORING_STATUSES
    ).exists():
        raise AssessmentConflict("La evaluación ya tiene una revisión abierta.")
    settings = version.public_snapshot["settings"]
    now = timezone.now()
    revision = AssessmentRevision(
        assessment=assessment,
        number=_next_number(
            AssessmentRevision.objects.select_for_update().filter(assessment=assessment)
        ),
        based_on_version=version,
        title=version.title,
        description=version.description,
        instructions="",
        time_limit_minutes=settings["time_limit_minutes"],
        attempt_limit=settings["attempt_limit"],
        pass_basis_points=settings["pass_basis_points"],
        shuffle_sections=settings["shuffle_sections"],
        shuffle_items=settings["shuffle_items"],
        feedback_mode=settings["feedback_mode"],
        status_changed_by_id=_actor_id(actor),
        status_changed_at=now,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )
    _clean_save(revision)
    objective_ids = [
        entry["id"] for entry in version.public_snapshot.get("objectives", [])
    ]
    objectives = {
        str(item.id): item
        for item in LearningObjective.objects.filter(id__in=objective_ids)
    }
    for position, entry in enumerate(
        version.public_snapshot.get("objectives", []), start=1
    ):
        objective = objectives.get(entry["id"])
        if objective:
            AssessmentRevisionObjective.objects.create(
                revision=revision,
                objective=objective,
                position=position,
                created_by_id=_actor_id(actor),
            )
    grading_by_item = {
        entry["assessment_item_id"]: entry
        for entry in version.grading_snapshot.get("items", [])
    }
    for section_data in version.public_snapshot["sections"]:
        section = AssessmentSection.objects.create(
            revision=revision,
            title=section_data["title"],
            instructions=section_data["instructions"],
            position=section_data["position"],
            created_by_id=_actor_id(actor),
            updated_by_id=_actor_id(actor),
        )
        for item_data in section_data["items"]:
            grading_entry = grading_by_item[item_data["id"]]
            question_version = QuestionVersion.objects.get(
                pk=grading_entry["question_version_id"]
            )
            item = AssessmentItem.objects.create(
                section=section,
                question_version=question_version,
                position=item_data["position"],
                points=Decimal(item_data["points"]),
                required=item_data["required"],
                created_by_id=_actor_id(actor),
                updated_by_id=_actor_id(actor),
            )
            for objective_position, objective_data in enumerate(
                item_data["objectives"], start=1
            ):
                objective = objectives.get(objective_data["id"])
                if objective:
                    AssessmentItemObjective.objects.create(
                        item=item,
                        objective=objective,
                        position=objective_position,
                        created_by_id=_actor_id(actor),
                    )
    return revision


@transaction.atomic
def create_delivery(
    *,
    actor: object,
    organization: Organization,
    assessment_version: AssessmentVersion,
    name: str,
    course_release: object | None = None,
    unit_id: object | None = None,
    opens_at: object | None = None,
    closes_at: object | None = None,
) -> AssessmentDelivery:
    delivery = AssessmentDelivery(
        organization=organization,
        assessment_version=assessment_version,
        name=name,
        course_release=course_release,
        unit_id=unit_id,
        opens_at=opens_at,
        closes_at=closes_at,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )
    _clean_save(delivery)
    return delivery


@transaction.atomic
def activate_delivery(
    *,
    actor: object,
    delivery: AssessmentDelivery,
    expected_version: int,
) -> AssessmentDelivery:
    locked = AssessmentDelivery.objects.select_for_update().get(pk=delivery.pk)
    _require_expected(locked.lock_version, expected_version)
    if locked.status == DeliveryStatus.WITHDRAWN:
        raise AssessmentConflict("Una entrega retirada no se reactiva.")
    if locked.course_release_id and not verify_release(locked.course_release).valid:
        raise AssessmentInvalid("El release vinculado no supera integridad.")
    locked.status = DeliveryStatus.ACTIVE
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    _clean_save(locked)
    return locked


@transaction.atomic
def withdraw_delivery(
    *,
    actor: object,
    delivery: AssessmentDelivery,
    expected_version: int,
    note: str,
) -> AssessmentDelivery:
    locked = AssessmentDelivery.objects.select_for_update().get(pk=delivery.pk)
    _require_expected(locked.lock_version, expected_version)
    if not note.strip():
        raise AssessmentInvalid("El retiro exige una justificación.")
    if locked.status == DeliveryStatus.WITHDRAWN:
        return locked
    locked.status = DeliveryStatus.WITHDRAWN
    locked.withdrawn_by_id = _actor_id(actor)
    locked.withdrawn_at = timezone.now()
    locked.withdrawal_note = note.strip()
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    _clean_save(locked)
    return locked


@transaction.atomic
def assign_delivery(
    *,
    actor: object,
    delivery: AssessmentDelivery,
    release_assignment: EnrollmentReleaseAssignment,
) -> DeliveryAssignment:
    locked_delivery = AssessmentDelivery.objects.select_for_update().get(pk=delivery.pk)
    locked_release_assignment = (
        EnrollmentReleaseAssignment.objects.select_for_update(of=("self",))
        .select_related(
            "enrollment__membership",
            "enrollment__cohort",
            "enrollment__current_release_assignment",
            "release__course",
        )
        .get(pk=release_assignment.pk)
    )
    enrollment = locked_release_assignment.enrollment
    if locked_delivery.status == DeliveryStatus.WITHDRAWN:
        raise AssessmentConflict("No se asigna una entrega retirada.")
    if (
        enrollment.status != EnrollmentStatus.ACTIVE
        or enrollment.membership.status != MembershipStatus.ACTIVE
        or enrollment.current_release_assignment_id != locked_release_assignment.id
        or locked_release_assignment.ended_at is not None
    ):
        raise AssessmentInvalid("La matrícula no tiene una asignación efectiva.")
    if not verify_release(locked_release_assignment.release).valid:
        raise AssessmentInvalid("El release asignado no supera integridad.")
    assignment = DeliveryAssignment(
        delivery=locked_delivery,
        release_assignment=locked_release_assignment,
        cohort=enrollment.cohort,
        assigned_by_id=_actor_id(actor),
    )
    _clean_save(assignment)
    return assignment


@transaction.atomic
def assign_delivery_batch(
    *,
    actor: object,
    delivery: AssessmentDelivery,
    release_assignments: Iterable[EnrollmentReleaseAssignment],
) -> list[DeliveryAssignment]:
    assignments = list(release_assignments)
    if not assignments:
        raise AssessmentInvalid("El lote debe incluir al menos una matrícula.")
    if len(assignments) > 100:
        raise AssessmentInvalid("El lote no puede superar 100 matrículas.")
    if len({assignment.pk for assignment in assignments}) != len(assignments):
        raise AssessmentInvalid("El lote contiene matrículas repetidas.")
    created: list[DeliveryAssignment] = []
    for release_assignment in sorted(assignments, key=lambda item: str(item.pk)):
        created.append(
            assign_delivery(
                actor=actor,
                delivery=delivery,
                release_assignment=release_assignment,
            )
        )
    return created


@transaction.atomic
def revoke_delivery_assignment(
    *, actor: object, assignment: DeliveryAssignment
) -> DeliveryAssignment:
    locked = DeliveryAssignment.objects.select_for_update().get(pk=assignment.pk)
    if locked.status == AssignmentStatus.REVOKED:
        return locked
    locked.status = AssignmentStatus.REVOKED
    locked.revoked_by_id = _actor_id(actor)
    locked.revoked_at = timezone.now()
    _clean_save(locked)
    return locked


def _require_learner_assignment(
    *, actor: object, assignment: DeliveryAssignment, at: datetime | None = None
) -> None:
    actor_id = _actor_id(actor)
    enrollment = assignment.release_assignment.enrollment
    now = at or timezone.now()
    if enrollment.membership.user_id != actor_id:
        raise AssessmentForbidden("La entrega no pertenece al estudiante.")
    if assignment.status != AssignmentStatus.ACTIVE:
        raise AttemptUnavailable("La asignación fue revocada.")
    if enrollment.current_release_assignment_id != assignment.release_assignment_id:
        raise AttemptUnavailable("La matrícula cambió de release.")
    if access_state(enrollment, at=now) != AccessState.AVAILABLE:
        raise AttemptUnavailable("La matrícula no tiene acceso efectivo.")
    delivery = assignment.delivery
    if delivery.status != DeliveryStatus.ACTIVE:
        raise AttemptUnavailable("La entrega no está activa.")
    if delivery.opens_at and now < delivery.opens_at:
        raise AttemptUnavailable("La entrega aún no está disponible.")
    if delivery.closes_at and now >= delivery.closes_at:
        raise AttemptUnavailable("La entrega ya cerró.")


def _ordered_snapshot_items(
    version: AssessmentVersion, seed: int
) -> list[tuple[dict[str, Any], dict[str, Any], int, int]]:
    generator = random.Random(seed)
    sections = [deep_json_copy(item) for item in version.public_snapshot["sections"]]
    grading = {
        item["assessment_item_id"]: item for item in version.grading_snapshot["items"]
    }
    if version.public_snapshot["settings"]["shuffle_sections"]:
        generator.shuffle(sections)
    ordered: list[tuple[dict[str, Any], dict[str, Any], int, int]] = []
    for section in sections:
        items = list(section["items"])
        if version.public_snapshot["settings"]["shuffle_items"]:
            generator.shuffle(items)
        for item in items:
            ordered.append(
                (item, grading[item["id"]], section["position"], item["position"])
            )
    return ordered


@transaction.atomic
def start_attempt(*, actor: object, assignment: DeliveryAssignment) -> Attempt:
    locked = (
        DeliveryAssignment.objects.select_for_update(of=("self",))
        .select_related(
            "delivery__assessment_version",
            "release_assignment__enrollment__membership",
            "release_assignment__enrollment__course__publication",
            "release_assignment__enrollment__current_release_assignment",
            "release_assignment__release__source_revision",
            "release_assignment__release__previous_release",
        )
        .get(pk=assignment.pk)
    )
    now = timezone.now()
    _require_learner_assignment(actor=actor, assignment=locked, at=now)
    existing = Attempt.objects.select_for_update().filter(delivery_assignment=locked)
    in_progress = existing.filter(status=AttemptStatus.IN_PROGRESS).first()
    if in_progress:
        return in_progress
    version = locked.delivery.assessment_version
    attempt_number = existing.count() + 1
    if version.attempt_limit and attempt_number > version.attempt_limit:
        raise AttemptUnavailable("Se alcanzó el límite de intentos.")
    seed = secrets.randbits(63)
    expires_at = (
        now + timedelta(minutes=version.time_limit_minutes)
        if version.time_limit_minutes
        else None
    )
    if locked.delivery.closes_at and (
        expires_at is None or locked.delivery.closes_at < expires_at
    ):
        expires_at = locked.delivery.closes_at
    attempt = Attempt(
        delivery_assignment=locked,
        assessment_version=version,
        attempt_number=attempt_number,
        seed=seed,
        started_at=now,
        expires_at=expires_at,
        maximum_score=version.maximum_score,
    )
    _clean_save(attempt)
    for display_position, (
        public_item,
        grading_item,
        section_position,
        item_position,
    ) in enumerate(_ordered_snapshot_items(version, seed), start=1):
        snapshot = {
            "public": public_item["question"],
            "grading": grading_item["grading"],
            "feedback": grading_item["feedback"],
            "points": public_item["points"],
            "required": public_item["required"],
        }
        attempt_item = AttemptItem(
            attempt=attempt,
            assessment_item_id=public_item["id"],
            question_version_id=public_item["question_version_id"],
            section_position=section_position,
            item_position=item_position,
            display_position=display_position,
            points=Decimal(public_item["points"]),
            required=public_item["required"],
            public_snapshot=deep_json_copy(public_item["question"]),
            grading_snapshot=deep_json_copy(grading_item["grading"]),
            feedback_snapshot=deep_json_copy(grading_item["feedback"]),
            snapshot_digest=content_digest(snapshot),
        )
        _clean_save(attempt_item)
    _record_attempt_event(
        attempt=attempt,
        event_type=AttemptEventType.STARTED,
        actor=actor,
        payload={"attempt_number": attempt_number},
    )
    return attempt


def _record_attempt_event(
    *,
    attempt: Attempt,
    event_type: str,
    actor: object | None,
    payload: dict[str, Any],
) -> AttemptEvent:
    event = AttemptEvent(
        attempt=attempt,
        event_type=event_type,
        actor_id=getattr(actor, "pk", None),
        payload=deep_json_copy(payload),
    )
    _clean_save(event)
    return event


def _locked_learner_attempt(
    *,
    actor: object,
    attempt: Attempt,
    expected_version: int,
    allow_expired: bool = False,
) -> Attempt:
    locked = (
        Attempt.objects.select_for_update(of=("self",))
        .select_related(
            "delivery_assignment__delivery",
            "delivery_assignment__release_assignment__enrollment__membership",
            "delivery_assignment__release_assignment__enrollment__course__publication",
            "delivery_assignment__release_assignment__enrollment__current_release_assignment",
        )
        .get(pk=attempt.pk)
    )
    _require_expected(locked.lock_version, expected_version)
    _require_learner_assignment(actor=actor, assignment=locked.delivery_assignment)
    if locked.status != AttemptStatus.IN_PROGRESS:
        raise AttemptUnavailable("El intento ya fue enviado.")
    if not allow_expired and locked.expires_at and timezone.now() >= locked.expires_at:
        raise AttemptExpired("El tiempo del intento terminó.")
    return locked


@transaction.atomic
def save_response(
    *,
    actor: object,
    attempt: Attempt,
    attempt_item: AttemptItem,
    expected_version: int,
    payload: object,
) -> tuple[Attempt, Response]:
    locked = _locked_learner_attempt(
        actor=actor,
        attempt=attempt,
        expected_version=expected_version,
    )
    item = AttemptItem.objects.get(pk=attempt_item.pk, attempt=locked)
    expected_type = str(item.public_snapshot["type"])
    validated = validate_response(payload, expected_type=expected_type)
    now = timezone.now()
    response, created = Response.objects.select_for_update().get_or_create(
        attempt_item=item,
        defaults={
            "response": validated,
            "status": ResponseStatus.SAVED,
            "saved_at": now,
        },
    )
    if not created:
        response.response = validated
        response.status = ResponseStatus.SAVED
        response.score = Decimal("0.000")
        response.saved_at = now
        response.graded_at = None
        response.grading_version += 1
        _clean_save(response)
    locked.lock_version += 1
    locked.save(update_fields=["lock_version", "updated_at"])
    _record_attempt_event(
        attempt=locked,
        event_type=AttemptEventType.RESPONSE_SAVED,
        actor=actor,
        payload={"attempt_item_id": str(item.id)},
    )
    return locked, response


def _score_attempt_locked(attempt: Attempt, *, actor: object) -> Attempt:
    items = list(attempt.items.order_by("display_position"))
    responses = {
        response.attempt_item_id: response
        for response in Response.objects.select_for_update().filter(
            attempt_item__attempt=attempt
        )
    }
    auto_score = Decimal("0.000")
    manual_score = Decimal("0.000")
    pending_manual = False
    now = timezone.now()
    for item in items:
        response = responses.get(item.id)
        if response is None:
            response = Response(
                attempt_item=item,
                response={
                    "schema_version": CURRENT_ASSESSMENT_SCHEMA_VERSION,
                    "type": item.public_snapshot["type"],
                    "value": None,
                },
                status=ResponseStatus.UNANSWERED,
                saved_at=now,
            )
        result = score_question(
            question_type=item.public_snapshot["type"],
            grading=item.grading_snapshot,
            response=response.response,
            maximum=item.points,
        )
        response.score = result.score
        response.graded_at = now
        if result.requires_manual:
            response.status = ResponseStatus.PENDING_MANUAL
            pending_manual = True
        else:
            response.status = ResponseStatus.AUTO_GRADED
            auto_score += result.score
        _clean_save(response)
    attempt.auto_score = quantize_score(auto_score)
    attempt.manual_score = quantize_score(manual_score)
    attempt.total_score = quantize_score(auto_score + manual_score)
    attempt.submitted_at = attempt.submitted_at or now
    if pending_manual:
        attempt.status = AttemptStatus.PENDING_MANUAL
        attempt.basis_points = None
        attempt.passed = None
        attempt.graded_at = None
    else:
        attempt.status = AttemptStatus.GRADED
        attempt.basis_points = basis_points(
            score=attempt.total_score, maximum=attempt.maximum_score
        )
        attempt.passed = (
            attempt.basis_points >= attempt.assessment_version.pass_basis_points
        )
        attempt.graded_at = now
    attempt.lock_version += 1
    _clean_save(attempt)
    _record_attempt_event(
        attempt=attempt,
        event_type=AttemptEventType.AUTO_GRADED,
        actor=actor,
        payload={"pending_manual": pending_manual},
    )
    if not pending_manual:
        _record_attempt_event(
            attempt=attempt,
            event_type=AttemptEventType.COMPLETED,
            actor=actor,
            payload={"basis_points": attempt.basis_points},
        )
    return attempt


@transaction.atomic
def submit_attempt(
    *, actor: object, attempt: Attempt, expected_version: int
) -> Attempt:
    locked = _locked_learner_attempt(
        actor=actor,
        attempt=attempt,
        expected_version=expected_version,
        allow_expired=True,
    )
    locked.submitted_at = timezone.now()
    _record_attempt_event(
        attempt=locked,
        event_type=AttemptEventType.SUBMITTED,
        actor=actor,
        payload={},
    )
    return _score_attempt_locked(locked, actor=actor)


@transaction.atomic
def grade_response_manually(
    *,
    actor: object,
    response: Response,
    score: Decimal,
    feedback: str,
) -> tuple[ManualGradeDecision, Attempt]:
    locked_response = (
        Response.objects.select_for_update(of=("self",))
        .select_related("attempt_item__attempt__assessment_version")
        .get(pk=response.pk)
    )
    item = locked_response.attempt_item
    attempt = Attempt.objects.select_for_update().get(pk=item.attempt_id)
    if attempt.status not in {
        AttemptStatus.PENDING_MANUAL,
        AttemptStatus.GRADED,
    } or locked_response.status not in {
        ResponseStatus.PENDING_MANUAL,
        ResponseStatus.MANUALLY_GRADED,
    }:
        raise AssessmentConflict(
            "La respuesta no admite una decisión manual o su corrección."
        )
    value = quantize_score(score)
    if value < 0 or value > item.points:
        raise AssessmentInvalid("El puntaje manual está fuera del rango del ítem.")
    sequence = (
        locked_response.manual_decisions.select_for_update().aggregate(
            maximum=Max("sequence")
        )["maximum"]
        or 0
    ) + 1
    decision = ManualGradeDecision(
        response=locked_response,
        sequence=sequence,
        score=value,
        feedback=feedback.strip(),
        actor_id=_actor_id(actor),
    )
    _clean_save(decision)
    locked_response.score = value
    locked_response.status = ResponseStatus.MANUALLY_GRADED
    locked_response.graded_at = timezone.now()
    locked_response.grading_version += 1
    _clean_save(locked_response)

    responses = list(
        Response.objects.select_for_update().filter(attempt_item__attempt=attempt)
    )
    attempt.auto_score = quantize_score(
        sum(
            (
                item.score
                for item in responses
                if item.status == ResponseStatus.AUTO_GRADED
            ),
            Decimal("0"),
        )
    )
    attempt.manual_score = quantize_score(
        sum(
            (
                item.score
                for item in responses
                if item.status == ResponseStatus.MANUALLY_GRADED
            ),
            Decimal("0"),
        )
    )
    attempt.total_score = quantize_score(attempt.auto_score + attempt.manual_score)
    pending = any(item.status == ResponseStatus.PENDING_MANUAL for item in responses)
    attempt.lock_version += 1
    if not pending:
        attempt.status = AttemptStatus.GRADED
        attempt.basis_points = basis_points(
            score=attempt.total_score, maximum=attempt.maximum_score
        )
        attempt.passed = (
            attempt.basis_points >= attempt.assessment_version.pass_basis_points
        )
        attempt.graded_at = timezone.now()
    _clean_save(attempt)
    _record_attempt_event(
        attempt=attempt,
        event_type=AttemptEventType.MANUAL_GRADED,
        actor=actor,
        payload={
            "response_id": str(locked_response.id),
            "decision_sequence": sequence,
        },
    )
    if not pending:
        _record_attempt_event(
            attempt=attempt,
            event_type=AttemptEventType.COMPLETED,
            actor=actor,
            payload={"basis_points": attempt.basis_points},
        )
    return decision, attempt
