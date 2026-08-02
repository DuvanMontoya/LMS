# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from domain.courses.models import Course
from domain.learning.choices import AcademicPeriodType, CohortStatus, EnrollmentStatus
from domain.learning.models import AcademicPeriod, CourseEnrollment, LearningCohort
from domain.learning.services import (
    archive_cohort,
    create_academic_period,
    create_cohort,
    enroll_member,
    revoke_enrollment,
)
from domain.organizations.choices import MembershipStatus
from domain.organizations.models import Membership, Organization
from domain.publishing.choices import PublicationStatus
from domain.publishing.models import CoursePublication

DEMO_ORGANIZATION = "organizacion-demo"
DEMO_COURSE = "introduccion-calculo-diferencial"
DEMO_COHORT = "cohorte-inicial-calculo"


class Command(BaseCommand):
    help = "Crea la cohorte y matrícula demo de learning sólo en desarrollo."

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("Learning demo sólo se permite con DEBUG=True.")
        organization = Organization.objects.filter(slug=DEMO_ORGANIZATION).first()
        course = (
            Course.objects.filter(organization=organization, slug=DEMO_COURSE).first()
            if organization
            else None
        )
        owner = get_user_model().objects.filter(email="owner@demo.local").first()
        learner = get_user_model().objects.filter(email="learner@demo.local").first()
        if not organization or not course or not owner or not learner:
            raise CommandError(
                "Ejecuta primero los demos de organización, curso y publicación."
            )
        publication = (
            CoursePublication.objects.select_related("current_release")
            .filter(course=course, status=PublicationStatus.ACTIVE)
            .first()
        )
        membership = Membership.objects.filter(
            organization=organization,
            user=learner,
            status=MembershipStatus.ACTIVE,
        ).first()
        if publication is None or membership is None:
            raise CommandError("Falta la publicación o membresía Learner demo activa.")
        academic_period = AcademicPeriod.objects.filter(
            organization=organization, slug="ano-2026"
        ).first()
        if academic_period is None:
            academic_period = create_academic_period(
                actor=owner,
                organization=organization,
                name="Año académico 2026",
                slug="ano-2026",
                period_type=AcademicPeriodType.SCHOOL_YEAR,
                starts_on=date(2026, 1, 1),
                ends_on=date(2026, 12, 31),
            )
        release = publication.current_release
        cohort = LearningCohort.objects.filter(
            organization=organization,
            course=course,
            release=release,
            status=CohortStatus.ACTIVE,
        ).first()
        if cohort is None:
            previous = LearningCohort.objects.filter(
                organization=organization,
                course=course,
                slug=DEMO_COHORT,
                status=CohortStatus.ACTIVE,
            ).first()
            if previous is not None:
                archive_cohort(
                    actor=owner,
                    cohort=previous,
                    expected_cohort_version=previous.lock_version,
                )
            cohort_slug = (
                DEMO_COHORT
                if not LearningCohort.objects.filter(
                    organization=organization,
                    course=course,
                    slug=DEMO_COHORT,
                ).exists()
                else f"{DEMO_COHORT}-v{release.number}"
            )
            cohort = create_cohort(
                actor=owner,
                organization=organization,
                course=course,
                release=release,
                academic_period=academic_period,
                name="Cohorte inicial de cálculo",
                slug=cohort_slug,
            )
        enrollment = (
            CourseEnrollment.objects.select_related("current_release_assignment")
            .filter(
                membership=membership,
                course=course,
            )
            .exclude(status=EnrollmentStatus.REVOKED)
            .first()
        )
        if enrollment is not None and (
            enrollment.current_release_assignment_id is None
            or enrollment.current_release_assignment.release_id != release.id
            or enrollment.cohort_id != cohort.id
        ):
            revoke_enrollment(
                actor=owner,
                enrollment=enrollment,
                expected_version=enrollment.lock_version,
            )
            enrollment = None
        if enrollment is None:
            enrollment = enroll_member(
                actor=owner,
                organization=organization,
                course=course,
                membership=membership,
                cohort=cohort,
            )
            state = "creada"
        else:
            state = "conservada"
        self.stdout.write(
            self.style.SUCCESS(
                f"Matrícula demo {state}: {enrollment.id}; "
                f"release {enrollment.current_release_assignment.release.number}."
            )
        )
