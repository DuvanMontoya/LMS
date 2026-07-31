# Phase 14 acceptance

Fecha de cierre local: 2026-07-30. Evidencia principal: pruebas unitarias,
transaccionales, API, drift, seguridad, worker Linux real y
`pnpm assessments:advanced-e2e` en Chromium. `PASS` significa que el criterio
está implementado y cubierto por evidencia proporcional; no se usaron `FAIL`,
`BLOCKED` ni `DEFERRED` para cerrar esta fase.

|   # | Criterio                                          | Estado |
| --: | ------------------------------------------------- | :----: |
|   1 | `domain.assessments` conserva la propiedad        |  PASS  |
|   2 | No se creó una app innecesaria                    |  PASS  |
|   3 | SymPy estable está instalado                      |  PASS  |
|   4 | Celery estable está instalado                     |  PASS  |
|   5 | Compute Engine estable está instalado             |  PASS  |
|   6 | NumPy no está instalado                           |  PASS  |
|   7 | SciPy no está instalado                           |  PASS  |
|   8 | pandas no está instalado                          |  PASS  |
|   9 | ANTLR no está instalado                           |  PASS  |
|  10 | No se usa `eval`                                  |  PASS  |
|  11 | No se usa `parse_expr`                            |  PASS  |
|  12 | No se usa `parse_latex` en backend                |  PASS  |
|  13 | Existe schema MathJSON                            |  PASS  |
|  14 | Existe schema de scoring policy                   |  PASS  |
|  15 | Los tipos son generados                           |  PASS  |
|  16 | El drift check funciona                           |  PASS  |
|  17 | Existe scoring engine v2                          |  PASS  |
|  18 | Funcionan credit basis points                     |  PASS  |
|  19 | Se conserva Decimal                               |  PASS  |
|  20 | Multiple choice partial funciona                  |  PASS  |
|  21 | Ordering partial funciona                         |  PASS  |
|  22 | Matching partial funciona                         |  PASS  |
|  23 | Numeric banded funciona                           |  PASS  |
|  24 | El score nunca es negativo                        |  PASS  |
|  25 | El score no supera el máximo                      |  PASS  |
|  26 | Existe `mathematical_expression`                  |  PASS  |
|  27 | MathLive funciona                                 |  PASS  |
|  28 | Compute Engine produce MathJSON                   |  PASS  |
|  29 | Backend valida MathJSON                           |  PASS  |
|  30 | La allowlist de AST funciona                      |  PASS  |
|  31 | Los símbolos se restringen                        |  PASS  |
|  32 | Las funciones se restringen                       |  PASS  |
|  33 | Los límites funcionan                             |  PASS  |
|  34 | Se rechaza exponent tower                         |  PASS  |
|  35 | Funciona equivalencia estructural                 |  PASS  |
|  36 | Funciona equivalencia simbólica                   |  PASS  |
|  37 | El sampling sólo refuta                           |  PASS  |
|  38 | Inconclusive no se marca incorrecto               |  PASS  |
|  39 | Timeout no se marca incorrecto                    |  PASS  |
|  40 | SymPy no corre en el proceso HTTP                 |  PASS  |
|  41 | Celery usa Redis como broker                      |  PASS  |
|  42 | El broker usa DB separada                         |  PASS  |
|  43 | No existe result backend                          |  PASS  |
|  44 | Celery usa JSON                                   |  PASS  |
|  45 | Se rechaza pickle                                 |  PASS  |
|  46 | El worker corre en Linux                          |  PASS  |
|  47 | El worker corre como no root                      |  PASS  |
|  48 | El worker no publica puertos                      |  PASS  |
|  49 | El dispatch ocurre tras commit                    |  PASS  |
|  50 | Un rollback no envía tarea                        |  PASS  |
|  51 | Las tareas son idempotentes                       |  PASS  |
|  52 | Los jobs durables están en PostgreSQL             |  PASS  |
|  53 | Existe pool                                       |  PASS  |
|  54 | Se valida `selection_count`                       |  PASS  |
|  55 | Los candidatos son inmutables                     |  PASS  |
|  56 | No hay candidatos duplicados                      |  PASS  |
|  57 | La selección es sin reemplazo                     |  PASS  |
|  58 | El mismo seed produce la misma selección          |  PASS  |
|  59 | La selección queda persistida                     |  PASS  |
|  60 | El maximum score del pool es correcto             |  PASS  |
|  61 | Existe grading policy                             |  PASS  |
|  62 | El backfill original funciona                     |  PASS  |
|  63 | Una correction crea revision                      |  PASS  |
|  64 | Una correction exige reason                       |  PASS  |
|  65 | Una correction no cambia el public payload        |  PASS  |
|  66 | Grading revision es inmutable                     |  PASS  |
|  67 | Existe `AttemptGradeVersion`                      |  PASS  |
|  68 | Grade version es append-only                      |  PASS  |
|  69 | Item grade es append-only                         |  PASS  |
|  70 | Existe current grade                              |  PASS  |
|  71 | La data migration conserva grades                 |  PASS  |
|  72 | Initial grade crea version                        |  PASS  |
|  73 | Manual grade crea version                         |  PASS  |
|  74 | Regrade crea version                              |  PASS  |
|  75 | Los grades anteriores permanecen                  |  PASS  |
|  76 | Se preservan manual grades                        |  PASS  |
|  77 | Funciona `grading_pending`                        |  PASS  |
|  78 | Funciona async grade                              |  PASS  |
|  79 | Worker failure no crea nota incorrecta            |  PASS  |
|  80 | Existe `RegradeJob`                               |  PASS  |
|  81 | El job es durable                                 |  PASS  |
|  82 | El job es idempotente                             |  PASS  |
|  83 | Funcionan chunks                                  |  PASS  |
|  84 | Worker duplicado no duplica                       |  PASS  |
|  85 | Un fallo parcial no borra grades                  |  PASS  |
|  86 | Funciona retry failed                             |  PASS  |
|  87 | Los contadores son coherentes                     |  PASS  |
|  88 | Existe gradebook                                  |  PASS  |
|  89 | Gradebook pertenece a un release                  |  PASS  |
|  90 | Funcionan columnas                                |  PASS  |
|  91 | Los pesos usan basis points                       |  PASS  |
|  92 | La activación exige 10.000                        |  PASS  |
|  93 | Funciona `highest`                                |  PASS  |
|  94 | Funciona `latest`                                 |  PASS  |
|  95 | Entries derivan de grades                         |  PASS  |
|  96 | Funcionan summaries                               |  PASS  |
|  97 | Regrade actualiza gradebook                       |  PASS  |
|  98 | Learner sólo ve su gradebook                      |  PASS  |
|  99 | Gradebook no cambia `CourseProgress`              |  PASS  |
| 100 | Existe analytics snapshot                         |  PASS  |
| 101 | Existe item analytics                             |  PASS  |
| 102 | Existe option analytics                           |  PASS  |
| 103 | Facilidad usa crédito promedio                    |  PASS  |
| 104 | Discriminación usa score sin el ítem              |  PASS  |
| 105 | Se usa `corr` de PostgreSQL                       |  PASS  |
| 106 | Funcionan percentiles                             |  PASS  |
| 107 | Funciona sample suppression                       |  PASS  |
| 108 | Varianza cero produce `NULL`                      |  PASS  |
| 109 | Pools usan `presented_count`                      |  PASS  |
| 110 | Analytics refresh es asíncrono                    |  PASS  |
| 111 | Analytics snapshots son append-only               |  PASS  |
| 112 | Analytics no se expone a learner                  |  PASS  |
| 113 | Las APIs están versionadas                        |  PASS  |
| 114 | Los jobs usan HTTP 202                            |  PASS  |
| 115 | IDOR de scoring policy devuelve 404               |  PASS  |
| 116 | IDOR de job devuelve 404                          |  PASS  |
| 117 | IDOR de gradebook devuelve 404                    |  PASS  |
| 118 | IDOR de analytics devuelve 404                    |  PASS  |
| 119 | Mass assignment falla                             |  PASS  |
| 120 | Expected MathJSON no se filtra                    |  PASS  |
| 121 | Grading payload no se filtra                      |  PASS  |
| 122 | Task args no contienen respuestas                 |  PASS  |
| 123 | Logs no contienen claves                          |  PASS  |
| 124 | El editor matemático funciona                     |  PASS  |
| 125 | La respuesta matemática funciona                  |  PASS  |
| 126 | La UI de grading pending funciona                 |  PASS  |
| 127 | El pool composer funciona                         |  PASS  |
| 128 | La regrade console funciona                       |  PASS  |
| 129 | La UI de gradebook funciona                       |  PASS  |
| 130 | El learner gradebook funciona                     |  PASS  |
| 131 | La UI de analytics funciona                       |  PASS  |
| 132 | No se usa `localStorage`                          |  PASS  |
| 133 | No se usa JWT                                     |  PASS  |
| 134 | Los formularios tienen labels                     |  PASS  |
| 135 | MathLive es accesible                             |  PASS  |
| 136 | Los pools son accesibles                          |  PASS  |
| 137 | La tabla de gradebook es accesible                |  PASS  |
| 138 | Analytics tiene equivalente textual               |  PASS  |
| 139 | axe pasa                                          |  PASS  |
| 140 | Teclado pasa                                      |  PASS  |
| 141 | Responsive pasa                                   |  PASS  |
| 142 | Demo es idempotente                               |  PASS  |
| 143 | Demo rechaza production                           |  PASS  |
| 144 | README explica el worker                          |  PASS  |
| 145 | Se usó un navegador real                          |  PASS  |
| 146 | La inspección visual está documentada             |  PASS  |
| 147 | E2E math pasa                                     |  PASS  |
| 148 | E2E inconclusive pasa                             |  PASS  |
| 149 | E2E partial credit pasa                           |  PASS  |
| 150 | E2E pool pasa                                     |  PASS  |
| 151 | E2E regrading pasa                                |  PASS  |
| 152 | E2E gradebook pasa                                |  PASS  |
| 153 | E2E analytics pasa                                |  PASS  |
| 154 | E2E concurrency pasa                              |  PASS  |
| 155 | E2E security pasa                                 |  PASS  |
| 156 | E2E cross-org pasa                                |  PASS  |
| 157 | Se probó el worker real                           |  PASS  |
| 158 | La base E2E se limpia                             |  PASS  |
| 159 | Redis E2E se limpia                               |  PASS  |
| 160 | El worker se detiene                              |  PASS  |
| 161 | Funciona la migración limpia                      |  PASS  |
| 162 | Los triggers migran desde cero                    |  PASS  |
| 163 | No hay migraciones pendientes                     |  PASS  |
| 164 | Ruff pasa                                         |  PASS  |
| 165 | Pyright pasa                                      |  PASS  |
| 166 | La cobertura cumple                               |  PASS  |
| 167 | ESLint pasa                                       |  PASS  |
| 168 | Prettier pasa                                     |  PASS  |
| 169 | TypeScript pasa                                   |  PASS  |
| 170 | Vitest pasa                                       |  PASS  |
| 171 | Next build pasa                                   |  PASS  |
| 172 | Las auditorías pasan                              |  PASS  |
| 173 | Auth no presenta regresiones                      |  PASS  |
| 174 | Organizations no presenta regresiones             |  PASS  |
| 175 | Catalog no presenta regresiones                   |  PASS  |
| 176 | Courses no presenta regresiones                   |  PASS  |
| 177 | Content no presenta regresiones                   |  PASS  |
| 178 | Publishing no presenta regresiones                |  PASS  |
| 179 | Learning no presenta regresiones                  |  PASS  |
| 180 | Assessments Prompt 13 no presenta regresiones     |  PASS  |
| 181 | No se ejecuta código del estudiante               |  PASS  |
| 182 | No se implementó QTI                              |  PASS  |
| 183 | No se implementó IRT                              |  PASS  |
| 184 | Codex no ejecutó commit                           |  PASS  |
| 185 | Codex no ejecutó push                             |  PASS  |
| 186 | Codex no ejecutó reset, rebase, merge o clean     |  PASS  |
| 187 | Se preservaron remoto e historial                 |  PASS  |
| 188 | Se registraron HEAD inicial y final               |  PASS  |
| 189 | Se preservaron o explicaron los cambios heredados |  PASS  |

Resultado: **189 PASS, 0 FAIL, 0 BLOCKED, 0 DEFERRED**.
