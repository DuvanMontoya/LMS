# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportOptionalMemberAccess=false, reportArgumentType=false
from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from domain.organizations.capabilities import Capability
from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.models import Membership, Organization
from domain.organizations.policies import active_roles, has_capability

from .exceptions import (
    ActiveChildrenExist,
    ActiveDependenciesExist,
    CatalogAccessDenied,
    CrossOrganizationRelation,
    DuplicateAssociation,
    PrerequisiteCycle,
    PrerequisiteSelfReference,
    PrerequisiteTargetArchived,
    TopicDepthExceeded,
    TreeIntegrityViolation,
)
from .graphs import would_create_cycle
from .models import (
    AcademicArea,
    CatalogStatus,
    Concept,
    ConceptPrerequisite,
    Discipline,
    LearningObjective,
    LearningObjectiveConcept,
    Subject,
    SubjectPrerequisite,
    SubjectTeachingResponsibility,
    Topic,
    TopicConcept,
)
from .policies import can_manage_catalog, can_manage_prerequisites


def _manage(actor: object, organization: Organization) -> None:
    if not can_manage_catalog(actor, organization):
        raise CatalogAccessDenied()


def _manage_responsibilities(actor: object, organization: Organization) -> None:
    if not has_capability(  # type: ignore[arg-type]
        actor, organization, Capability.CATALOG_TEACHING_RESPONSIBILITY_MANAGE
    ):
        raise CatalogAccessDenied()


@transaction.atomic
def assign_subject_teaching_responsibility(
    *,
    actor: object,
    organization: Organization,
    subject: Subject,
    membership: Membership,
    starts_on: date,
    ends_on: date | None,
    rationale: str,
) -> SubjectTeachingResponsibility:
    _manage_responsibilities(actor, organization)
    if (
        subject.organization.id != organization.id
        or membership.organization_id != organization.id
        or membership.status != MembershipStatus.ACTIVE.value
        or not (
            active_roles(membership)
            & {RoleCode.AUTHOR, RoleCode.REVIEWER, RoleCode.INSTRUCTOR}
        )
    ):
        raise CrossOrganizationRelation()
    responsibility = SubjectTeachingResponsibility(
        subject=subject,
        membership=membership,
        starts_on=starts_on,
        ends_on=ends_on,
        rationale=rationale,
        created_by=actor,
    )
    responsibility.full_clean()
    responsibility.save()
    return responsibility


@transaction.atomic
def close_subject_teaching_responsibility(
    *, actor: object, responsibility: SubjectTeachingResponsibility, ended_on: date
) -> SubjectTeachingResponsibility:
    _manage_responsibilities(actor, responsibility.subject.organization)
    locked = SubjectTeachingResponsibility.objects.select_for_update().get(
        pk=responsibility.pk
    )
    if locked.ended_at is not None:
        return locked
    if ended_on < locked.starts_on:
        raise ValueError("La fecha de cierre precede el inicio.")
    locked.ends_on = ended_on
    locked.ended_by = actor
    locked.ended_at = timezone.now()
    locked.full_clean()
    locked.save(update_fields=["ends_on", "ended_by", "ended_at"])
    return locked


def _save(instance: object, actor: object) -> object:
    instance.created_by = actor
    instance.updated_by = actor
    try:
        instance.full_clean()
    except ValidationError as error:
        raise ValueError(error.message_dict) from error
    instance.save()
    return instance


@transaction.atomic
def update_entity(
    *, actor: object, organization: Organization, entity: object, **data: str
) -> object:
    """Apply permitted fields through model validation without bypassing actors."""
    _manage(actor, organization)
    if entity.organization.id != organization.id:
        raise CrossOrganizationRelation()
    for field, value in data.items():
        setattr(entity, field, value)
    entity.updated_by = actor
    try:
        entity.full_clean()
    except ValidationError as error:
        raise ValueError(error.message_dict) from error
    entity.save()
    return entity


@transaction.atomic
def create_area(
    *, actor: object, organization: Organization, **data: str
) -> AcademicArea:
    _manage(actor, organization)
    return _save(AcademicArea(organization=organization, **data), actor)  # type: ignore[return-value]


@transaction.atomic
def create_discipline(
    *, actor: object, organization: Organization, area: AcademicArea, **data: str
) -> Discipline:
    _manage(actor, organization)
    if area.organization_id != organization.id:
        raise CrossOrganizationRelation()
    if area.status != CatalogStatus.ACTIVE:
        raise PrerequisiteTargetArchived()
    return _save(Discipline(area=area, **data), actor)  # type: ignore[return-value]


