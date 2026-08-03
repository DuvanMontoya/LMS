# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from domain.courses.choices import (
    ActivityCompletionMethod,
    ActivityType,
    AuthoringStatus,
)
from domain.courses.exceptions import (
    CourseAccessDenied,
    CourseDomainError,
    CourseRevisionConflict,
)
from domain.courses.models import CourseActivity, CourseModule, CourseRevision
from domain.courses.policies import (
    can_manage_course,
    has_course_academic_responsibility,
)
from domain.courses.services import (
    create_activity,
    replace_activity_learning_objectives,
)
from domain.organizations.models import Organization

from .exceptions import AssessmentConflict, AssessmentForbidden, AssessmentInvalid
from .models import AssessmentActivityBinding, AssessmentVersion
from .policies import can_manage_authoring


@transaction.atomic
def create_and_bind_assessment_activity(
    *,
    actor: Any,
    organization: Organization,
    module: CourseModule,
    assessment_version: AssessmentVersion,
    expected_revision_version: int,
    required: bool,
) -> tuple[AssessmentActivityBinding, CourseActivity, int]:
    objectives = [
        link.objective
        for link in assessment_version.source_revision.objective_links.select_related(
            "objective"
        ).order_by("position", "id")
    ]
    aligned_ids = set(
        module.revision.objective_alignments.values_list(
            "learning_objective_id", flat=True
        )
    )
    objective_ids = {objective.id for objective in objectives}
    if not objectives:
        raise AssessmentInvalid(
            "La evaluación aprobada no tiene objetivos curriculares verificables."
        )
    if not objective_ids <= aligned_ids:
        raise AssessmentInvalid(
            "Esta evaluación no es compatible con los objetivos del curso. "
            "Elige una evaluación alineada o amplía primero la alineación del curso."
        )
    try:
        activity, revision = create_activity(
            actor=actor,
            organization=organization,
            module=module,
            expected_version=expected_revision_version,
            activity_type=ActivityType.ASSESSMENT,
            title=assessment_version.title,
            summary=assessment_version.description,
            estimated_duration_minutes=assessment_version.time_limit_minutes,
            required=required,
            completion_method=ActivityCompletionMethod.PASS,
            minimum_attendance_basis_points=None,
            minimum_grade_basis_points=assessment_version.pass_basis_points,
        )
    except CourseRevisionConflict as error:
        raise AssessmentConflict(str(error)) from error
    except CourseAccessDenied as error:
        raise AssessmentForbidden(str(error)) from error
    except CourseDomainError as error:
        raise AssessmentInvalid(str(error)) from error
    try:
        aligned_revision = replace_activity_learning_objectives(
            actor=actor,
            organization=organization,
            activity=activity,
            expected_version=revision.lock_version,
            learning_objectives=objectives,
        )
    except CourseDomainError as error:
        raise AssessmentInvalid(str(error)) from error
    binding, lock_version = bind_assessment_activity(
        actor=actor,
        organization=organization,
        activity=activity,
        assessment_version=assessment_version,
        expected_revision_version=aligned_revision.lock_version,
    )
    return binding, activity, lock_version


@transaction.atomic
def bind_assessment_activity(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    assessment_version: AssessmentVersion,
    expected_revision_version: int,
) -> tuple[AssessmentActivityBinding, int]:
    locked_revision = CourseRevision.objects.select_for_update().get(
        pk=activity.module.revision_id
    )
    if (
        not can_manage_course(actor, organization)
        or not can_manage_authoring(actor, organization)
        or not has_course_academic_responsibility(
            actor, organization, course=locked_revision.course
        )
    ):
        raise AssessmentForbidden("No puedes vincular esta actividad.")
    if locked_revision.lock_version != expected_revision_version:
        raise AssessmentConflict("La revisión cambió; actualiza antes de vincular.")
    if locked_revision.authoring_status not in {
        AuthoringStatus.DRAFT,
        AuthoringStatus.CHANGES_REQUESTED,
    }:
        raise AssessmentInvalid("La revisión del curso no es editable.")
    if (
        activity.activity_type != ActivityType.ASSESSMENT
        or activity.module.revision_id != locked_revision.id
        or locked_revision.course.organization_id != organization.id
        or assessment_version.assessment.organization_id != organization.id
    ):
        raise AssessmentInvalid("La vinculación curricular no es válida.")
    if AssessmentActivityBinding.objects.filter(activity=activity).exists():
        raise AssessmentConflict(
            "La actividad ya tiene una versión de evaluación vinculada."
        )
    binding = AssessmentActivityBinding(
        activity=activity,
        assessment_version=assessment_version,
        created_by=actor,
    )
    try:
        binding.full_clean()
    except ValidationError as error:
        raise AssessmentInvalid("La vinculación curricular no es válida.") from error
    binding.save()
    locked_revision.lock_version += 1
    locked_revision.updated_by = actor
    locked_revision.save(update_fields=["lock_version", "updated_by", "updated_at"])
    return binding, locked_revision.lock_version


def readiness_issues(revision: CourseRevision) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    cached_objective_ids = getattr(revision, "_readiness_course_objective_ids", None)
    course_objective_ids = (
        set(cached_objective_ids)
        if cached_objective_ids is not None
        else set(
            revision.objective_alignments.values_list(
                "learning_objective_id", flat=True
            )
        )
    )
    cached_activities = getattr(revision, "_readiness_active_activities", None)
    activities = (
        [
            activity
            for activity in cached_activities
            if activity.activity_type == ActivityType.ASSESSMENT
        ]
        if cached_activities is not None
        else list(
            CourseActivity.objects.filter(
                module__revision=revision,
                activity_type=ActivityType.ASSESSMENT,
                status="active",
            )
        )
    )
    if not activities:
        return issues
    bindings = {
        binding.activity_id: binding
        for binding in AssessmentActivityBinding.objects.filter(activity__in=activities)
        .select_related("assessment_version__source_revision")
        .prefetch_related("assessment_version__source_revision__objective_links")
    }
    for activity in activities:
        binding = bindings.get(activity.id)
        path = f"activities.{activity.id}"
        if binding is None:
            issues.append(
                {
                    "code": "assessment_binding_required",
                    "path": path,
                    "message": "La evaluación no tiene una versión aprobada vinculada.",
                }
            )
            continue
        objective_ids = {
            link.objective_id
            for link in binding.assessment_version.source_revision.objective_links.all()
        }
        if not objective_ids <= course_objective_ids:
            issues.append(
                {
                    "code": "assessment_objective_outside_course",
                    "path": f"{path}.learning_objectives",
                    "message": "La evaluación usa objetivos ajenos al curso.",
                }
            )
    return issues


def snapshot_binding(activity: CourseActivity) -> dict[str, Any]:
    binding = AssessmentActivityBinding.objects.select_related(
        "assessment_version__assessment"
    ).get(activity=activity)
    version = binding.assessment_version
    return {
        "provider": "assessments",
        "assessment_version_id": str(version.id),
        "assessment_id": str(version.assessment_id),
        "number": version.number,
        "title": version.title,
        "snapshot_digest": version.snapshot_digest,
        "pass_basis_points": version.pass_basis_points,
        "maximum_score": str(version.maximum_score),
    }


def clone_binding(source: CourseActivity, target: CourseActivity, actor: Any) -> None:
    binding = AssessmentActivityBinding.objects.get(activity=source)
    AssessmentActivityBinding.objects.create(
        activity=target,
        assessment_version=binding.assessment_version,
        created_by=actor,
    )
