from __future__ import annotations

from datetime import date

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from domain.catalog.services import (
    assign_subject_teaching_responsibility,
    create_area,
    create_discipline,
    create_learning_objective,
    create_root_topic,
    create_subject,
)
from domain.courses.services import create_course
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
)


class CourseFixtureMixin:
    def user(self, email: str):
        user = get_user_model().objects.create_user(
            email=email, password="Password123!x"
        )
        EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
        return user

    def curriculum(self, suffix: str = ""):
        governance_owner = self.user(f"owner{suffix}@example.test")
        organization = create_organization_with_owner(
            actor=governance_owner,
            name=f"Institución {suffix or 'principal'}",
            slug=f"institucion{suffix}",
        )
        owner = self.user(f"academic-operator{suffix}@example.test")
        add_existing_member_with_roles(
            actor=governance_owner,
            organization=organization,
            user=owner,
            roles={RoleCode.ADMINISTRATOR, RoleCode.AUTHOR},
        )
        area = create_area(
            actor=owner,
            organization=organization,
            name="Matemáticas",
            slug="matematicas",
            description="",
        )
        discipline = create_discipline(
            actor=owner,
            organization=organization,
            area=area,
            name="Matemática escolar",
            slug="matematica-escolar",
            description="",
        )
        subject = create_subject(
            actor=owner,
            organization=organization,
            discipline=discipline,
            name="Álgebra",
            slug="algebra",
            description="",
        )
        assign_subject_teaching_responsibility(
            actor=owner,
            organization=organization,
            subject=subject,
            membership=Membership.objects.get(organization=organization, user=owner),
            starts_on=date(2020, 1, 1),
            ends_on=None,
            rationale="Responsabilidad explícita del fixture académico.",
        )
        objective = create_learning_objective(
            actor=owner,
            organization=organization,
            subject=subject,
            code="ALG-01",
            statement="Modelar relaciones lineales.",
            description="",
            cognitive_level="apply",
        )
        topic = create_root_topic(
            actor=owner,
            organization=organization,
            subject=subject,
            title="Funciones lineales",
            slug="funciones-lineales",
            description="",
        )
        return owner, organization, subject, objective, topic

    def member(self, owner, organization, role: RoleCode, email: str):
        user = self.user(email)
        add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=user,
            roles={role},
        )
        return user

    def course_revision(self):
        owner, organization, subject, objective, topic = self.curriculum()
        revision = create_course(
            actor=owner,
            organization=organization,
            slug="algebra-esencial",
            title="Álgebra esencial",
            summary="Curso demo para validar la estructura de autoría.",
            primary_subject=subject,
            learning_objectives=[objective],
        )
        return owner, organization, subject, objective, topic, revision
