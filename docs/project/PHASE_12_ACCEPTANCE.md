# Phase 12 acceptance

Fecha de cierre: 2026-07-30.  
Commit base y final: `9d6a33d704ad94917ec80af1d5cf77b2bea6f287`.

La clasificación se apoya en ADR 0022, `docs/architecture/LEARNING.md`, las
migraciones y pruebas de `domain.learning`, el contrato OpenAPI generado, las
superficies web, `apps/web/e2e/learning.spec.ts` y la validación real descrita
al final. No hay criterios esenciales en `FAIL` o `BLOCKED`.

| # | Estado | Evidencia |
| -: | :---: | --- |
| 1 | PASS | `domain.learning` es dueño exclusivo de entrega y progreso. |
| 2 | PASS | El check modular prueba que publishing no importa learning. |
| 3 | PASS | El check modular prueba que courses no importa learning. |
| 4 | PASS | No se añadió un LMS externo. |
| 5 | PASS | No se añadió Celery. |
| 6 | PASS | Se definieron seis capacidades `learning.*`. |
| 7 | PASS | La matriz por rol está codificada y probada. |
| 8 | PASS | Learner carece de administración learning. |
| 9 | PASS | `LearningCohort` usa UUID. |
| 10 | PASS | Cohorte pertenece a una organización. |
| 11 | PASS | Cohorte pertenece a un curso. |
| 12 | PASS | Cohorte fija un release verificado del curso. |
| 13 | PASS | Modelo y trigger impiden cambiarlo con matrículas. |
| 14 | PASS | Constraint garantiza slug único sin distinguir mayúsculas. |
| 15 | PASS | Cohorte admite ventanas opcionales válidas. |
| 16 | PASS | Cohorte se archiva; no existe DELETE físico. |
| 17 | PASS | `CourseEnrollment` usa UUID. |
| 18 | PASS | Matrícula referencia membership institucional. |
| 19 | PASS | Matrícula referencia curso de la organización. |
| 20 | PASS | Constraint permite máximo una matrícula no revocada. |
| 21 | PASS | Las revocadas permanecen como historial. |
| 22 | PASS | Estado active implementado. |
| 23 | PASS | Estado suspended implementado. |
| 24 | PASS | Estado revoked implementado. |
| 25 | PASS | Revoked es terminal. |
| 26 | PASS | Reincorporación crea matrícula nueva. |
| 27 | PASS | Assignment histórico usa UUID. |
| 28 | PASS | Servicios mantienen intervalos contiguos. |
| 29 | PASS | Constraint permite máximo un assignment vigente. |
| 30 | PASS | Release asignado debe pertenecer al curso. |
| 31 | PASS | Upgrade conserva el assignment anterior cerrado. |
| 32 | PASS | Upgrade crea progreso nuevo sin copiar progreso. |
| 33 | PASS | Matrícula de cohorte rechaza upgrade individual. |
| 34 | PASS | Progreso se vincula al assignment/release asignado. |
| 35 | PASS | Nueva publicación no modifica matrícula ni progreso. |
| 36 | PASS | `CourseProgress` usa UUID. |
| 37 | PASS | Total de unidades se fija desde el snapshot. |
| 38 | PASS | Completadas se mantiene dentro de límites. |
| 39 | PASS | Porcentaje determinista en basis points. |
| 40 | PASS | Estado not_started implementado. |
| 41 | PASS | Estado in_progress implementado. |
| 42 | PASS | Estado completed implementado. |
| 43 | PASS | `UnitProgress` es único por progreso/unidad. |
| 44 | PASS | Ausencia de fila equivale a not_started. |
| 45 | PASS | Apertura de unidad implementada. |
| 46 | PASS | Completado explícito implementado. |
| 47 | PASS | Reapertura implementada. |
| 48 | PASS | Completar de nuevo es idempotente. |
| 49 | PASS | Última unidad completa el curso exactamente una vez. |
| 50 | PASS | Reabrir unidad reabre el curso. |
| 51 | PASS | Contadores se actualizan en la misma transacción. |
| 52 | PASS | Progreso tiene versión optimista. |
| 53 | PASS | `expected_version` obsoleto devuelve 409 estable. |
| 54 | PASS | Concurrencia no duplica contadores. |
| 55 | PASS | Finalización concurrente emite una transición. |
| 56 | PASS | Continuidad guarda última unidad del snapshot. |
| 57 | PASS | Continuidad guarda último nodo semántico. |
| 58 | PASS | Nodo se valida contra el snapshot. |
| 59 | PASS | Entrega no consulta contenido vivo. |
| 60 | PASS | Last-write-wins de posición está documentado. |
| 61 | PASS | Movimientos de posición no generan eventos masivos. |
| 62 | PASS | Reanudación en nodo válido funciona. |
| 63 | PASS | Nodo ausente aplica fallback seguro. |
| 64 | PASS | `LearningEvent` usa UUID. |
| 65 | PASS | Eventos se crean append-only. |
| 66 | PASS | Trigger PostgreSQL rechaza UPDATE. |
| 67 | PASS | Trigger PostgreSQL rechaza DELETE. |
| 68 | PASS | Matrícula individual manual implementada. |
| 69 | PASS | Matrícula por cohorte implementada. |
| 70 | PASS | Lote de cohorte es atómico. |
| 71 | PASS | Duplicados se rechazan sin parcialidad. |
| 72 | PASS | Membership inactiva se rechaza. |
| 73 | PASS | Membership de otra organización se rechaza. |
| 74 | PASS | Publicación retirada deniega entrega. |
| 75 | PASS | Ventana futura deniega entrega. |
| 76 | PASS | Ventana vencida deniega entrega. |
| 77 | PASS | Suspensión deniega entrega. |
| 78 | PASS | Reactivación restaura el progreso previo. |
| 79 | PASS | Revocación corta acceso de forma terminal. |
| 80 | PASS | Suspensión preserva progreso histórico. |
| 81 | PASS | Revocación preserva progreso administrativo. |
| 82 | PASS | Upgrade explícito funciona. |
| 83 | PASS | Downgrade retroactivo no existe. |
| 84 | PASS | Learner sólo consulta su propia matrícula. |
| 85 | PASS | Administración exige capacidad autorizada. |
| 86 | PASS | Author no puede matricular. |
| 87 | PASS | Reviewer respeta la matriz definida. |
| 88 | PASS | Instructor sólo consulta progreso autorizado. |
| 89 | PASS | `is_staff` no omite políticas. |
| 90 | PASS | Superuser tiene bypass administrativo explícito y acotado. |
| 91 | PASS | Biblioteca del learner requiere matrícula. |
| 92 | PASS | `course.published.view` no sustituye matrícula. |
| 93 | PASS | El estudiante lee sólo snapshot asignado. |
| 94 | PASS | Selectores de entrega no consultan authoring. |
| 95 | PASS | Matrícula R1 continúa en R1 tras publicar R2. |
| 96 | PASS | Cada assignment tiene progreso separado. |
| 97 | PASS | API está versionada bajo `/api/v1`. |
| 98 | PASS | API learning no expone DELETE. |
| 99 | PASS | Serializers cierran mass assignment. |
| 100 | PASS | Matrícula ajena devuelve 404. |
| 101 | PASS | Progreso ajeno devuelve 404. |
| 102 | PASS | Unidad ajena devuelve 404. |
| 103 | PASS | Unidad de otro release devuelve 404. |
| 104 | PASS | Cohorte de otra organización devuelve 404. |
| 105 | PASS | OpenAPI se genera válido. |
| 106 | PASS | Schema se genera sin warnings. |
| 107 | PASS | Cliente TypeScript fue regenerado. |
| 108 | PASS | Checks de drift pasan. |
| 109 | PASS | Existe dashboard “Mi aprendizaje”. |
| 110 | PASS | Existe outline con progreso. |
| 111 | PASS | Existe lector académico snapshot-only. |
| 112 | PASS | Progreso usa elemento nativo accesible. |
| 113 | PASS | UI permite completar unidad. |
| 114 | PASS | UI permite reabrir unidad. |
| 115 | PASS | UI ofrece continuar. |
| 116 | PASS | UI restaura el nodo semántico. |
| 117 | PASS | Tracker usa observer, debounce y pagehide. |
| 118 | PASS | No se usa localStorage para progreso o posición. |
| 119 | PASS | No se almacena JWT en navegador. |
| 120 | PASS | Existe dashboard administrativo. |
| 121 | PASS | Existen gestión y detalle de cohortes. |
| 122 | PASS | Existen listado y detalle de matrículas. |
| 123 | PASS | Existe progreso institucional agregado e individual. |
| 124 | PASS | Controles tienen labels accesibles. |
| 125 | PASS | Tablas incluyen caption. |
| 126 | PASS | Restauración gestiona foco. |
| 127 | PASS | Flujos críticos funcionan con teclado. |
| 128 | PASS | Axe WCAG A/AA pasa. |
| 129 | PASS | 390 px no presenta overflow horizontal. |
| 130 | PASS | Demo es idempotente y preserva estado. |
| 131 | PASS | Demo se rechaza en producción. |
| 132 | PASS | README explica matrícula demo. |
| 133 | PASS | README explica release pinning. |
| 134 | PASS | Se inspeccionó el flujo en Chromium real. |
| 135 | PASS | Inspección visual y correcciones están documentadas. |
| 136 | PASS | E2E crea y usa cohorte. |
| 137 | PASS | E2E crea matrícula de cohorte e individual. |
| 138 | PASS | E2E recorre aprendizaje real. |
| 139 | PASS | E2E completa todas las unidades. |
| 140 | PASS | E2E prueba suspensión y reactivación. |
| 141 | PASS | E2E prueba revocación y reincorporación. |
| 142 | PASS | E2E prueba pinning R1 tras R2. |
| 143 | PASS | E2E prueba upgrade explícito a R2. |
| 144 | PASS | E2E obtiene 200/409 con dos contextos. |
| 145 | PASS | E2E prueba cross-org 404. |
| 146 | PASS | E2E prueba ventana futura. |
| 147 | PASS | E2E prueba withdrawal. |
| 148 | PASS | Runner elimina la base E2E. |
| 149 | PASS | Runner limpia sólo el prefijo Redis E2E. |
| 150 | PASS | Runner limpia correo E2E. |
| 151 | PASS | Suite migra una base vacía. |
| 152 | PASS | Triggers migran desde cero. |
| 153 | PASS | `makemigrations --check` no detecta pendientes. |
| 154 | PASS | Ruff lint y format pasan. |
| 155 | PASS | Pyright pasa con 0 errores. |
| 156 | PASS | 143 pruebas logran 81.80% de cobertura. |
| 157 | PASS | ESLint pasa. |
| 158 | PASS | Prettier check pasa. |
| 159 | PASS | TypeScript estricto pasa. |
| 160 | PASS | 38 pruebas Vitest pasan. |
| 161 | PASS | Next production build pasa. |
| 162 | PASS | pip-audit y pnpm audit no hallan vulnerabilidades. |
| 163 | PASS | Regresión de autenticación pasa en suite total. |
| 164 | PASS | Regresión de organizations pasa en suite total. |
| 165 | PASS | Regresión de catalog pasa en suite total. |
| 166 | PASS | Regresión de courses pasa en suite total. |
| 167 | PASS | Regresión de content pasa en suite total. |
| 168 | PASS | 143 pruebas y E2E publishing pasan. |
| 169 | PASS | No se implementaron evaluaciones. |
| 170 | PASS | No se implementaron certificados. |
| 171 | PASS | Codex no ejecutó commit. |
| 172 | PASS | Codex no ejecutó push. |
| 173 | PASS | Codex no ejecutó reset, rebase, merge ni clean. |
| 174 | PASS | Remoto e historial fueron preservados. |
| 175 | PASS | HEAD inicial y final fueron registrados. |
| 176 | PASS | No había cambios heredados iniciales; todo el diff es de fase. |

