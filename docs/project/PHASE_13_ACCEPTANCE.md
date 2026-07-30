# Phase 13 — Matriz de aceptación

Fecha de cierre: 2026-07-30.

Clasificación basada en revisión de código y contratos, migración PostgreSQL
desde cero, 172 pruebas backend con cobertura, 43 pruebas frontend, build de
producción, auditorías, E2E Chromium aislado y recorrido manual integrado por
rol a escritorio y 390 px.

## 1–30 — Arquitectura, schemas, tipos y bancos

| # | Criterio | Estado |
|---:|---|---|
| 1 | assessments es propietaria del dominio | PASS |
| 2 | learning no importa assessments | PASS |
| 3 | no se instaló LMS externo | PASS |
| 4 | no se instaló SymPy | PASS |
| 5 | no se instaló Celery | PASS |
| 6 | capacidades assessments existen | PASS |
| 7 | matriz de roles está actualizada | PASS |
| 8 | learner no tiene capacidades administrativas | PASS |
| 9 | QTI se documenta como futuro | PASS |
| 10 | no se afirma conformidad QTI | PASS |
| 11 | schemas Draft 2020-12 existen | PASS |
| 12 | no tienen refs remotos | PASS |
| 13 | tipos TS son generados | PASS |
| 14 | drift funciona | PASS |
| 15 | public/grading están separados | PASS |
| 16 | grading no aparece al learner | PASS |
| 17 | ocho tipos existen | PASS |
| 18 | single choice funciona | PASS |
| 19 | multiple choice funciona | PASS |
| 20 | true/false funciona | PASS |
| 21 | numeric usa Decimal | PASS |
| 22 | numeric no usa float | PASS |
| 23 | short text normaliza | PASS |
| 24 | long text queda manual | PASS |
| 25 | ordering funciona | PASS |
| 26 | matching funciona | PASS |
| 27 | no existe partial credit | PASS |
| 28 | QuestionBank usa UUID | PASS |
| 29 | bank slug es único | PASS |
| 30 | bank no se elimina | PASS |

## 31–60 — Preguntas y evaluaciones versionadas

| # | Criterio | Estado |
|---:|---|---|
| 31 | Question usa UUID | PASS |
| 32 | code es estable | PASS |
| 33 | QuestionRevision usa UUID | PASS |
| 34 | una revisión abierta | PASS |
| 35 | expected version funciona | PASS |
| 36 | workflow funciona | PASS |
| 37 | QuestionVersion usa UUID | PASS |
| 38 | QuestionVersion es inmutable | PASS |
| 39 | triggers funcionan | PASS |
| 40 | public digest existe | PASS |
| 41 | definition digest existe | PASS |
| 42 | new draft funciona | PASS |
| 43 | BankVersion existe | PASS |
| 44 | BankVersion es inmutable | PASS |
| 45 | digest no-op funciona | PASS |
| 46 | Assessment usa UUID | PASS |
| 47 | AssessmentRevision usa UUID | PASS |
| 48 | una revisión abierta | PASS |
| 49 | settings validan | PASS |
| 50 | secciones ordenadas | PASS |
| 51 | ítems ordenados | PASS |
| 52 | constraints son diferibles | PASS |
| 53 | puntos usan Decimal | PASS |
| 54 | QuestionVersion queda fijada | PASS |
| 55 | objectives funcionan | PASS |
| 56 | readiness funciona | PASS |
| 57 | AssessmentVersion existe | PASS |
| 58 | AssessmentVersion es inmutable | PASS |
| 59 | public snapshot no tiene claves | PASS |
| 60 | grading snapshot no se expone | PASS |

## 61–90 — Delivery, intentos y calificación

| # | Criterio | Estado |
|---:|---|---|
| 61 | maximum score es exacto | PASS |
| 62 | Delivery usa UUID | PASS |
| 63 | Delivery fija AssessmentVersion | PASS |
| 64 | ventana funciona | PASS |
| 65 | retiro funciona | PASS |
| 66 | DeliveryAssignment existe | PASS |
| 67 | assignment cross-release falla | PASS |
| 68 | lote es atómico | PASS |
| 69 | Attempt usa UUID | PASS |
| 70 | attempt number es único | PASS |
| 71 | máximo una in_progress | PASS |
| 72 | max attempts funciona | PASS |
| 73 | start es idempotente | PASS |
| 74 | concurrent start es seguro | PASS |
| 75 | seed es segura | PASS |
| 76 | orden final se almacena | PASS |
| 77 | AttemptItem es inmutable | PASS |
| 78 | Response pertenece a item | PASS |
| 79 | save usa expected version | PASS |
| 80 | conflict devuelve 409 | PASS |
| 81 | submit es definitivo | PASS |
| 82 | segundo submit no duplica | PASS |
| 83 | absent response obtiene 0 | PASS |
| 84 | auto grading funciona | PASS |
| 85 | long text queda pending | PASS |
| 86 | ManualGradeDecision es append-only | PASS |
| 87 | corrección manual conserva historial | PASS |
| 88 | final score recalcula | PASS |
| 89 | basis points funcionan | PASS |
| 90 | passed funciona | PASS |

