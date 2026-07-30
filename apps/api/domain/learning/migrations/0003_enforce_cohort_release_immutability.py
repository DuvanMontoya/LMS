from django.db import migrations


FORWARD_SQL = """
CREATE OR REPLACE FUNCTION learning_reject_enrolled_cohort_release_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.release_id IS DISTINCT FROM OLD.release_id
       AND EXISTS (
           SELECT 1
           FROM learning_courseenrollment
           WHERE cohort_id = OLD.id
       )
    THEN
        RAISE EXCEPTION 'learning cohort release is immutable after enrollment'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER learning_cohort_release_immutable
BEFORE UPDATE OF release_id ON learning_learningcohort
FOR EACH ROW
EXECUTE FUNCTION learning_reject_enrolled_cohort_release_change();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS learning_cohort_release_immutable
ON learning_learningcohort;
DROP FUNCTION IF EXISTS learning_reject_enrolled_cohort_release_change();
"""


class Migration(migrations.Migration):
    dependencies = [("learning", "0002_enforce_learning_event_immutability")]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
