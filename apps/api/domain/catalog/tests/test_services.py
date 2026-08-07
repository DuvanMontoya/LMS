from __future__ import annotations

from datetime import date

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from domain.catalog.exceptions import (
    ActiveChildrenExist,
    ActiveDependenciesExist,
    CrossOrganizationRelation,
    DuplicateAssociation,
    PrerequisiteCycle,
    PrerequisiteSelfReference,
    TopicDepthExceeded,
)
from domain.catalog.models import (
    CatalogStatus,
    ConceptPrerequisite,
    SubjectPrerequisite,
    SubjectTeachingResponsibility,
    Topic,
    TopicConcept,
)
from domain.catalog.selectors import responsible_subjects_for_actor
from domain.catalog.services import (
    archive_area,
    archive_concept,
    archive_discipline,
    archive_entity,
    archive_subject,
    archive_topic_subtree,
    assign_subject_teaching_responsibility,
    close_subject_teaching_responsibility,
    create_area,
    create_child_topic,
    create_concept,
    create_discipline,
    create_learning_objective,
    create_root_topic,
    create_subject,
    move_topic,
    replace_concept_prerequisites,
    replace_subject_prerequisites,
    replace_topic_concepts,
    restore_entity,
)
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
)


class CatalogServiceTests(TestCase):
    def test_subject_responsibility_is_scoped_dated_and_history_preserving(
        self,
    ) -> None:
        owner, organization, _area, _discipline, subject = self.curriculum()
        instructor = self.user("responsible-instructor@example.test")
        add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=instructor,
            roles={RoleCode.INSTRUCTOR},
        )
        membership = Membership.objects.get(organization=organization, user=instructor)
        responsibility = assign_subject_teaching_responsibility(
            actor=owner,
            organization=organization,
            subject=subject,
            membership=membership,
            starts_on=date.today(),
            ends_on=None,
            rationale="Responsabilidad académica anual.",
        )
        self.assertEqual(
            list(
                responsible_subjects_for_actor(
                    actor=instructor, organization=organization
                )
            ),
            [subject],
        )
        with self.assertRaisesMessage(ValidationError, "no se elimina físicamente"):
            responsibility.delete()
        close_subject_teaching_responsibility(
            actor=owner,
            responsibility=responsibility,
            ended_on=date.today(),
        )
        self.assertFalse(
            responsible_subjects_for_actor(
                actor=instructor, organization=organization
            ).exists()
        )
        self.assertEqual(SubjectTeachingResponsibility.objects.count(), 1)

    def user(self, email: str):
        user = get_user_model().objects.create_user(
            email=email, password="Password123!x"
        )
        EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
        return user

    def curriculum(self):
        governance_owner = self.user("owner@example.test")
        organization = create_organization_with_owner(
            actor=governance_owner, name="Institución", slug="institucion"
        )
        actor = self.user("catalog-administrator@example.test")
        add_existing_member_with_roles(
            actor=governance_owner,
            organization=organization,
            user=actor,
            roles={RoleCode.ADMINISTRATOR},
        )
        area = create_area(
            actor=actor,
            organization=organization,
            name="Matemáticas",
            slug="matematicas",
            description="",
        )
        discipline = create_discipline(
            actor=actor,
            organization=organization,
            area=area,
            name="Base",
            slug="base",
            description="",
        )
        subject = create_subject(
            actor=actor,
            organization=organization,
            discipline=discipline,
            name="Álgebra",
            slug="algebra",
            description="",
        )
        return actor, organization, area, discipline, subject

    def test_structure_topics_associations_and_restore(self) -> None:
        actor, organization, area, _, subject = self.curriculum()
        root = create_root_topic(
            actor=actor,
            organization=organization,
            subject=subject,
            title="Funciones",
            slug="funciones",
            description="",
        )
        child = create_child_topic(
            actor=actor,
            organization=organization,
            parent=root,
            title="Dominio",
            slug="dominio",
            description="",
        )
        self.assertEqual(child.depth, 2)
        self.assertFalse(any(Topic.objects.find_problems()))
        concept = create_concept(
            actor=actor,
            organization=organization,
            name="Función",
            slug="funcion",
            definition="Relación.",
        )
        replace_topic_concepts(
            actor=actor, organization=organization, topic=root, concepts=[concept]
        )
        self.assertEqual(TopicConcept.objects.get(topic=root).position, 0)
        second_concept = create_concept(
            actor=actor,
            organization=organization,
            name="Dominio",
            slug="dominio-concepto",
            definition="Conjunto de valores permitidos.",
        )
        replace_topic_concepts(
            actor=actor,
            organization=organization,
            topic=root,
            concepts=[concept, second_concept],
        )
        original_ids = dict(
            TopicConcept.objects.filter(topic=root).values_list("concept_id", "id")
        )
        replace_topic_concepts(
            actor=actor,
            organization=organization,
            topic=root,
            concepts=[second_concept, concept],
        )
        reordered = list(
            TopicConcept.objects.filter(topic=root)
            .order_by("position")
            .values_list("concept_id", "id")
        )
        self.assertEqual(
            reordered,
            [
                (second_concept.id, original_ids[second_concept.id]),
                (concept.id, original_ids[concept.id]),
            ],
        )
        archive_entity(actor=actor, organization=organization, entity=area)
        area.refresh_from_db()
        self.assertEqual(area.status, CatalogStatus.ARCHIVED)
        restore_entity(actor=actor, organization=organization, entity=area)
        area.refresh_from_db()
        self.assertEqual(area.status, CatalogStatus.ACTIVE)

    def test_topic_depth_and_cross_subject_moves_are_rejected(self) -> None:
        actor, organization, _, discipline, subject = self.curriculum()
        root = create_root_topic(
            actor=actor,
            organization=organization,
            subject=subject,
            title="N0",
            slug="n0",
            description="",
        )
        node = root
        for number in range(1, 8):
            node = create_child_topic(
                actor=actor,
                organization=organization,
                parent=node,
                title=f"N{number}",
                slug=f"n{number}",
                description="",
            )
        with self.assertRaises(TopicDepthExceeded):
            create_child_topic(
                actor=actor,
                organization=organization,
                parent=node,
                title="N8",
                slug="n8",
                description="",
            )
        other = create_subject(
            actor=actor,
            organization=organization,
            discipline=discipline,
            name="Geometría",
            slug="geometria",
            description="",
        )
        other_root = create_root_topic(
            actor=actor,
            organization=organization,
            subject=other,
            title="Otro",
            slug="otro",
            description="",
        )
        with self.assertRaises(CrossOrganizationRelation):
            move_topic(
                actor=actor, organization=organization, topic=root, target=other_root
            )

    def test_prerequisites_are_acyclic_and_organization_scoped(self) -> None:
        actor, organization, _, discipline, subject = self.curriculum()
        prerequisite = create_subject(
            actor=actor,
            organization=organization,
            discipline=discipline,
            name="Base 2",
            slug="base-2",
            description="",
        )
        replace_subject_prerequisites(
            actor=actor,
            organization=organization,
            target=subject,
            prerequisites=[(prerequisite, "required", "")],
        )
        self.assertEqual(SubjectPrerequisite.objects.count(), 1)
        original_link = SubjectPrerequisite.objects.get(subject=subject)
        replace_subject_prerequisites(
            actor=actor,
            organization=organization,
            target=subject,
            prerequisites=[(prerequisite, "recommended", "Refuerzo previo.")],
        )
        preserved_link = SubjectPrerequisite.objects.get(subject=subject)
        self.assertEqual(preserved_link.id, original_link.id)
        self.assertEqual(preserved_link.kind, "recommended")
        self.assertEqual(preserved_link.rationale, "Refuerzo previo.")
        with self.assertRaises(DuplicateAssociation):
            replace_subject_prerequisites(
                actor=actor,
                organization=organization,
                target=subject,
                prerequisites=[
                    (prerequisite, "required", ""),
                    (prerequisite, "recommended", ""),
                ],
            )
        with self.assertRaises(PrerequisiteCycle):
            replace_subject_prerequisites(
                actor=actor,
                organization=organization,
                target=prerequisite,
                prerequisites=[(subject, "required", "")],
            )
        with self.assertRaises(PrerequisiteSelfReference):
            replace_subject_prerequisites(
                actor=actor,
                organization=organization,
                target=subject,
                prerequisites=[(subject, "required", "")],
            )
        first = create_concept(
            actor=actor, organization=organization, name="A", slug="a", definition="a"
        )
        second = create_concept(
            actor=actor, organization=organization, name="B", slug="b", definition="b"
        )
        replace_concept_prerequisites(
            actor=actor,
            organization=organization,
            target=first,
            prerequisites=[(second, "required", "")],
        )
        self.assertEqual(ConceptPrerequisite.objects.count(), 1)
        with self.assertRaises(PrerequisiteCycle):
            replace_concept_prerequisites(
                actor=actor,
                organization=organization,
                target=second,
                prerequisites=[(first, "required", "")],
            )

    def test_objective_creation_uses_subject_organization(self) -> None:
        actor, organization, _, _, subject = self.curriculum()
        objective = create_learning_objective(
            actor=actor,
            organization=organization,
            subject=subject,
            code="OBJ-001",
            statement="Resolver un problema.",
            description="",
            cognitive_level="apply",
        )
        self.assertEqual(objective.organization, organization)

    def test_archiving_protects_active_structure_and_dependencies(self) -> None:
        actor, organization, area, discipline, subject = self.curriculum()
        with self.assertRaises(ActiveChildrenExist):
            archive_area(actor=actor, organization=organization, area=area)
        with self.assertRaises(ActiveChildrenExist):
            archive_discipline(
                actor=actor, organization=organization, discipline=discipline
            )
        topic = create_root_topic(
            actor=actor,
            organization=organization,
            subject=subject,
            title="Tema",
            slug="tema",
            description="",
        )
        child = create_child_topic(
            actor=actor,
            organization=organization,
            parent=topic,
            title="Hijo",
            slug="hijo",
            description="",
        )
        with self.assertRaises(ActiveDependenciesExist):
            archive_subject(actor=actor, organization=organization, subject=subject)
        archive_topic_subtree(actor=actor, organization=organization, topic=topic)
        child.refresh_from_db()
        self.assertEqual(child.status, CatalogStatus.ARCHIVED)
        concept = create_concept(
            actor=actor,
            organization=organization,
            name="Concepto",
            slug="concepto",
            definition="Definición.",
        )
        active_topic = create_root_topic(
            actor=actor,
            organization=organization,
            subject=subject,
            title="Tema activo",
            slug="tema-activo",
            description="",
        )
        replace_topic_concepts(
            actor=actor,
            organization=organization,
            topic=active_topic,
            concepts=[concept],
        )
        with self.assertRaises(ActiveDependenciesExist):
            archive_concept(actor=actor, organization=organization, concept=concept)