@transaction.atomic
def create_subject(
    *, actor: object, organization: Organization, discipline: Discipline, **data: str
) -> Subject:
    _manage(actor, organization)
    if discipline.organization.id != organization.id:
        raise CrossOrganizationRelation()
    if discipline.status != CatalogStatus.ACTIVE:
        raise PrerequisiteTargetArchived()
    return _save(Subject(discipline=discipline, **data), actor)  # type: ignore[return-value]


@transaction.atomic
def create_concept(
    *, actor: object, organization: Organization, **data: str
) -> Concept:
    _manage(actor, organization)
    return _save(Concept(organization=organization, **data), actor)  # type: ignore[return-value]


@transaction.atomic
def create_learning_objective(
    *, actor: object, organization: Organization, subject: Subject, **data: str
) -> LearningObjective:
    _manage(actor, organization)
    if (
        subject.organization.id != organization.id
        or subject.status != CatalogStatus.ACTIVE
    ):
        raise CrossOrganizationRelation()
    return _save(LearningObjective(subject=subject, **data), actor)  # type: ignore[return-value]


def _topic_data(
    actor: object, subject: Subject, data: dict[str, str]
) -> dict[str, object]:
    return {**data, "subject": subject, "created_by": actor, "updated_by": actor}


@transaction.atomic
def create_root_topic(
    *, actor: object, organization: Organization, subject: Subject, **data: str
) -> Topic:
    _manage(actor, organization)
    subject = Subject.objects.select_for_update().get(pk=subject.pk)
    if (
        subject.organization.id != organization.id
        or subject.status != CatalogStatus.ACTIVE
    ):
        raise CrossOrganizationRelation()
    node = Topic.objects.add_root(create_kwargs=_topic_data(actor, subject, data))
    _check_tree()
    return node


@transaction.atomic
def create_child_topic(
    *, actor: object, organization: Organization, parent: Topic, **data: str
) -> Topic:
    _manage(actor, organization)
    subject = Subject.objects.select_for_update().get(pk=parent.subject_id)
    parent = Topic.objects.get(pk=parent.pk)
    if (
        subject.organization.id != organization.id
        or parent.status != CatalogStatus.ACTIVE
    ):
        raise CrossOrganizationRelation()
    if parent.depth >= 8:
        raise TopicDepthExceeded()
    node = Topic.objects.add_child(
        parent, create_kwargs=_topic_data(actor, subject, data)
    )
    _check_tree()
    return node


@transaction.atomic
def move_topic(
    *,
    actor: object,
    organization: Organization,
    topic: Topic,
    target: Topic,
    pos: str = "sorted-child",
) -> Topic:
    _manage(actor, organization)
    subject = Subject.objects.select_for_update().get(pk=topic.subject_id)
    topic = Topic.objects.get(pk=topic.pk)
    target = Topic.objects.get(pk=target.pk)
    if (
        subject.organization.id != organization.id
        or topic.subject_id != target.subject_id
        or target.path.startswith(topic.path)
    ):
        raise CrossOrganizationRelation()
    if pos.endswith("child") and target.depth >= 8:
        raise TopicDepthExceeded()
    Topic.objects.move(topic, target, pos=pos)
    topic.refresh_from_db()
    _check_tree()
    return topic


def _check_tree() -> None:
    problems = Topic.objects.find_problems()
    if any(problems):
        raise TreeIntegrityViolation()


@transaction.atomic
def replace_topic_concepts(
    *,
    actor: object,
    organization: Organization,
    topic: Topic,
    concepts: Iterable[Concept],
) -> None:
    _manage(actor, organization)
    selected = list(concepts)
    if len({item.id for item in selected}) != len(selected) or any(
        item.organization_id != organization.id or item.status != CatalogStatus.ACTIVE
        for item in selected
    ):
        raise CrossOrganizationRelation()
    topic = Topic.objects.select_for_update().get(pk=topic.pk)
    _replace_ordered_concepts(
        actor=actor,
        entity=topic,
        model=TopicConcept,
        relation_field="topic",
        selected=selected,
    )


@transaction.atomic
def replace_learning_objective_concepts(
    *,
    actor: object,
    organization: Organization,
    objective: LearningObjective,
    concepts: Iterable[Concept],
) -> None:
    _manage(actor, organization)
    selected = list(concepts)
    if objective.organization.id != organization.id or any(
        item.organization_id != organization.id or item.status != CatalogStatus.ACTIVE
        for item in selected
    ):
        raise CrossOrganizationRelation()
    objective = LearningObjective.objects.select_for_update().get(pk=objective.pk)
    _replace_ordered_concepts(
        actor=actor,
        entity=objective,
        model=LearningObjectiveConcept,
        relation_field="learning_objective",
        selected=selected,
    )


