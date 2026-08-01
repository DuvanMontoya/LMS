from django.db import migrations


def create_legacy_profiles_and_settings(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Membership = apps.get_model("organizations", "Membership")
    OrganizationMembershipSettings = apps.get_model(
        "organizations", "OrganizationMembershipSettings"
    )
    OrganizationMemberProfile = apps.get_model(
        "organizations", "OrganizationMemberProfile"
    )
    for organization in Organization.objects.iterator():
        OrganizationMembershipSettings.objects.get_or_create(organization=organization)
    for membership in Membership.objects.iterator():
        OrganizationMemberProfile.objects.get_or_create(membership=membership)


def add_event_append_only_guard(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION organizations_reject_membership_event_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'MembershipEvent is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        cursor.execute(
            """
            CREATE TRIGGER organizations_membership_event_append_only
            BEFORE UPDATE OR DELETE ON organizations_membershipevent
            FOR EACH ROW EXECUTE FUNCTION organizations_reject_membership_event_mutation();
            """
        )


def remove_event_append_only_guard(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DROP TRIGGER IF EXISTS organizations_membership_event_append_only "
            "ON organizations_membershipevent"
        )
        cursor.execute(
            "DROP FUNCTION IF EXISTS organizations_reject_membership_event_mutation()"
        )


class Migration(migrations.Migration):
    dependencies = [("organizations", "0002_membershipevent_details_and_more")]

    operations = [
        migrations.RunPython(
            create_legacy_profiles_and_settings, migrations.RunPython.noop
        ),
        migrations.RunPython(add_event_append_only_guard, remove_event_append_only_guard),
    ]
