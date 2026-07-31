from django.db import migrations


CREATE_SQL = """
CREATE OR REPLACE FUNCTION assets_reject_append_only_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER assets_variant_append_only
BEFORE UPDATE OR DELETE ON assets_assetvariant
FOR EACH ROW EXECUTE FUNCTION assets_reject_append_only_mutation();

CREATE TRIGGER assets_event_append_only
BEFORE UPDATE OR DELETE ON assets_assetevent
FOR EACH ROW EXECUTE FUNCTION assets_reject_append_only_mutation();

CREATE OR REPLACE FUNCTION assets_protect_terminal_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'asset versions cannot be deleted'
            USING ERRCODE = '55000';
    END IF;
    IF OLD.status IN ('ready', 'rejected', 'failed') AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'terminal asset versions are immutable'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER assets_version_terminal_immutable
BEFORE UPDATE OR DELETE ON assets_assetversion
FOR EACH ROW EXECUTE FUNCTION assets_protect_terminal_version();

CREATE OR REPLACE FUNCTION assets_protect_completed_upload_part()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    session_status text;
BEGIN
    SELECT status INTO session_status
    FROM assets_assetuploadsession
    WHERE id = OLD.upload_session_id;
    IF session_status = 'completed' THEN
        RAISE EXCEPTION 'parts of completed uploads are append-only'
            USING ERRCODE = '55000';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER assets_upload_part_completed_immutable
BEFORE UPDATE OR DELETE ON assets_assetuploadpart
FOR EACH ROW EXECUTE FUNCTION assets_protect_completed_upload_part();
"""

DROP_SQL = """
DROP TRIGGER IF EXISTS assets_upload_part_completed_immutable
    ON assets_assetuploadpart;
DROP FUNCTION IF EXISTS assets_protect_completed_upload_part();
DROP TRIGGER IF EXISTS assets_version_terminal_immutable
    ON assets_assetversion;
DROP FUNCTION IF EXISTS assets_protect_terminal_version();
DROP TRIGGER IF EXISTS assets_event_append_only ON assets_assetevent;
DROP TRIGGER IF EXISTS assets_variant_append_only ON assets_assetvariant;
DROP FUNCTION IF EXISTS assets_reject_append_only_mutation();
"""


class Migration(migrations.Migration):
    dependencies = [("assets", "0001_initial")]

    operations = [migrations.RunSQL(CREATE_SQL, reverse_sql=DROP_SQL)]
