from __future__ import annotations

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from domain.organizations.capabilities import Capability
from domain.organizations.choices import RoleCode
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
)


class OrganizationApiTests(TestCase):
    def verified_user(self, email: str):
        user = get_user_model().objects.create_user(
            email=email, password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        return user

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_owner_adds_member_and_member_context_is_minimal(self) -> None:
        owner = self.verified_user("owner@example.test")
        learner = self.verified_user("learner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        owner_client = self.client_for(owner)
        response = owner_client.post(
            f"/api/v1/organizations/{organization.slug}/memberships/",
            {"email": learner.email, "roles": [RoleCode.LEARNER]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        context = self.client_for(learner).get("/api/v1/access/context/")
        self.assertEqual(context.status_code, 200)
        self.assertEqual(
            set(context.data), {"user", "organizations", "is_platform_operator"}
        )
        self.assertFalse(context.data["is_platform_operator"])
        item = context.data["organizations"][0]
        self.assertEqual(
            set(item),
            {
                "id",
                "name",
                "slug",
                "membership_id",
                "membership_status",
                "roles",
                "capabilities",
            },
        )
        self.assertNotIn("is_staff", str(context.data))

    def test_platform_operator_can_provision_without_cross_institution_access(
        self,
    ) -> None:
        owner = self.verified_user("owner@example.test")
        existing = create_organization_with_owner(
            actor=owner, name="Institución existente", slug="institucion-existente"
        )
        operator = self.verified_user("operator@example.test")
        operator.is_superuser = True
        operator.is_staff = True
        operator.save(update_fields=["is_superuser", "is_staff"])
        client = self.client_for(operator)

        context = client.get("/api/v1/access/context/")
        self.assertEqual(context.status_code, 200)
        self.assertTrue(context.data["is_platform_operator"])
        self.assertEqual(context.data["organizations"], [])
        self.assertEqual(
            client.get(f"/api/v1/organizations/{existing.slug}/").status_code,
            404,
        )
        self.assertEqual(
            client.get(
                f"/api/v1/organizations/{existing.slug}/memberships/"
            ).status_code,
            404,
        )

        created = client.post(
            "/api/v1/platform/organizations/",
            {"name": "Nueva Academia"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["name"], "Nueva Academia")
        self.assertRegex(created.data["slug"], r"^nueva-academia-[0-9a-f]{6}$")
        organization_slugs = [
            item["slug"] for item in client.get("/api/v1/organizations/").data
        ]
        self.assertIn(existing.slug, organization_slugs)
        self.assertIn(created.data["slug"], organization_slugs)
        created_context = client.get("/api/v1/access/context/")
        self.assertEqual(created_context.status_code, 200)
        self.assertEqual(len(created_context.data["organizations"]), 1)
        access = created_context.data["organizations"][0]
        self.assertEqual(access["slug"], created.data["slug"])
        self.assertEqual(access["roles"], [RoleCode.OWNER])
        self.assertIn(Capability.MEMBERSHIP_ADD.value, access["capabilities"])

    def test_non_platform_user_cannot_provision_an_institution(self) -> None:
        user = self.verified_user("user@example.test")
        response = self.client_for(user).post(
            "/api/v1/platform/organizations/",
            {"name": "No autorizada"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_cross_organization_slug_and_membership_are_not_found(self) -> None:
        owner = self.verified_user("owner@example.test")
        other_owner = self.verified_user("other-owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Primera", slug="primera"
        )
        other = create_organization_with_owner(
            actor=other_owner, name="Segunda", slug="segunda"
        )
        other_membership = other.memberships.get(user=other_owner)
        client = self.client_for(owner)
        self.assertEqual(
            client.get(f"/api/v1/organizations/{other.slug}/").status_code, 404
        )
        self.assertEqual(
            client.get(
                f"/api/v1/organizations/{organization.slug}/memberships/{other_membership.id}/"
            ).status_code,
            404,
        )

    def test_administrator_cannot_assign_owner_or_manage_owner(self) -> None:
        owner = self.verified_user("owner@example.test")
        administrator = self.verified_user("administrator@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        membership = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=administrator,
            roles={RoleCode.ADMINISTRATOR},
        )
        response = self.client_for(administrator).put(
            f"/api/v1/organizations/{organization.slug}/memberships/{membership.id}/roles/",
            {"roles": [RoleCode.OWNER]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "role_assignment_denied")