def _replace_ordered_concepts(
    *,
    actor: object,
    entity: object,
    model: type[TopicConcept] | type[LearningObjectiveConcept],
    relation_field: str,
    selected: list[Concept],
) -> None:
    """Replace an ordered association without recreating unchanged links."""
    selected_ids = [concept.id for concept in selected]
    links = model.objects.select_for_update().filter(**{relation_field: entity})
    existing = {link.concept_id: link for link in links}
    model.objects.filter(**{relation_field: entity}).exclude(
        concept_id__in=selected_ids
    ).delete()
    retained_ids = [concept_id for concept_id in selected_ids if concept_id in existing]
    if retained_ids:
        # Move retained positions out of the final range before compacting them;
        # this preserves database uniqueness throughout the update.
        model.objects.filter(
            **{relation_field: entity, "concept_id__in": retained_ids}
        ).update(position=F("position") + len(selected) + len(existing))
    for position, concept in enumerate(selected):
        link = existing.get(concept.id)
        if link is None:
            model.objects.create(
                **{
                    relation_field: entity,
                    "concept": concept,
                    "position": position,
                    "created_by": actor,
                }
            )
        else:
            model.objects.filter(pk=link.pk).update(position=position)


def _replace_prerequisites(
    *,
    actor: object,
    organization: Organization,
    target: object,
    prerequisites: Iterable[tuple[object, str, str]],
    graph: str,
) -> None:
    if not can_manage_prerequisites(actor, organization):
        raise CatalogAccessDenied()
    model = SubjectPrerequisite if graph == "subject" else ConceptPrerequisite
    source_name = "subject" if graph == "subject" else "concept"
    selected = list(prerequisites)
    if len({item[0].pk for item in selected}) != len(selected):
        raise DuplicateAssociation()
    with transaction.atomic():
        Organization.objects.select_for_update().get(pk=organization.pk)
        list(
            model.objects.select_for_update().filter(
                **{
                    f"{source_name}__"
                    + (
                        "discipline__area__organization"
                        if graph == "subject"
                        else "organization"
                    ): organization
                }
            )
        )
        existing = {
            link.prerequisite_id: link
            for link in model.objects.select_for_update().filter(
                **{source_name: target}
            )
        }
        for prerequisite, _, _ in selected:
            if prerequisite.pk == target.pk:
                raise PrerequisiteSelfReference()
            target_org = target.organization
            prerequisite_org = prerequisite.organization
            if (
                target_org.id != organization.id
                or prerequisite_org.id != organization.id
            ):
                raise CrossOrganizationRelation()
            if (
                target.status != CatalogStatus.ACTIVE
                or prerequisite.status != CatalogStatus.ACTIVE
            ):
                raise PrerequisiteTargetArchived()
            if would_create_cycle(
                graph=graph,
                node_id=str(target.pk),
                prerequisite_id=str(prerequisite.pk),
            ):
                raise PrerequisiteCycle()
        selected_ids = {prerequisite.pk for prerequisite, _, _ in selected}
        model.objects.filter(**{source_name: target}).exclude(
            prerequisite_id__in=selected_ids
        ).delete()
        for prerequisite, kind, rationale in selected:
            link = existing.get(prerequisite.pk)
            if link is None:
                model.objects.create(
                    **{
                        source_name: target,
                        "prerequisite": prerequisite,
                        "kind": kind,
                        "rationale": rationale,
                        "created_by": actor,
                    }
                )
            elif link.kind != kind or link.rationale != rationale:
                model.objects.filter(pk=link.pk).update(kind=kind, rationale=rationale)


def replace_subject_prerequisites(**kwargs: object) -> None:
    _replace_prerequisites(graph="subject", **kwargs)


def replace_concept_prerequisites(**kwargs: object) -> None:
    _replace_prerequisites(graph="concept", **kwargs)


@transaction.atomic
def archive_entity(
    *, actor: object, organization: Organization, entity: object
) -> object:
    _manage(actor, organization)
    if entity.status != CatalogStatus.ACTIVE:
        return entity
    entity.status = CatalogStatus.ARCHIVED
    entity.archived_at = timezone.now()
    entity.archived_by = actor
    entity.updated_by = actor
    entity.save(
        update_fields=[
            "status",
            "archived_at",
            "archived_by",
            "updated_by",
            "updated_at",
        ]
    )
    return entity