## Evidencia de validación

| Comando | Resultado |
| --- | --- |
| `pnpm learning:check` | PASS: límites modulares y checks Django |
| `pnpm learning:migrations:sql` | PASS: SQL 0001/0002/0003 inspeccionado |
| `pnpm learning:schema` | PASS: OpenAPI sin warnings |
| `pnpm learning:client:check` | PASS: sin drift |
| `pnpm platform:client:check` | PASS: sin drift |
| `pnpm learning:test` | PASS: 17 pruebas |
| `pnpm api:test` | PASS: 143 pruebas, 81.80% |
| `pnpm api:typecheck` | PASS: 0 errores y 0 warnings |
| `pnpm api:test:migrations` | PASS: base vacía, triggers y cleanup |
| `pnpm web:lint` | PASS |
| `pnpm web:format:check` | PASS |
| `pnpm web:typecheck` | PASS |
| `pnpm web:test` | PASS: 38 pruebas |
| `pnpm web:build` | PASS |
| `pnpm publishing:e2e` | PASS: 1/1 Chromium |
| `pnpm learning:e2e` | PASS: 1/1 Chromium |
| `uv run pip-audit` | PASS: sin vulnerabilidades conocidas |
| `pnpm audit --prod` | PASS: sin vulnerabilidades conocidas |
| `pnpm infra:smoke` | PASS: PostgreSQL y Redis autenticados/persistentes |

## Fuentes y decisiones

- ADR 0022: release pinning, concurrencia, eventos y continuidad.
- `docs/architecture/LEARNING.md`: modelo, transacciones y 14 diagramas.
- `docs/research/OFFICIAL_SOURCES.md`: documentación oficial consultada el
  2026-07-30.
- `docs/project/STATUS.md`: estado final, riesgos y siguiente paso.
