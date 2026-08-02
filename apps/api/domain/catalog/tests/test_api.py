from __future__ import annotations

from datetime import date

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from domain.catalog.models import CatalogStatus
from domain.catalog.services import (
    create_area,
    create_concept,
    create_discipline,
    create_subject,
)
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
)


class CatalogApiTests(TestCase):
    def user(self, email: str):
        user = get_user_model().objects.create_user(
            email=email, password="Password123!x"
        )
        EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
        return user

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def operational_organization(self, *, email: str, name: str, slug: str):
        governance_owner = self.user(f"governance-{email}")
        organization = create_organization_with_owner(
            actor=governance_owner, name=name, slug=slug
        )
        administrator = self.user(email)
        add_existing_member_with_roles(
            actor=governance_owner,
            organization=organization,
            user=administrator,
            roles={RoleCode.ADMINISTRATOR},
        )
        return administrator, organization

    def test_teaching_responsibilities_are_administered_and_self_scoped(self) -> None:
        owner, organization = self.operational_organization(
            email="owner-responsibilities@example.test",
            name="Institución",
            slug="responsabilidades",
        )
        instructor = self.user("instructor-responsibilities@example.test")
        other_instructor = self.user("other-instructor@example.test")
        for user in (instructor, other_instructor):
            add_existing_member_with_roles(
                actor=owner,
                organization=organization,
                user=user,
                roles={RoleCode.AUTHOR},
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
            name="General",
            slug="general",
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
        membership = Membership.objects.get(organization=organization, user=instructor)
        prefix = (
            f"/api/v1/organizations/{organization.slug}/catalog/"
            "teaching-responsibilities/"
        )
        created = self.client_for(owner).post(
            prefix,
            {
                "subject_id": str(subject.id),
                "membership_id": str(membership.id),
                "starts_on": date.today().isoformat(),
                "rationale": "Asignación del periodo académico.",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["member_email"], instructor.email)
        self.assertEqual(len(self.client_for(owner).get(prefix).data), 1)
        self.assertEqual(len(self.client_for(instructor).get(prefix).data), 1)
        self.assertEqual(len(self.client_for(other_instructor).get(prefix).data), 0)
        subject_scope = (
            f"/api/v1/organizations/{organization.slug}/catalog/subjects/"
            "?status=active&teaching_responsibility=mine"
        )
        self.assertEqual(
            [row["id"] for row in self.client_for(instructor).get(subject_scope).data],
            [str(subject.id)],
        )
        self.assertEqual(
            self.client_for(other_instructor).get(subject_scope).data,
            [],
        )

        forbidden = self.client_for(instructor).post(
            prefix,
            {
                "subject_id": str(subject.id),
                "membership_id": str(membership.id),
                "starts_on": date.today().isoformat(),
                "rationale": "Autoconcesión no permitida.",
            },
            format="json",
        )
        self.assertEqual(forbidden.status_code, 403)
        close_url = f"{prefix}{created.data['id']}/close/"
        self.assertEqual(
            self.client_for(instructor)
            .post(close_url, {"ended_on": date.today().isoformat()}, format="json")
            .status_code,
            403,
        )
        closed = self.client_for(owner).post(
            close_url, {"ended_on": date.today().isoformat()}, format="json"
        )
        self.assertEqual(closed.status_code, 200)
        self.assertIsNotNone(closed.data["ended_at"])
        self.assertEqual(self.client_for(instructor).get(subject_scope).data, [])

    def test_owner_creates_and_lists_curriculum_structure(self) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        client = self.client_for(owner)
        prefix = f"/api/v1/organizations/{organization.slug}/catalog"
        area = client.post(
            f"{prefix}/areas/",
            {"name": "Matemáticas", "slug": "matematicas", "description": ""},
            format="json",
        )
        self.assertEqual(area.status_code, 201)
        disciplines = client.post(
            f"{prefix}/disciplines/",
            {"area_id": area.data["id"], "name": "Base", "slug": "base"},
            format="json",
        )
        self.assertEqual(disciplines.status_code, 201)
        subject = client.post(
            f"{prefix}/subjects/",
            {
                "discipline_id": disciplines.data["id"],
                "name": "Álgebra",
                "slug": "algebra",
            },
            format="json",
        )
        self.assertEqual(subject.status_code, 201)
        topic = client.post(
            f"{prefix}/subjects/{subject.data['id']}/topics/",
            {"title": "Funciones", "slug": "funciones"},
            format="json",
        )
        self.assertEqual(topic.status_code, 201)
        tree = client.get(f"{prefix}/subjects/{subject.data['id']}/topics/")
        self.assertEqual(tree.status_code, 200)
        self.assertEqual(tree.data[0]["title"], "Funciones")
        self.assertEqual(client.get(f"{prefix}/areas/").data[0]["slug"], "matematicas")

    def test_reader_only_sees_active_catalog_and_other_organization_is_not_found(
        self,
    ) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        other, external = self.operational_organization(
            email="other@example.test", name="Externa", slug="externa"
        )
        active = create_area(
            actor=owner,
            organization=organization,
            name="Activa",
            slug="activa",
            description="",
        )
        archived = create_area(
            actor=owner,
            organization=organization,
            name="Archivada",
            slug="archivada",
            description="",
        )
        archived.status = CatalogStatus.ARCHIVED
        archived.save(update_fields=["status"])
        response = self.client_for(other).get(
            f"/api/v1/organizations/{organization.slug}/catalog/areas/"
        )
        self.assertEqual(response.status_code, 404)
        own = self.client_for(owner).get(
            f"/api/v1/organizations/{organization.slug}/catalog/areas/"
        )
        self.assertEqual(
            {item["id"] for item in own.data}, {str(active.id), str(archived.id)}
        )
        self.assertEqual(
            self.client_for(owner)
            .get(f"/api/v1/organizations/{external.slug}/catalog/areas/")
            .status_code,
            404,
        )

    def test_concepts_are_scoped_to_the_organization(self) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        create_concept(
            actor=owner,
            organization=organization,
            name="Función",
            slug="funcion",
            definition="Relación entre variables.",
        )
        response = self.client_for(owner).get(
            f"/api/v1/organizations/{organization.slug}/catalog/concepts/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], "Función")

    def test_catalog_filters_and_create_endpoints(self) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        client = self.client_for(owner)
        prefix = f"/api/v1/organizations/{organization.slug}/catalog"
        created = client.post(
            f"{prefix}/concepts/",
            {
                "name": "Función lineal",
                "slug": "funcion-lineal",
                "definition": "Una relación de primer grado.",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(
            client.get(f"{prefix}/concepts/?search=lineal").data[0]["id"],
            created.data["id"],
        )
        second = client.post(
            f"{prefix}/concepts/",
            {
                "name": "Álgebra abstracta",
                "slug": "algebra-abstracta",
                "definition": "Estructuras algebraicas.",
            },
            format="json",
        )
        self.assertEqual(second.status_code, 201)
        ordered = client.get(f"{prefix}/concepts/?ordering=-name")
        self.assertEqual(ordered.status_code, 200)
        self.assertEqual(ordered.data[0]["id"], created.data["id"])

    def test_owner_updates_and_archives_simple_catalog_entities(self) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        client = self.client_for(owner)
        prefix = f"/api/v1/organizations/{organization.slug}/catalog"
        area = client.post(
            f"{prefix}/areas/", {"name": "Base", "slug": "base"}, format="json"
        )
        updated = client.patch(
            f"{prefix}/areas/{area.data['id']}/",
            {"name": "Fundamentos"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["name"], "Fundamentos")
        archived = client.post(f"{prefix}/areas/{area.data['id']}/archive/")
        self.assertEqual(archived.status_code, 200)
        self.assertEqual(archived.data["status"], CatalogStatus.ARCHIVED)
        restored = client.post(f"{prefix}/areas/{area.data['id']}/restore/")
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.data["status"], CatalogStatus.ACTIVE)

    def test_archive_dependency_rejection_returns_the_safe_catalog_error(self) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        concept = create_concept(
            actor=owner,
            organization=organization,
            name="Asociado",
            slug="asociado",
            definition="No puede archivarse con dependencias activas.",
        )
        area = create_area(
            actor=owner,
            organization=organization,
            name="Área",
            slug="area",
            description="",
        )
        client = self.client_for(owner)
        prefix = f"/api/v1/organizations/{organization.slug}/catalog"
        discipline = client.post(
            f"{prefix}/disciplines/",
            {"area_id": str(area.id), "name": "Base", "slug": "base"},
            format="json",
        )
        subject = client.post(
            f"{prefix}/subjects/",
            {
                "discipline_id": discipline.data["id"],
                "name": "Asignatura",
                "slug": "asignatura",
            },
            format="json",
        )
        topic = client.post(
            f"{prefix}/subjects/{subject.data['id']}/topics/",
            {"title": "Tema", "slug": "tema"},
            format="json",
        )
        client.put(
            f"{prefix}/topics/{topic.data['id']}/concepts/",
            {"concept_ids": [str(concept.id)]},
            format="json",
        )
        rejected = client.post(f"{prefix}/concepts/{concept.id}/archive/")
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.data["code"], "catalog_operation_rejected")
        self.assertEqual(
            rejected.data["detail"], "La operación curricular no es válida."
        )

    def test_subject_prerequisites_are_replaced_and_cycles_return_conflict(
        self,
    ) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        client = self.client_for(owner)
        prefix = f"/api/v1/organizations/{organization.slug}/catalog"
        area = client.post(
            f"{prefix}/areas/", {"name": "Base", "slug": "base"}, format="json"
        )
        discipline = client.post(
            f"{prefix}/disciplines/",
            {"area_id": area.data["id"], "name": "General", "slug": "general"},
            format="json",
        )
        first = client.post(
            f"{prefix}/subjects/",
            {
                "discipline_id": discipline.data["id"],
                "name": "Álgebra",
                "slug": "algebra",
            },
            format="json",
        )
        second = client.post(
            f"{prefix}/subjects/",
            {
                "discipline_id": discipline.data["id"],
                "name": "Cálculo",
                "slug": "calculo",
            },
            format="json",
        )
        payload = {
            "prerequisites": [{"prerequisite_id": first.data["id"], "kind": "required"}]
        }
        result = client.put(
            f"{prefix}/subjects/{second.data['id']}/prerequisites/",
            payload,
            format="json",
        )
        self.assertEqual(result.status_code, 200)
        aggregate = client.get(f"{prefix}/subject-prerequisites/")
        self.assertEqual(aggregate.status_code, 200)
        self.assertEqual(
            aggregate.data,
            [
                {
                    "entity_id": second.data["id"],
                    "prerequisite_id": first.data["id"],
                    "kind": "required",
                    "rationale": "",
                }
            ],
        )
        cycle = client.put(
            f"{prefix}/subjects/{first.data['id']}/prerequisites/",
            {
                "prerequisites": [
                    {"prerequisite_id": second.data["id"], "kind": "required"}
                ]
            },
            format="json",
        )
        self.assertEqual(cycle.status_code, 409)
        self.assertEqual(cycle.data["code"], "prerequisite_cycle")

    def test_topic_concept_association_keeps_the_request_order(self) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        client = self.client_for(owner)
        prefix = f"/api/v1/organizations/{organization.slug}/catalog"
        area = client.post(
            f"{prefix}/areas/", {"name": "Área", "slug": "area"}, format="json"
        )
        discipline = client.post(
            f"{prefix}/disciplines/",
            {"area_id": area.data["id"], "name": "Disciplina", "slug": "disciplina"},
            format="json",
        )
        subject = client.post(
            f"{prefix}/subjects/",
            {
                "discipline_id": discipline.data["id"],
                "name": "Asignatura",
                "slug": "asignatura",
            },
            format="json",
        )
        topic = client.post(
            f"{prefix}/subjects/{subject.data['id']}/topics/",
            {"title": "Tema", "slug": "tema"},
            format="json",
        )
        first = client.post(
            f"{prefix}/concepts/",
            {"name": "Uno", "slug": "uno", "definition": "Uno"},
            format="json",
        )
        second = client.post(
            f"{prefix}/concepts/",
            {"name": "Dos", "slug": "dos", "definition": "Dos"},
            format="json",
        )
        result = client.put(
            f"{prefix}/topics/{topic.data['id']}/concepts/",
            {"concept_ids": [second.data["id"], first.data["id"]]},
            format="json",
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(
            result.data["concept_ids"], [second.data["id"], first.data["id"]]
        )
        aggregate = client.get(f"{prefix}/topic-concepts/")
        self.assertEqual(aggregate.status_code, 200)
        self.assertEqual(
            aggregate.data,
            [
                {
                    "entity_id": topic.data["id"],
                    "concept_ids": [second.data["id"], first.data["id"]],
                }
            ],
        )

    def test_concept_prerequisite_rejects_a_cycle(self) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        client = self.client_for(owner)
        prefix = f"/api/v1/organizations/{organization.slug}/catalog"
        first = client.post(
            f"{prefix}/concepts/",
            {"name": "Vectores", "slug": "vectores", "definition": "Dirección."},
            format="json",
        )
        second = client.post(
            f"{prefix}/concepts/",
            {"name": "Matrices", "slug": "matrices", "definition": "Arreglo."},
            format="json",
        )
        result = client.put(
            f"{prefix}/concepts/{second.data['id']}/prerequisites/",
            {
                "prerequisites": [
                    {"prerequisite_id": first.data["id"], "kind": "required"}
                ]
            },
            format="json",
        )
        self.assertEqual(result.status_code, 200)
        aggregate = client.get(f"{prefix}/concept-prerequisites/")
        self.assertEqual(aggregate.status_code, 200)
        self.assertEqual(aggregate.data[0]["entity_id"], second.data["id"])
        self.assertEqual(aggregate.data[0]["prerequisite_id"], first.data["id"])
        cycle = client.put(
            f"{prefix}/concepts/{first.data['id']}/prerequisites/",
            {
                "prerequisites": [
                    {"prerequisite_id": second.data["id"], "kind": "required"}
                ]
            },
            format="json",
        )
        self.assertEqual(cycle.status_code, 409)
        self.assertEqual(cycle.data["code"], "prerequisite_cycle")

    def test_objective_concept_associations_are_available_in_one_query(self) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        client = self.client_for(owner)
        prefix = f"/api/v1/organizations/{organization.slug}/catalog"
        area = client.post(
            f"{prefix}/areas/", {"name": "Área", "slug": "area"}, format="json"
        )
        discipline = client.post(
            f"{prefix}/disciplines/",
            {"area_id": area.data["id"], "name": "Base", "slug": "base"},
            format="json",
        )
        subject = client.post(
            f"{prefix}/subjects/",
            {
                "discipline_id": discipline.data["id"],
                "name": "Asignatura",
                "slug": "asignatura",
            },
            format="json",
        )
        objective = client.post(
            f"{prefix}/learning-objectives/",
            {
                "subject_id": subject.data["id"],
                "code": "OBJ-001",
                "statement": "Explicar el concepto.",
            },
            format="json",
        )
        concept = client.post(
            f"{prefix}/concepts/",
            {"name": "Concepto", "slug": "concepto", "definition": "Definición."},
            format="json",
        )
        replaced = client.put(
            f"{prefix}/learning-objectives/{objective.data['id']}/concepts/",
            {"concept_ids": [concept.data["id"]]},
            format="json",
        )
        self.assertEqual(replaced.status_code, 200)
        aggregate = client.get(f"{prefix}/objective-concepts/")
        self.assertEqual(aggregate.status_code, 200)
        self.assertEqual(
            aggregate.data,
            [
                {
                    "entity_id": objective.data["id"],
                    "concept_ids": [concept.data["id"]],
                }
            ],
        )

    def test_detail_actions_update_move_and_archive_objective(self) -> None:
        owner, organization = self.operational_organization(
            email="owner@example.test", name="Institución", slug="institucion"
        )
        client = self.client_for(owner)
        prefix = f"/api/v1/organizations/{organization.slug}/catalog"
        area = client.post(
            f"{prefix}/areas/", {"name": "Área", "slug": "area"}, format="json"
        )
        discipline = client.post(
            f"{prefix}/disciplines/",
            {"area_id": area.data["id"], "name": "Base", "slug": "base"},
            format="json",
        )
        subject = client.post(
            f"{prefix}/subjects/",
            {
                "discipline_id": discipline.data["id"],
                "name": "Álgebra",
                "slug": "algebra",
            },
            format="json",
        )
        self.assertEqual(
            client.patch(
                f"{prefix}/subjects/{subject.data['id']}/",
                {"name": "Álgebra lineal"},
                format="json",
            ).data["name"],
            "Álgebra lineal",
        )
        root = client.post(
            f"{prefix}/subjects/{subject.data['id']}/topics/",
            {"title": "Raíz", "slug": "raiz"},
            format="json",
        )
        child = client.post(
            f"{prefix}/subjects/{subject.data['id']}/topics/",
            {"title": "Hijo", "slug": "hijo", "parent_id": root.data["id"]},
            format="json",
        )
        moved = client.post(
            f"{prefix}/topics/{child.data['id']}/move/",
            {"target_id": root.data["id"], "position": "left"},
            format="json",
        )
        self.assertEqual(moved.status_code, 200)
        objective = client.post(
            f"{prefix}/learning-objectives/",
            {
                "subject_id": subject.data["id"],
                "code": "OBJ-001",
                "statement": "Demostrar.",
            },
            format="json",
        )
        archived = client.post(
            f"{prefix}/learning-objectives/{objective.data['id']}/archive/",
            format="json",
        )
        self.assertEqual(archived.data["status"], CatalogStatus.ARCHIVED)
        restored = client.post(
            f"{prefix}/learning-objectives/{objective.data['id']}/restore/",
            format="json",
        )
        self.assertEqual(restored.data["status"], CatalogStatus.ACTIVE)
