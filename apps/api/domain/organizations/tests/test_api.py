from __future__ import annotations

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from domain.organizations.choices import (
    InvitationStatus,
    InvitationType,
    OrganizationStatus,
    RoleCode,
)
from domain.organizations.models import MembershipInvitation, Organization
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
        designated_owner = self.verified_user("designated-owner@example.test")
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
            {
                "name": "Nueva Academia",
                "owner_email": designated_owner.email,
                "administrator_emails": ["initial-admin@example.test"],
            },
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
        self.assertEqual(created_context.data["organizations"], [])
        self.assertEqual(
            client.get(f"/api/v1/organizations/{created.data['slug']}/").status_code,
            404,
        )
        owner_context = self.client_for(designated_owner).get("/api/v1/access/context/")
        self.assertEqual(owner_context.status_code, 200)
        self.assertEqual(owner_context.data["organizations"], [])
        pending = Organization.objects.get(slug=created.data["slug"])
        self.assertEqual(pending.status, OrganizationStatus.PENDING_ACTIVATION)
        invitation = pending.membership_invitations.get(email=designated_owner.email)
        self.assertEqual(invitation.status, InvitationStatus.PENDING)
        self.assertEqual(invitation.invitation_type, InvitationType.INITIAL_OWNER)
        self.assertEqual(invitation.invited_roles, [RoleCode.OWNER])
        control_plane = f"/api/v1/platform/organizations/{pending.slug}/invitations/"
        invitations = client.get(control_plane)
        self.assertEqual(invitations.status_code, 200)
        self.assertEqual(len(invitations.data), 2)
        administrator_invitation = pending.membership_invitations.get(
            email="initial-admin@example.test"
        )
        resent = client.post(f"{control_plane}{administrator_invitation.id}/resend/")
        self.assertEqual(resent.status_code, 200)
        revoked = client.post(f"{control_plane}{administrator_invitation.id}/revoke/")
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(revoked.data["status"], InvitationStatus.REVOKED)

    def test_platform_operator_cannot_invite_itself_and_can_invite_new_owner(
        self,
    ) -> None:
        operator = self.verified_user("operator@example.test")
        operator.is_superuser = True
        operator.is_staff = True
        operator.save(update_fields=["is_superuser", "is_staff"])
        client = self.client_for(operator)

        rejected = client.post(
            "/api/v1/platform/organizations/",
            {"name": "Nueva Academia", "owner_email": operator.email},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.data["code"], "initial_owner_unavailable")

        created = client.post(
            "/api/v1/platform/organizations/",
            {"name": "Nueva Academia", "owner_email": "missing@example.test"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["status"], OrganizationStatus.PENDING_ACTIVATION)
        invitation = MembershipInvitation.objects.get(
            organization__slug=created.data["slug"], email="missing@example.test"
        )
        self.assertEqual(invitation.invitation_type, InvitationType.INITIAL_OWNER)
        self.assertIsNone(invitation.existing_user_id)

    def test_non_platform_user_cannot_provision_an_institution(self) -> None:
        user = self.verified_user("user@example.test")
        owner = self.verified_user("owner@example.test")
        response = self.client_for(user).post(
            "/api/v1/platform/organizations/",
            {"name": "No autorizada", "owner_email": owner.email},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "permission_denied")
        self.assertEqual(
            self.client_for(user)
            .get("/api/v1/platform/organizations/unknown/invitations/")
            .status_code,
            403,
        )

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

    def test_member_can_manage_only_its_own_personal_profile(self) -> None:
        owner = self.verified_user("owner@example.test")
        learner = self.verified_user("learner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        membership = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=learner,
            roles={RoleCode.LEARNER},
        )
        client = self.client_for(learner)
        base = f"/api/v1/organizations/{organization.slug}/memberships/{membership.id}"

        self.assertEqual(client.get(f"{base}/").status_code, 200)
        profile = client.get(f"{base}/profile/")
        self.assertEqual(profile.status_code, 200)
        self.assertNotIn("administrative_notes", profile.data)

        updated = client.patch(
            f"{base}/profile/",
            {"preferred_name": "Estudiante"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["preferred_name"], "Estudiante")

        blocked = client.patch(
            f"{base}/profile/",
            {"member_type": "instructor"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.data["code"], "permission_denied")

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
