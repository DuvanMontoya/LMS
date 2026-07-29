from __future__ import annotations

from django.db import connection

_GRAPH_SQL = {
    "subject": "catalog_subjectprerequisite",
    "concept": "catalog_conceptprerequisite",
}


def would_create_cycle(*, graph: str, node_id: str, prerequisite_id: str) -> bool:
    """Return whether prerequisite already reaches node using static parameterized SQL."""
    table = _GRAPH_SQL[graph]
    sql = f"""
        WITH RECURSIVE reachable(id) AS (
          SELECT prerequisite_id FROM {table} WHERE subject_id = %s
          UNION ALL
          SELECT edge.prerequisite_id
          FROM {table} edge JOIN reachable ON edge.subject_id = reachable.id
        ) CYCLE id SET is_cycle USING cycle_path
        SELECT EXISTS(SELECT 1 FROM reachable WHERE id = %s)
    """
    if graph == "concept":
        sql = sql.replace("subject_id", "concept_id")
    with connection.cursor() as cursor:
        cursor.execute(sql, [prerequisite_id, node_id])
        result = cursor.fetchone()
    return bool(result and result[0])
