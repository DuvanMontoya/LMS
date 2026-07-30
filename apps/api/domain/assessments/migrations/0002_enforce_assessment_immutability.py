from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE OR REPLACE FUNCTION assessments_reject_immutable_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'immutable assessment record: % is not allowed on %',
        TG_OP, TG_TABLE_NAME
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER assessments_qtransition_reject_update
BEFORE UPDATE ON assessments_questionrevisiontransition
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();
CREATE TRIGGER assessments_qtransition_reject_delete
BEFORE DELETE ON assessments_questionrevisiontransition
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();

CREATE TRIGGER assessments_qversion_reject_update
BEFORE UPDATE ON assessments_questionversion
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();
CREATE TRIGGER assessments_qversion_reject_delete
BEFORE DELETE ON assessments_questionversion
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();

CREATE TRIGGER assessments_bankversion_reject_update
BEFORE UPDATE ON assessments_questionbankversion
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();
CREATE TRIGGER assessments_bankversion_reject_delete
BEFORE DELETE ON assessments_questionbankversion
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();

CREATE TRIGGER assessments_atransition_reject_update
BEFORE UPDATE ON assessments_assessmentrevisiontransition
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();
CREATE TRIGGER assessments_atransition_reject_delete
BEFORE DELETE ON assessments_assessmentrevisiontransition
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();

CREATE TRIGGER assessments_aversion_reject_update
BEFORE UPDATE ON assessments_assessmentversion
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();
CREATE TRIGGER assessments_aversion_reject_delete
BEFORE DELETE ON assessments_assessmentversion
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();

CREATE TRIGGER assessments_attemptitem_reject_update
BEFORE UPDATE ON assessments_attemptitem
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();
CREATE TRIGGER assessments_attemptitem_reject_delete
BEFORE DELETE ON assessments_attemptitem
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();

CREATE TRIGGER assessments_manualgrade_reject_update
BEFORE UPDATE ON assessments_manualgradedecision
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();
CREATE TRIGGER assessments_manualgrade_reject_delete
BEFORE DELETE ON assessments_manualgradedecision
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();

CREATE TRIGGER assessments_attemptevent_reject_update
BEFORE UPDATE ON assessments_attemptevent
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();
CREATE TRIGGER assessments_attemptevent_reject_delete
BEFORE DELETE ON assessments_attemptevent
FOR EACH ROW EXECUTE FUNCTION assessments_reject_immutable_change();
""",
            reverse_sql="""
DROP TRIGGER IF EXISTS assessments_attemptevent_reject_delete
    ON assessments_attemptevent;
DROP TRIGGER IF EXISTS assessments_attemptevent_reject_update
    ON assessments_attemptevent;
DROP TRIGGER IF EXISTS assessments_manualgrade_reject_delete
    ON assessments_manualgradedecision;
DROP TRIGGER IF EXISTS assessments_manualgrade_reject_update
    ON assessments_manualgradedecision;
DROP TRIGGER IF EXISTS assessments_attemptitem_reject_delete
    ON assessments_attemptitem;
DROP TRIGGER IF EXISTS assessments_attemptitem_reject_update
    ON assessments_attemptitem;
DROP TRIGGER IF EXISTS assessments_aversion_reject_delete
    ON assessments_assessmentversion;
DROP TRIGGER IF EXISTS assessments_aversion_reject_update
    ON assessments_assessmentversion;
DROP TRIGGER IF EXISTS assessments_atransition_reject_delete
    ON assessments_assessmentrevisiontransition;
DROP TRIGGER IF EXISTS assessments_atransition_reject_update
    ON assessments_assessmentrevisiontransition;
DROP TRIGGER IF EXISTS assessments_bankversion_reject_delete
    ON assessments_questionbankversion;
DROP TRIGGER IF EXISTS assessments_bankversion_reject_update
    ON assessments_questionbankversion;
DROP TRIGGER IF EXISTS assessments_qversion_reject_delete
    ON assessments_questionversion;
DROP TRIGGER IF EXISTS assessments_qversion_reject_update
    ON assessments_questionversion;
DROP TRIGGER IF EXISTS assessments_qtransition_reject_delete
    ON assessments_questionrevisiontransition;
DROP TRIGGER IF EXISTS assessments_qtransition_reject_update
    ON assessments_questionrevisiontransition;
DROP FUNCTION IF EXISTS assessments_reject_immutable_change();
""",
        )
    ]
