# Matriz de aceptación: membresías, grupos y matrículas

Fecha de inicio: 2026-08-01. Esta matriz reemplaza sólo los criterios de
cohortes/matrículas afectados por ADR 0035; no invalida el historial de
aceptación de Phase 12.

| ID | Prioridad | Criterio | Estado | Evidencia requerida |
|---|---|---|---|---|
| R-01 | P0 | `Membership` y sus role assignments siguen siendo la única fuente de roles institucionales. | PENDIENTE | Pruebas de policy y regresión de roles. |
| R-02 | P0 | Un docente no lista, abre, califica, programa ni gestiona un grupo de curso ajeno. | PENDIENTE | API/security, assessments, scheduling y dos contextos Chromium. |
| R-03 | P0 | Owner/admin conservan alcance institucional sin que el superuser cree visibilidad institucional implícita. | PENDIENTE | Policies y API anti-IDOR. |
| R-04 | P1 | Un grupo académico sincronizado matricula sólo learners activos y registra su procedencia. | PENDIENTE | PostgreSQL, servicios y E2E. |
| R-05 | P1 | Una baja cierra asignación y suspende sólo el acceso nacido de sincronización; no borra progreso. | PENDIENTE | Servicios, triggers y regresión de progreso. |
| R-06 | P1 | Traslado mismo curso/release preserva matrícula y progreso; otro release exige upgrade explícito. | PENDIENTE | Concurrencia y migración PostgreSQL. |
| R-07 | P1 | Ventana heredada sigue la política del grupo; excepción individual queda visible e intacta. | PENDIENTE | Modelos, access y UI. |
| R-08 | P1 | Backfill conserva acceso y deja `legacy_migration`; ninguna cohorte existente se sincroniza sin confirmación. | PENDIENTE | Migración limpia y base con datos. |
| R-09 | P1 | Roster, staff y matrícula individual usan búsqueda remota, paginación, selección persistente y `expected_version`. | PENDIENTE | OpenAPI, API, Vitest y Chromium a 390 px. |
| R-10 | P1 | Preview no escribe; confirmación idempotente bajo doble sincronización y conflicto 409. | PENDIENTE | TransactionTestCase PostgreSQL. |
| R-11 | P1 | Assessments conserva el grupo de curso efectivo como snapshot y scheduling exige matrícula/asignación efectivas para nuevas series. | PENDIENTE | Regresión transversal. |
| R-12 | P2 | La UI emplea Personas, Grupos académicos, Grupos de curso y Matrículas individuales; “cohorte” sólo aparece como compatibilidad técnica. | PENDIENTE | Chromium, axe, teclado y 390 px. |
| R-13 | P1 | No hay borrado físico ni mutación de hechos cerrados de roster/asignación. | PENDIENTE | SQL directo en PostgreSQL. |
| R-14 | P1 | `pnpm learning:check`, `learning:test`, `assessments:test`, `scheduling:test`, `web:test`, `check` y `learning:e2e` concluyen con evidencia proporcional. | PENDIENTE | Logs fechados de ejecución. |
