# 0018 — Organization-scoped academic taxonomy and curriculum graph

Fecha: 2026-07-29. Estado: aceptado.

`domain.catalog` posee la taxonomía institucional: Área → Disciplina → Asignatura, el árbol materialized-path de temas, conceptos reutilizables, objetivos y dos DAG explícitos de prerrequisitos. La organización llega por la ruta y por las relaciones estructurales; no se duplican claves organizacionales en disciplinas, asignaturas, temas u objetivos.

Se usa `django-treebeard` con `MP_Node` sólo para `Topic`. Sus mutaciones bloquean la asignatura y se verifican con `find_problems()`. Los grafos se mantienen en tablas relacionales, se inspeccionan mediante CTE recursivas parametrizadas y bloquean la organización para serializar mutaciones. No se usa una base de grafos, `GenericForeignKey`, JSON relacional ni tipos genéricos.

`django-filter` queda reservado para filtros declarativos de la API. El acceso usa capacidades de `organizations`; estados activo/archivado sustituyen el borrado físico. Cursos, módulos y contenido quedan aplazados al Prompt 9.
