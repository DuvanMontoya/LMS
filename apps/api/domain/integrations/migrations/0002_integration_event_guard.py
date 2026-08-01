from django.db import migrations


def add_event_append_only_guard(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION integrations_reject_event_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'IntegrationEvent is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        cursor.execute(
            """
            CREATE TRIGGER integrations_event_append_only
            BEFORE UPDATE OR DELETE ON integrations_integrationevent
            FOR EACH ROW EXECUTE FUNCTION integrations_reject_event_mutation();
            """
        )


def remove_event_append_only_guard(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DROP TRIGGER IF EXISTS integrations_event_append_only "
            "ON integrations_integrationevent"
        )
        cursor.execute("DROP FUNCTION IF EXISTS integrations_reject_event_mutation()")


class Migration(migrations.Migration):
    dependencies = [("integrations", "0001_initial")]

    operations = [
        migrations.RunPython(add_event_append_only_guard, remove_event_append_only_guard),
    ]
