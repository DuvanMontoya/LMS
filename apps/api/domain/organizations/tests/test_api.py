from __future__ import annotations

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

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
        self.assertEqual(set(context.data), {"user", "organizations"})
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
