# Matriz de aceptación: membresías, grupos y matrículas

Fecha de inicio: 2026-08-01. Última actualización: 2026-08-02. Esta matriz
reemplaza sólo los criterios de grupos/matrículas afectados por ADR 0035; no
invalida el historial de aceptación de Phase 12. `PASS` exige evidencia
ejecutada; `PARCIAL` identifica con precisión la puerta todavía pendiente.

| ID | Prioridad | Criterio | Estado | Evidencia requerida |
|---|---|---|---|---|
| R-01 | P0 | `Membership` y sus role assignments siguen siendo la única fuente de roles institucionales. | PASS | `organizations:test` 43/43; matriz de policies sin roles copiados a identidad. |
| R-02 | P0 | Un docente no lista, abre, califica, programa ni gestiona un grupo de curso ajeno. | PARCIAL | API anti-IDOR de learning/assessments y scheduling en PostgreSQL están verdes; falta repetir dos contextos Chromium con grupos distintos. |
| R-03 | P0 | Administrator conserva operación institucional; owner queda limitado a gobierno y superuser no obtiene visibilidad tenant implícita. | PASS | `organizations:test` 43/43 y regresiones API/policy de owner, administrator y superuser. |
| R-04 | P1 | Un grupo académico sincronizado matricula sólo learners activos y registra su procedencia. | PASS | Servicio PostgreSQL excluye membresía suspendida y registra `academic_group_sync`. |
| R-05 | P1 | Una baja cierra asignación y suspende sólo el acceso nacido de sincronización; no borra progreso. | PASS | Regresión de roster conserva progreso completado y acceso manual, y cierra asignaciones históricas. |
| R-06 | P1 | Traslado mismo curso/release preserva matrícula y progreso; otro release exige upgrade explícito. | PASS | Prueba de traslado conserva los mismos IDs de matrícula/asignación/progreso; upgrade y carrera están cubiertos. |
| R-07 | P1 | Ventana heredada sigue la política del grupo; excepción individual queda visible e intacta. | PASS | Regresión de ventanas/withdrawal y serialización de acceso efectivo. |
| R-08 | P1 | Backfill conserva acceso y deja `legacy_migration`; ningún grupo existente se sincroniza sin confirmación. | PASS | Funciones reales de migraciones 0006/0007 ejecutadas sobre esquema PostgreSQL: modo manual, revisión requerida y cero altas automáticas. |
| R-09 | P1 | Roster, staff y matrícula individual usan búsqueda remota, paginación, selección persistente y `expected_version`. | PARCIAL | OpenAPI/API y Vitest cubren paginación y selección entre páginas; falta evidencia Chromium específica a 390 px. |
| R-10 | P1 | Preview no escribe; confirmación idempotente bajo doble sincronización y conflicto 409. | PASS | Conteos antes/después del preview y `TransactionTestCase`: un éxito, un conflicto, una sola asignación/evento. |
| R-11 | P1 | Assessments conserva el grupo de curso efectivo como snapshot y scheduling exige matrícula/asignación efectivas para nuevas series. | PASS | Regresiones transversales de delivery/gradebook/analítica/regrading y host vigente en el grupo. |
| R-12 | P2 | La UI emplea Personas, Grupos académicos, Grupos de curso y Matrículas individuales; “cohorte” sólo aparece como compatibilidad técnica. | PARCIAL | Etiquetas y rutas de producto están migradas; falta cierre conjunto Chromium, axe, teclado y 390 px. |
| R-13 | P1 | No hay borrado físico ni mutación de hechos cerrados de roster/asignación. | PASS | Triggers comprobados con SQL directo en PostgreSQL. |
| R-14 | P1 | `pnpm learning:check`, `learning:test`, `assessments:test`, `scheduling:test`, `web:test`, `check` y `learning:e2e` concluyen con evidencia proporcional. | EN CURSO | Checks de dominio y suites PostgreSQL específicas están verdes; faltan cierre web/build/check, Chromium y `learning:e2e` de esta revisión. |