## 91–120 — Feedback, seguridad y frontend learner

| # | Criterio | Estado |
|---:|---|---|
| 91 | feedback none funciona | PASS |
| 92 | score only funciona | PASS |
| 93 | full feedback funciona | PASS |
| 94 | no feedback antes de grading | PASS |
| 95 | timer funciona | PASS |
| 96 | saves expirados fallan | PASS |
| 97 | submit expirado funciona | PASS |
| 98 | AttemptEvent es append-only | PASS |
| 99 | API está versionada | PASS |
| 100 | no existe DELETE físico | PASS |
| 101 | IDOR bank devuelve 404 | PASS |
| 102 | IDOR question devuelve 404 | PASS |
| 103 | IDOR assessment devuelve 404 | PASS |
| 104 | IDOR delivery devuelve 404 | PASS |
| 105 | IDOR attempt devuelve 404 | PASS |
| 106 | IDOR result devuelve 404 | PASS |
| 107 | mass assignment falla | PASS |
| 108 | learner no ve claves | PASS |
| 109 | HTML SSR no contiene claves | PASS |
| 110 | logs no contienen claves | PASS |
| 111 | frontend bank funciona | PASS |
| 112 | question editor funciona | PASS |
| 113 | composer funciona | PASS |
| 114 | delivery funciona | PASS |
| 115 | learner list funciona | PASS |
| 116 | attempt UI funciona | PASS |
| 117 | navigator funciona | PASS |
| 118 | timer es accesible | PASS |
| 119 | response controls son accesibles | PASS |
| 120 | submit confirmation funciona | PASS |

## 121–150 — Resultados, accesibilidad y E2E

| # | Criterio | Estado |
|---:|---|---|
| 121 | result funciona | PASS |
| 122 | pending manual funciona | PASS |
| 123 | grading UI funciona | PASS |
| 124 | manual grade funciona | PASS |
| 125 | no usa localStorage | PASS |
| 126 | no usa JWT | PASS |
| 127 | forms tienen labels | PASS |
| 128 | fieldsets funcionan | PASS |
| 129 | ordering funciona por teclado | PASS |
| 130 | matching funciona por teclado | PASS |
| 131 | foco funciona | PASS |
| 132 | axe pasa | PASS |
| 133 | responsive pasa | PASS |
| 134 | demo es idempotente | PASS |
| 135 | demo rechaza production | PASS |
| 136 | README explica evaluaciones | PASS |
| 137 | navegador real fue usado | PASS |
| 138 | inspección visual fue documentada | PASS |
| 139 | E2E bank pasa | PASS |
| 140 | E2E questions pasa | PASS |
| 141 | E2E assessment pasa | PASS |
| 142 | E2E delivery pasa | PASS |
| 143 | E2E automatic attempt pasa | PASS |
| 144 | E2E manual grading pasa | PASS |
| 145 | E2E max attempts pasa | PASS |
| 146 | E2E conflict pasa | PASS |
| 147 | E2E timer pasa | PASS |
| 148 | E2E leakage pasa | PASS |
| 149 | E2E cross-org pasa | PASS |
| 150 | base E2E se limpia | PASS |

## 151–180 — Infraestructura, regresión y Git

| # | Criterio | Estado |
|---:|---|---|
| 151 | Redis E2E se limpia | PASS |
| 152 | correo E2E se limpia | PASS |
| 153 | migración limpia funciona | PASS |
| 154 | triggers migran desde cero | PASS |
| 155 | no hay migraciones pendientes | PASS |
| 156 | Ruff pasa | PASS |
| 157 | Pyright pasa | PASS |
| 158 | cobertura cumple | PASS |
| 159 | ESLint pasa | PASS |
| 160 | Prettier pasa | PASS |
| 161 | TypeScript pasa | PASS |
| 162 | Vitest pasa | PASS |
| 163 | Next build pasa | PASS |
| 164 | auditorías pasan | PASS |
| 165 | auth no presenta regresiones | PASS |
| 166 | organizations no presenta regresiones | PASS |
| 167 | catalog no presenta regresiones | PASS |
| 168 | courses no presenta regresiones | PASS |
| 169 | content no presenta regresiones | PASS |
| 170 | publishing no presenta regresiones | PASS |
| 171 | learning no presenta regresiones | PASS |
| 172 | no se implementó symbolic grading | PASS |
| 173 | no se implementó code execution | PASS |
| 174 | no se implementó QTI import/export | PASS |
| 175 | Codex no ejecutó commit | PASS |
| 176 | Codex no ejecutó push | PASS |
| 177 | Codex no ejecutó reset, rebase, merge o clean | PASS |
| 178 | remoto e historial fueron preservados | PASS |
| 179 | HEAD inicial y final fueron registrados | PASS |
| 180 | cambios heredados fueron preservados o explicados | PASS |

## Resultado

**180 PASS · 0 FAIL · 0 BLOCKED · 0 DEFERRED.**