def archive_area(
    *, actor: object, organization: Organization, area: AcademicArea
) -> AcademicArea:
    _manage(actor, organization)
    if area.organization_id != organization.id:
        raise CrossOrganizationRelation()
    if area.disciplines.filter(status=CatalogStatus.ACTIVE).exists():
        raise ActiveChildrenExist()
    return archive_entity(actor=actor, organization=organization, entity=area)  # type: ignore[return-value]


def archive_discipline(
    *, actor: object, organization: Organization, discipline: Discipline
) -> Discipline:
    _manage(actor, organization)
    if discipline.organization.id != organization.id:
        raise CrossOrganizationRelation()
    if discipline.subjects.filter(status=CatalogStatus.ACTIVE).exists():
        raise ActiveChildrenExist()
    return archive_entity(actor=actor, organization=organization, entity=discipline)  # type: ignore[return-value]


def archive_subject(
    *, actor: object, organization: Organization, subject: Subject
) -> Subject:
    _manage(actor, organization)
    if subject.organization.id != organization.id:
        raise CrossOrganizationRelation()
    if (
        subject.topics.filter(status=CatalogStatus.ACTIVE).exists()
        or subject.learning_objectives.filter(status=CatalogStatus.ACTIVE).exists()
        or subject.prerequisite_links.exists()
        or subject.dependent_links.exists()
    ):
        raise ActiveDependenciesExist()
    return archive_entity(actor=actor, organization=organization, entity=subject)  # type: ignore[return-value]


@transaction.atomic
def archive_topic_subtree(
    *, actor: object, organization: Organization, topic: Topic
) -> Topic:
    _manage(actor, organization)
    topic = Topic.objects.select_for_update().get(pk=topic.pk)
    if topic.subject.organization.id != organization.id:
        raise CrossOrganizationRelation()
    now = timezone.now()
    Topic.objects.filter(
        path__startswith=topic.path, status=CatalogStatus.ACTIVE
    ).update(
        status=CatalogStatus.ARCHIVED,
        archived_at=now,
        archived_by=actor,
        updated_by=actor,
    )
    topic.refresh_from_db()
    _check_tree()
    return topic


def archive_concept(
    *, actor: object, organization: Organization, concept: Concept
) -> Concept:
    _manage(actor, organization)
    if concept.organization_id != organization.id:
        raise CrossOrganizationRelation()
    if (
        concept.topic_links.filter(topic__status=CatalogStatus.ACTIVE).exists()
        or concept.objective_links.filter(
            learning_objective__status=CatalogStatus.ACTIVE
        ).exists()
        or concept.prerequisite_links.exists()
        or concept.dependent_links.exists()
    ):
        raise ActiveDependenciesExist()
    return archive_entity(actor=actor, organization=organization, entity=concept)  # type: ignore[return-value]


def archive_learning_objective(
    *, actor: object, organization: Organization, objective: LearningObjective
) -> LearningObjective:
    _manage(actor, organization)
    if objective.organization.id != organization.id:
        raise CrossOrganizationRelation()
    return archive_entity(actor=actor, organization=organization, entity=objective)  # type: ignore[return-value]


@transaction.atomic
def restore_entity(
    *, actor: object, organization: Organization, entity: object
) -> object:
    _manage(actor, organization)
    if entity.organization.id != organization.id:
        raise CrossOrganizationRelation()
    if isinstance(entity, Discipline) and entity.area.status != CatalogStatus.ACTIVE:
        raise ActiveDependenciesExist()
    if isinstance(entity, Subject) and entity.discipline.status != CatalogStatus.ACTIVE:
        raise ActiveDependenciesExist()
    if isinstance(entity, Topic):
        parent = Topic.objects.get_parent(entity)
        if entity.subject.status != CatalogStatus.ACTIVE or (
            parent is not None and parent.status != CatalogStatus.ACTIVE
        ):
            raise ActiveDependenciesExist()
    if (
        isinstance(entity, LearningObjective)
        and entity.subject.status != CatalogStatus.ACTIVE
    ):
        raise ActiveDependenciesExist()
    entity.status = CatalogStatus.ACTIVE
    entity.archived_at = None
    entity.archived_by = None
    entity.updated_by = actor
    entity.save(
        update_fields=[
            "status",
            "archived_at",
            "archived_by",
            "updated_by",
            "updated_at",
        ]
    )
    return entity
