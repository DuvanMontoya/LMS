from __future__ import annotations

from datetime import timedelta

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.utils import timezone

from domain.organizations.choices import (
    InvitationStatus,
    InvitationType,
    MembershipEventType,
    RoleCode,
)
from domain.organizations.exceptions import RevisionConflict
from domain.organizations.models import (
    Membership,
    MembershipEvent,
    MembershipInvitation,
)
from domain.organizations.services import (
    accept_session_invitation,
    add_existing_member_with_roles,
    begin_invitation_activation,
    create_invitation,
    create_organization_with_owner,
    update_membership_settings,
)


class OnboardingServiceTests(TestCase):
    def verified_user(self, email: str):
        user = get_user_model().objects.create_user(
            email=email, password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        return user

    def request(self):
        request = RequestFactory().post("/")
        SessionMiddleware(lambda _: None).process_request(request)
        request.session.save()
        return request

    def test_new_user_invitation_has_no_membership_until_verified_acceptance(
        self,
    ) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        invitation, token = create_invitation(
            actor=owner,
            organization=organization,
            email="new@example.test",
            roles={RoleCode.LEARNER},
            invitation_type=InvitationType.NEW_USER,
        )
        self.assertEqual(
            Membership.objects.filter(organization=organization).count(), 1
        )
        self.assertEqual(len(invitation.token_digest), 64)
        self.assertNotEqual(invitation.token_digest, token)

        request = self.request()
        begin_invitation_activation(request=request, token=token)
        invited = self.verified_user("new@example.test")
        membership = accept_session_invitation(request=request, user=invited)

        self.assertIsNotNone(membership)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, InvitationStatus.ACCEPTED)
        request.session["organization_invitation_id"] = str(invitation.id)
        request.session["organization_invitation_digest"] = invitation.token_digest
        retried = accept_session_invitation(request=request, user=invited)
        self.assertIsNotNone(retried)
        self.assertEqual(retried.pk, membership.pk)

    def test_organization_settings_are_versioned_and_validate_domains(self) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        current = organization.membership_settings
        updated = update_membership_settings(
            actor=owner,
            organization=organization,
            expected_version=current.lock_version,
            public_join_enabled=True,
            join_requires_approval=True,
            allowed_email_domains=["Example.TEST"],
            default_role=RoleCode.LEARNER,
            invitation_expiry_hours=72,
            allow_admin_managed_accounts=True,
            allow_bulk_invitations=False,
        )
        self.assertEqual(updated.allowed_email_domains, ["example.test"])
        self.assertEqual(updated.lock_version, current.lock_version + 1)
        with self.assertRaises(RevisionConflict):
            update_membership_settings(
                actor=owner,
                organization=organization,
                expected_version=current.lock_version,
                public_join_enabled=True,
                join_requires_approval=True,
                allowed_email_domains=["*.example.test"],
                default_role=RoleCode.LEARNER,
                invitation_expiry_hours=72,
                allow_admin_managed_accounts=True,
                allow_bulk_invitations=False,
            )


class OnboardingApiTests(TestCase):
    def verified_user(self, email: str):
        user = get_user_model().objects.create_user(
            email=email, password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        return user

    def test_invitation_response_never_exposes_token_or_digest(self) -> None:
        owner = get_user_model().objects.create_user(
            email="owner@example.test", password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=owner, email=owner.email, primary=True, verified=True
        )
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        self.client.force_login(owner)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/api/v1/organizations/{organization.slug}/invitations/",
                {"email": "invitee@example.test", "roles": [RoleCode.LEARNER]},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("token", response.json())
        self.assertNotIn("token_digest", response.json())
        self.assertEqual(MembershipInvitation.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["invitee@example.test"])
        self.assertIn("/invitaciones/activar?token=", message.body)
        self.assertEqual(message.alternatives[0].mimetype, "text/html")
        self.assertIn("Activar mi acceso", message.alternatives[0].content)
        self.assertTrue(
            message.extra_headers["Resend-Idempotency-Key"].startswith(
                "membership-invitation-"
            )
        )

    def test_administrator_recovery_email_does_not_bind_flow_to_its_session(
        self,
    ) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        learner = self.verified_user("learner@example.test")
        membership = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=learner,
            roles={RoleCode.LEARNER},
        )
        self.client.force_login(owner)
        session_key = self.client.session.session_key

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/api/v1/organizations/{organization.slug}/memberships/"
                f"{membership.pk}/password-recovery/"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sent": True})
        self.assertEqual(self.client.session.session_key, session_key)
        self.assertNotIn("account_password_reset_verification", self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [learner.email])
        self.assertIn("/auth/recuperar-contrasena", message.body)
        self.assertNotIn("password_reset", message.body)
        self.assertEqual(message.alternatives[0].mimetype, "text/html")
        self.assertTrue(
            message.extra_headers["Resend-Idempotency-Key"].startswith(
                "member-recovery-"
            )
        )
        self.assertTrue(
            MembershipEvent.objects.filter(
                membership=membership,
                event_type=MembershipEventType.PASSWORD_RECOVERY_SENT,
                actor=owner,
            ).exists()
        )

    def test_learner_cannot_send_recovery_for_another_member(self) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        learner = self.verified_user("learner@example.test")
        membership = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=learner,
            roles={RoleCode.LEARNER},
        )
        self.client.force_login(learner)

        response = self.client.post(
            f"/api/v1/organizations/{organization.slug}/memberships/"
            f"{membership.pk}/password-recovery/"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_member_directory_filters_are_remote_and_combinable(self) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        learner = self.verified_user("ana.diaz@example.test")
        membership = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=learner,
            roles={RoleCode.LEARNER},
        )
        membership.institutional_profile.member_type = "Estudiante"
        membership.institutional_profile.preferred_name = "Ana Díaz"
        membership.institutional_profile.save(
            update_fields=("member_type", "preferred_name", "updated_at")
        )
        self.client.force_login(owner)

        response = self.client.get(
            f"/api/v1/organizations/{organization.slug}/memberships/",
            {
                "q": "Ana",
                "status": "active",
                "role": "learner",
                "member_type": "estudiante",
                "ordering": "-joined_at",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["membership_id"], str(membership.id)
        )

    def test_managed_account_is_inactive_until_the_person_activates_it(self) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        settings = organization.membership_settings
        settings.allow_admin_managed_accounts = True
        settings.save(update_fields=("allow_admin_managed_accounts", "updated_at"))
        self.client.force_login(owner)

        response = self.client.post(
            f"/api/v1/organizations/{organization.slug}/managed-accounts/",
            {
                "email": "estudiante@example.test",
                "roles": [RoleCode.LEARNER],
                "given_name": "Ana",
                "family_name": "Díaz",
                "member_type": "Estudiante",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(email="estudiante@example.test")
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.assertFalse(
            Membership.objects.filter(organization=organization, user=user).exists()
        )

    def test_managed_account_email_can_be_corrected_without_exposing_a_token(
        self,
    ) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        self.client.force_login(owner)
        created = self.client.post(
            f"/api/v1/organizations/{organization.slug}/managed-accounts/",
            {
                "email": "wrong@example.test",
                "roles": [RoleCode.LEARNER],
                "given_name": "Ana",
                "family_name": "Díaz",
                "member_type": "Estudiante",
            },
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        invitation_id = created.json()["id"]

        corrected = self.client.patch(
            f"/api/v1/organizations/{organization.slug}/invitations/{invitation_id}/managed-email/",
            {"email": "ana.diaz@example.test"},
            content_type="application/json",
        )
        self.assertEqual(corrected.status_code, 200)
        self.assertEqual(corrected.json()["email"], "ana.diaz@example.test")
        self.assertNotIn("token", corrected.json())
        self.assertNotIn("token_digest", corrected.json())
        user = get_user_model().objects.get(
            pk=MembershipInvitation.objects.get(pk=invitation_id).existing_user_id
        )
        self.assertEqual(user.email, "ana.diaz@example.test")
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())

    def test_bulk_member_lifecycle_is_atomic_and_rejects_cross_organization_ids(
        self,
    ) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        learner = self.verified_user("learner@example.test")
        member = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=learner,
            roles={RoleCode.LEARNER},
        )
        other_owner = self.verified_user("other-owner@example.test")
        other = create_organization_with_owner(
            actor=other_owner, name="Otra", slug="otra"
        )
        foreign = Membership.objects.get(organization=other, user=other_owner)
        self.client.force_login(owner)
        base = f"/api/v1/organizations/{organization.slug}/memberships/bulk-transition/"

        rejected = self.client.post(
            base,
            {"membership_ids": [str(member.id), str(foreign.id)], "action": "suspend"},
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 403)
        member.refresh_from_db()
        self.assertEqual(member.status, "active")

        suspended = self.client.post(
            base,
            {"membership_ids": [str(member.id)], "action": "suspend"},
            content_type="application/json",
        )
        self.assertEqual(suspended.status_code, 200)
        self.assertEqual(suspended.json()[0]["status"], "suspended")

    def test_invitation_list_materializes_expired_pending_records(self) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        invitation, _ = create_invitation(
            actor=owner,
            organization=organization,
            email="late@example.test",
            roles={RoleCode.LEARNER},
            invitation_type=InvitationType.NEW_USER,
        )
        invitation.expires_at = timezone.now() - timedelta(minutes=1)
        invitation.save(update_fields=("expires_at", "updated_at"))
        self.client.force_login(owner)

        response = self.client.get(
            f"/api/v1/organizations/{organization.slug}/invitations/",
            {"status": "expired"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["status"], "expired")

    def test_owner_can_manage_settings_invitations_profiles_and_join_requests(
        self,
    ) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        self.client.force_login(owner)
        base = f"/api/v1/organizations/{organization.slug}"

        settings = self.client.get(f"{base}/membership-settings/")
        self.assertEqual(settings.status_code, 200)
        updated = self.client.put(
            f"{base}/membership-settings/",
            {
                "expected_version": settings.json()["lock_version"],
                "public_join_enabled": True,
                "join_requires_approval": True,
                "allowed_email_domains": [],
                "default_role": RoleCode.LEARNER,
                "invitation_expiry_hours": 48,
                "allow_admin_managed_accounts": True,
                "allow_bulk_invitations": False,
            },
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertTrue(updated.json()["public_join_enabled"])

        invitation = self.client.post(
            f"{base}/invitations/",
            {"email": "invited@example.test", "roles": [RoleCode.LEARNER]},
            content_type="application/json",
        )
        self.assertEqual(invitation.status_code, 201)
        invitation_id = invitation.json()["id"]
        self.assertEqual(self.client.get(f"{base}/invitations/").status_code, 200)
        self.assertEqual(
            self.client.post(f"{base}/invitations/{invitation_id}/resend/").status_code,
            200,
        )
        self.assertEqual(
            self.client.post(f"{base}/invitations/{invitation_id}/revoke/").status_code,
            200,
        )

        owner_membership = Membership.objects.get(organization=organization, user=owner)
        profile = self.client.get(f"{base}/memberships/{owner_membership.id}/profile/")
        self.assertEqual(profile.status_code, 200)
        changed = self.client.patch(
            f"{base}/memberships/{owner_membership.id}/profile/",
            {"preferred_name": "Rectora", "administrative_notes": "Verificado"},
            content_type="application/json",
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["preferred_name"], "Rectora")
        self.assertEqual(
            self.client.post(
                f"{base}/memberships/{owner_membership.id}/revoke-sessions/"
            ).status_code,
            200,
        )

        applicant = self.verified_user("applicant@example.test")
        self.client.force_login(applicant)
        joined = self.client.post(f"{base}/join/")
        self.assertEqual(joined.status_code, 201)
        join_request_id = joined.json()["id"]

        self.client.force_login(owner)
        self.assertEqual(self.client.get(f"{base}/join-requests/").status_code, 200)
        reviewed = self.client.post(f"{base}/join-requests/{join_request_id}/approve/")
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.json()["status"], "approved")
        self.assertTrue(
            Membership.objects.filter(
                organization=organization, user=applicant
            ).exists()
        )

    def test_bulk_invitation_preview_requires_clean_csv_before_atomic_confirm(
        self,
    ) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        settings = organization.membership_settings
        settings.allow_bulk_invitations = True
        settings.save(update_fields=("allow_bulk_invitations", "updated_at"))
        self.client.force_login(owner)
        base = f"/api/v1/organizations/{organization.slug}/invitations/bulk"
        invalid = self.client.post(
            f"{base}/preview/",
            {
                "file": SimpleUploadedFile(
                    "invitaciones.csv",
                    b"email,given_name,family_name,member_type,institutional_id,roles\n"
                    b"owner@example.test,Ana,Diaz,student,ID-1,owner\n",
                    content_type="text/csv",
                )
            },
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(invalid.json()["valid_count"], 0)
        self.assertEqual(invalid.json()["issues"][0]["field"], "roles")

        preview = self.client.post(
            f"{base}/preview/",
            {
                "file": SimpleUploadedFile(
                    "invitaciones.csv",
                    b"email,given_name,family_name,member_type,institutional_id,roles\n"
                    b"bulk@example.test,Ana,Diaz,student,ID-2,learner|instructor\n",
                    content_type="text/csv",
                )
            },
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["valid_count"], 1)
        confirmed = self.client.post(
            f"{base}/confirm/",
            {"preview_id": preview.json()["preview_id"]},
            content_type="application/json",
        )
        self.assertEqual(confirmed.status_code, 201)
        self.assertEqual(confirmed.json()["created"], 1)
        self.assertTrue(
            MembershipInvitation.objects.filter(email="bulk@example.test").exists()
        )
