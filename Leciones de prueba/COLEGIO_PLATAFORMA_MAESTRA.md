# PLATAFORMA ACADÉMICA Y ADMINISTRATIVA — COLEGIO
## DOCUMENTO MAESTRO v1.0

> **Propósito dual:**
> 1. Especificación de producto completa (PRD) para planificación y revisión humana.
> 2. Instrucciones de agente de código (AGENTS.md) para implementación automatizada.
>
> **Stack:** NestJS + Prisma + PostgreSQL · Next.js + Tailwind + shadcn/ui · Flutter
> **Modalidad:** Multi-tenant SaaS — cada colegio es un tenant independiente con aislamiento total de datos por `colegioId`.

---

## ÍNDICE

- [A. Contexto y Fundamentos](#a-contexto-y-fundamentos)
- [B. Arquitectura del Sistema](#b-arquitectura-del-sistema)
- [C. Roles y Permisos](#c-roles-y-permisos)
- [D. Modelo de Datos — Schema Prisma](#d-modelo-de-datos--schema-prisma)
- [E. Módulos del Sistema](#e-módulos-del-sistema)
- [F. API Endpoints NestJS](#f-api-endpoints-nestjs)
- [G. Pantallas y Vistas](#g-pantallas-y-vistas)
- [H. Instrucciones para Agente de Código](#h-instrucciones-para-agente-de-código)

---

## A. CONTEXTO Y FUNDAMENTOS

### A1. Propósito del Sistema

Plataforma SaaS que digitaliza por completo la gestión académica y administrativa de un colegio colombiano de preescolar a media vocacional. Reemplaza procesos en papel, Excel y sistemas desconectados. Cada institución educativa que se suscribe obtiene su propio espacio de trabajo aislado (tenant).

**Cobertura:**
- Preescolar (Pre-jardín, Jardín, Transición)
- Educación Básica Primaria (Grados 1° – 5°)
- Educación Básica Secundaria (Grados 6° – 9°)
- Educación Media (Grados 10° – 11°, académica o técnica)

**Usuarios atendidos:** Rector, Coordinadores, Docentes, Secretaría, Financiero, Psicoorientador, Estudiantes, Padres/Acudientes.

---

### A2. Marco Legal Colombiano

Todo el sistema debe reflejar y hacer cumplir la siguiente normativa vigente. El agente de código **nunca** inventa reglas de negocio que contradigan estas leyes.

| Norma | Descripción | Impacto en el sistema |
|-------|-------------|----------------------|
| **Ley 115 de 1994** | Ley General de Educación | Estructura del currículo, áreas obligatorias, jornada, grados |
| **Decreto 1860 de 1994** | Reglamenta la Ley 115 | PEI, manual de convivencia, gobierno escolar |
| **Decreto 1290 de 2009** | Sistema Institucional de Evaluación del Estudiante (SIEE) | Todo el módulo de calificaciones y promoción |
| **Decreto 1075 de 2015** | Decreto Único Reglamentario del Sector Educación | Operación general del establecimiento |
| **Ley 1620 de 2013** | Sistema Nacional de Convivencia Escolar | Módulo de convivencia y disciplina |
| **Decreto 1965 de 2013** | Reglamenta la Ley 1620 | Protocolo de atención a faltas, comité de convivencia |
| **Resolución 2343 de 1996** | Indicadores de logro curriculares | Estructura de logros e indicadores |
| **Ley 1581 de 2012** | Habeas Data / Protección de datos personales | Consentimiento de padres, manejo de datos de menores |
| **Decreto 1421 de 2017** | Educación inclusiva para estudiantes con discapacidad | Campos de discapacidad, ajustes razonables |

---

### A3. Estructura del Sistema Educativo Colombiano

```
INSTITUCIÓN EDUCATIVA
├── PREESCOLAR
│   ├── Pre-jardín (3 años)
│   ├── Jardín (4 años)
│   └── Transición / Grado 0 (5 años)
│
├── EDUCACIÓN BÁSICA PRIMARIA
│   ├── Grado 1°
│   ├── Grado 2°
│   ├── Grado 3°
│   ├── Grado 4°
│   └── Grado 5°
│
├── EDUCACIÓN BÁSICA SECUNDARIA
│   ├── Grado 6°
│   ├── Grado 7°
│   ├── Grado 8°
│   └── Grado 9°
│
└── EDUCACIÓN MEDIA
    ├── Grado 10° (Académica o Técnica)
    └── Grado 11° (Académica o Técnica)
```

**Calendarios escolares:** A (Feb–Nov) o B (Sep–Jun). El sistema soporta ambos.

**Jornadas:** Mañana, Tarde, Noche, Completa, Única. Un colegio puede tener varias.

---

### A4. Áreas Obligatorias (Ley 115, Art. 23)

El sistema precarga estas áreas al crear un colegio. No son eliminables, solo configurables.

| # | Área | Aplica a |
|---|------|----------|
| 1 | Ciencias Naturales y Educación Ambiental | Básica y Media |
| 2 | Ciencias Sociales, Historia, Geografía, Constitución Política y Democracia | Básica y Media |
| 3 | Educación Artística y Cultural | Básica y Media |
| 4 | Educación Ética y en Valores Humanos | Básica y Media |
| 5 | Educación Física, Recreación y Deportes | Básica y Media |
| 6 | Educación Religiosa | Básica y Media (con posibilidad de exención) |
| 7 | Humanidades — Lengua Castellana e Idiomas Extranjeros | Básica y Media |
| 8 | Matemáticas | Básica y Media |
| 9 | Tecnología e Informática | Básica y Media |
| 10 | Filosofía | Solo Media (10° y 11°) |

---

### A5. Sistema de Evaluación — Decreto 1290 de 2009

Este decreto es el corazón del módulo de calificaciones. Se resume así:

**A5.1 Escala de Valoración Nacional (equivalencias)**

| Desempeño | Descripción |
|-----------|-------------|
| **Superior (S)** | Supera los desempeños esperados |
| **Alto (A)** | Alcanza los desempeños esperados |
| **Básico (B)** | Supera los desempeños mínimos esperados |
| **Bajo (Bj)** | No supera los desempeños mínimos esperados |

> **CRÍTICO:** Cada institución define su propia escala numérica que equivale a estos niveles. El sistema almacena la escala institucional (p.ej. Superior: 4.6–5.0, Alto: 4.0–4.5, Básico: 3.0–3.9, Bajo: 1.0–2.9) pero también debe poder manejar escala de 1–10 o porcentual.

**A5.2 Períodos Académicos**
- Típicamente 4 períodos por año académico.
- Cada período tiene un porcentaje en la nota final anual (por defecto 25% cada uno, configurable).
- Nota definitiva anual = suma ponderada de los 4 períodos.

**A5.3 Criterios de Evaluación por Período**
Cada institución define sus propios criterios y pesos. Ejemplo típico:

| Criterio | Descripción | Peso típico |
|----------|-------------|-------------|
| Ser | Actitudinal, valores, convivencia | 20% |
| Saber | Cognitivo, conceptual, conocimiento | 40% |
| Hacer | Procedimental, habilidades, práctica | 40% |

**A5.4 Logros e Indicadores de Logro**
- Por cada asignatura, grado y período se definen **logros**.
- Cada logro tiene **indicadores de logro** medibles y observables.
- El docente evalúa los indicadores para determinar la nota.

**A5.5 Proceso de Nivelación (durante el año)**
- Si un estudiante obtiene Desempeño Bajo en un período, debe recibir actividades de nivelación.
- La nivelación se registra y puede reemplazar parcialmente la nota del período (configurable).

**A5.6 Proceso de Habilitación (fin de año)**
- Si un estudiante termina con Desempeño Bajo en una o más áreas, puede habilitarlas.
- La habilitación es una prueba o actividad extraordinaria al final del año.
- Nota de habilitación reemplaza o promedia con la nota anual (configurable por SIEE).
- Política de habilitaciones: número máximo de áreas habilitables (configurable).

**A5.7 Promoción y Reprobación**
- La institución define los criterios de promoción en el SIEE.
- Ejemplo típico: reprueba si queda con Bajo en más de 2 áreas después de habilitaciones.
- Preescolar: la reprobación es excepcional y requiere concepto de psicoorientador y autorización de la Secretaría de Educación.
- La Comisión de Evaluación y Promoción toma la decisión final.

**A5.8 Promoción Anticipada**
- Un estudiante sobresaliente puede ser promovido al grado siguiente antes de terminar el año.
- Requiere concepto favorable del Consejo Académico.
- Solo aplica en el primer período y debe formalizarse antes del 30 de junio.

**A5.9 Comisión de Evaluación y Promoción**
- Se reúne al final de cada período y al final del año.
- Integrada por: rector o coordinador (preside), docentes del grado, psicoorientador.
- Toma decisiones sobre: estudiantes con bajo rendimiento, habilitaciones, reprobación, promoción anticipada.
- Genera un acta oficial por cada reunión.

---

## B. ARQUITECTURA DEL SISTEMA

### B1. Stack Tecnológico

```
backend/
  ├── NestJS (framework)
  ├── Prisma ORM (acceso a datos)
  ├── PostgreSQL (base de datos)
  ├── JWT (autenticación — accessToken + refreshToken)
  ├── bcrypt (hash de contraseñas)
  ├── class-validator + class-transformer (validación DTOs)
  ├── @nestjs/swagger (documentación API)
  └── multer / S3 (manejo de archivos)

frontend-web/
  ├── Next.js 14+ (App Router)
  ├── Tailwind CSS
  ├── shadcn/ui (componentes)
  ├── React Query / TanStack Query (estado servidor)
  ├── Zustand (estado cliente)
  ├── React Hook Form + Zod (formularios y validación)
  └── Recharts (gráficas y analytics)

mobile/
  ├── Flutter
  ├── Material 3 con ThemeData profundo
  ├── Riverpod (gestión de estado)
  ├── Dio (cliente HTTP)
  └── go_router (navegación)
```

### B2. Convenciones Multi-Tenant

- **Aislamiento:** Todo modelo de datos que pertenezca a un colegio lleva `colegioId: String` con FK a `Colegio`.
- **Guards:** Guard `TenantGuard` en NestJS verifica que el recurso solicitado pertenece al `colegioId` del JWT.
- **Queries:** Todos los `findMany`, `findFirst`, `findUnique` incluyen `where: { colegioId }` sin excepción.
- **Índices:** Índices compuestos `[colegioId, campo]` en tablas de alta consulta.

### B3. Módulos NestJS

```
src/
├── app.module.ts
├── auth/                        # Login, JWT, refresh
├── tenant/                      # Gestión de colegios (superadmin)
├── users/                       # CRUD usuarios + personas
├── roles/                       # Asignación de roles por colegio
├── academic-structure/          # Grados, grupos, áreas, asignaturas
├── academic-year/               # Años académicos y períodos
├── enrollment/                  # Inscripciones y matrículas
├── staff/                       # Docentes, directivos, administrativos
├── students/                    # Perfil del estudiante
├── parents/                     # Acudientes y relaciones
├── siee/                        # Configuración SIEE, escala, criterios
├── grades/                      # Calificaciones por período
├── annual-grades/               # Notas anuales y promoción
├── achievements/                # Logros e indicadores
├── attendance/                  # Registro de asistencia
├── schedule/                    # Horarios y franjas
├── coexistence/                 # Convivencia, anotaciones, comité
├── communications/              # Circulares y notificaciones
├── secretary/                   # Documentos, certificados, constancias
├── financial/                   # Pagos, pensiones, conceptos de cobro
├── counseling/                  # Psicoorientación
├── reports/                     # Boletines e informes PDF
├── analytics/                   # Reportes y estadísticas
└── shared/                      # Guards, pipes, decorators, utils
```

### B4. Estructura Frontend Next.js

```
app/
├── (auth)/
│   ├── login/
│   └── forgot-password/
├── (dashboard)/
│   ├── layout.tsx               # Shell con sidebar y header
│   ├── page.tsx                 # Dashboard inicio (por rol)
│   ├── institucion/
│   │   ├── configuracion/
│   │   ├── siee/
│   │   ├── calendario/
│   │   └── gobierno-escolar/
│   ├── estructura/
│   │   ├── grados/
│   │   ├── grupos/
│   │   ├── areas/
│   │   └── asignaturas/
│   ├── personal/
│   │   ├── docentes/
│   │   └── administrativos/
│   ├── estudiantes/
│   │   ├── page.tsx             # Listado
│   │   └── [id]/
│   │       ├── page.tsx         # Perfil general
│   │       ├── calificaciones/
│   │       ├── asistencia/
│   │       ├── convivencia/
│   │       └── documentos/
│   ├── inscripciones/
│   ├── matriculas/
│   ├── horarios/
│   ├── calificaciones/
│   │   ├── registro/            # Docente ingresa notas
│   │   └── consulta/
│   ├── asistencia/
│   ├── convivencia/
│   ├── boletines/
│   ├── secretaria/
│   ├── financiero/
│   ├── orientacion/
│   ├── comunicaciones/
│   └── reportes/
components/
├── ui/                          # shadcn/ui base
├── layout/                      # Sidebar, Header, Breadcrumb
├── students/                    # StudentCard, StudentSearch
├── grades/                      # GradeTable, GradeInput, PerformanceBadge
├── reports/                     # BoletinoViewer, GradeChart
└── shared/                      # DataTable, FormModal, StatusBadge
```

### B5. Estructura Flutter (Mobile)

```
lib/
├── main.dart
├── core/
│   ├── theme/                   # Material 3, colores, tipografía
│   ├── router/                  # go_router
│   ├── network/                 # Dio, interceptors JWT
│   └── constants/
├── features/
│   ├── auth/                    # Login
│   ├── dashboard/               # Home por rol
│   ├── attendance/              # Tomar/ver asistencia
│   ├── grades/                  # Ver/ingresar notas
│   ├── schedule/                # Horario de clases
│   ├── communications/          # Circulares
│   ├── coexistence/             # Anotaciones
│   └── reports/                 # Boletín digital
└── shared/
    ├── widgets/
    └── models/
```

---

## C. ROLES Y PERMISOS

### C1. Jerarquía de Roles

```
SUPERADMIN_PLATAFORMA              ← Solo Anthropic/equipo técnico
└── RECTOR                         ← Máxima autoridad del colegio
    ├── COORDINADOR_ACADEMICO      ← Gestión académica y curricular
    ├── COORDINADOR_CONVIVENCIA    ← Disciplina y manual de convivencia
    ├── SECRETARIA                 ← Documentos, matrícula, certificados
    ├── FINANCIERO                 ← Cobros, pagos, paz y salvo
    ├── PSICORENTADOR              ← Orientación y bienestar estudiantil
    ├── JEFE_AREA                  ← Coordinación de un área curricular
    ├── DOCENTE                    ← Enseñanza, evaluación, asistencia
    │   └── DIRECTOR_GRUPO        ← Rol adicional: gestiona un grupo específico
    ├── ESTUDIANTE                 ← Acceso a su información académica
    └── PADRE_ACUDIENTE            ← Acceso a información del acudido
```

> Un mismo usuario puede tener múltiples roles (p.ej. un docente puede ser también jefe de área y director de grupo).

---

### C2. Descripción Detallada por Rol

#### C2.1 SUPERADMIN_PLATAFORMA

**Quién es:** Equipo técnico de la empresa que opera la plataforma SaaS.

**Puede:**
- Crear, editar, suspender y eliminar colegios (tenants).
- Ver estadísticas globales de uso.
- Impersonar cualquier usuario para soporte.
- Gestionar planes y facturación.
- Ver logs de errores y auditoría global.

**No puede:**
- Acceder a datos académicos específicos de estudiantes sin autorización del rector.

---

#### C2.2 RECTOR

**Quién es:** Máxima autoridad pedagógica y administrativa de la institución. Firma actos administrativos.

**Puede:**
- Configurar todos los parámetros institucionales (nombre, DANE, NIT, logo, jornadas, calendarios).
- Definir y modificar el SIEE (Sistema Institucional de Evaluación del Estudiante).
- Crear, editar y eliminar usuarios de todos los roles dentro del colegio.
- Ver y aprobar inscripciones de estudiantes.
- Firmar digitalmente matrículas y actas.
- Ver calificaciones, asistencia y convivencia de todos los estudiantes.
- Generar todos los reportes e informes.
- Ver y aprobar el estado financiero.
- Presidir o delegar la Comisión de Evaluación y Promoción.
- Aprobar promociones anticipadas.
- Emitir circulares a toda la comunidad educativa.
- Acceder al módulo de orientación escolar.
- Configurar la estructura académica completa (grados, grupos, áreas, asignaturas).
- Ver el tablero de analytics institucional.

**Vista principal (Dashboard):** KPIs institucionales: matrícula total, % de asistencia, promedio académico por grado, alertas de estudiantes en riesgo, estado financiero.

---

#### C2.3 COORDINADOR_ACADEMICO

**Quién es:** Responsable del proceso pedagógico, curricular y de evaluación.

**Puede:**
- Gestionar la estructura académica (grados, grupos, áreas, asignaturas).
- Asignar docentes a grupos y asignaturas.
- Crear y modificar horarios.
- Configurar logros e indicadores de logro por asignatura, grado y período.
- Ver calificaciones de todos los estudiantes.
- Generar reportes académicos por grado, grupo, asignatura.
- Gestionar períodos académicos (apertura, cierre).
- Coordinar las Comisiones de Evaluación y Promoción (convocar, levantar actas).
- Aprobar o rechazar solicitudes de nivelación.
- Monitorear asistencia de docentes y estudiantes.
- Ver y exportar el Registro de Valoración (libro de calificaciones).
- Gestionar procesos de promoción anticipada (iniciar solicitud).
- Emitir circulares a docentes y estudiantes.
- Acceder a perfil académico de cualquier estudiante.

**No puede:**
- Configurar el SIEE (solo rector).
- Ver información financiera detallada.
- Eliminar usuarios.

**Vista principal:** Estado académico por período activo: grupos sin calificaciones cerradas, docentes con pendientes, estudiantes con bajo rendimiento.

---

#### C2.4 COORDINADOR_CONVIVENCIA

**Quién es:** Responsable de la disciplina, el manual de convivencia y el comité de convivencia escolar.

**Puede:**
- Registrar anotaciones de convivencia (positivas, negativas, informativas).
- Clasificar faltas según el manual de convivencia (Leve, Grave, Gravísima).
- Activar protocolos de atención según la Ley 1620 (Ley de Convivencia).
- Registrar compromisos de convivencia y su seguimiento.
- Citar acudientes para procesos disciplinarios.
- Gestionar el Comité de Convivencia Escolar (actas, decisiones).
- Ver historial de convivencia de cualquier estudiante.
- Generar informes de convivencia por grupo, grado, período.
- Emitir circulares relacionadas con convivencia.
- Notificar a padres/acudientes sobre situaciones disciplinarias.

**No puede:**
- Ver calificaciones (salvo el historial general de desempeño).
- Acceder a información financiera.

**Vista principal:** Alertas de convivencia activas, protocolos pendientes de cierre, estudiantes con múltiples anotaciones.

---

#### C2.5 SECRETARIA (SECRETARIO/A ACADÉMICO/A)

**Quién es:** Responsable de los procesos administrativos de matrículas, documentos y certificados.

**Puede:**
- Recibir y gestionar inscripciones de nuevos estudiantes.
- Realizar matrículas nuevas y renovaciones.
- Retirar estudiantes (transferencias, deserción).
- Gestionar el archivo de documentos de cada estudiante (fotocopia de documento, registro civil, carnet de vacunas, boletines del año anterior, etc.).
- Emitir constancias de estudio.
- Emitir certificados de calificaciones.
- Emitir paz y salvos académicos.
- Emitir diplomas de bachillerato (preparar el documento para firma del rector).
- Llevar el libro de matrícula digital.
- Gestionar traslados entre grupos dentro del colegio.
- Actualizar datos del estudiante y sus acudientes.
- Ver calendario de fechas importantes (inicio de clases, entrega de boletines, etc.).
- Ver estado de pagos de cada estudiante (solo lectura del módulo financiero).

**No puede:**
- Modificar calificaciones.
- Registrar asistencia.
- Acceder a anotaciones de convivencia confidenciales.

**Vista principal:** Solicitudes de documentos pendientes, procesos de matrícula abiertos, lista de estudiantes sin documentos completos.

---

#### C2.6 FINANCIERO (TESORERO/A)

**Quién es:** Responsable de los cobros, pagos y estado financiero del colegio.

**Puede:**
- Crear y gestionar conceptos de cobro (matrícula, pensión, kit escolar, etc.).
- Registrar pagos recibidos (efectivo, transferencia, datafono).
- Ver el estado de cuenta de cada estudiante.
- Generar recibos de pago.
- Gestionar exoneraciones o descuentos.
- Generar listados de cartera (deudores).
- Generar paz y salvos financieros.
- Ver reportes financieros (recaudo por período, proyección de ingresos).
- Exportar informes en Excel/PDF.
- Notificar a acudientes sobre pagos pendientes.

**No puede:**
- Ver calificaciones detalladas.
- Modificar datos académicos.
- Acceder a convivencia.

**Vista principal:** Resumen financiero del mes, lista de morosos, recaudos del día.

---

#### C2.7 PSICOORIENTADOR/A

**Quién es:** Profesional en orientación escolar, bienestar estudiantil y atención psicosocial.

**Puede:**
- Registrar citas de orientación con estudiantes.
- Llevar historiales de orientación (privados, con control de acceso estricto).
- Ver calificaciones y asistencia para identificar estudiantes en riesgo.
- Ver anotaciones de convivencia para correlacionar situaciones.
- Generar informes de orientación (con control de confidencialidad).
- Participar en la Comisión de Evaluación y Promoción.
- Registrar remisiones a profesionales externos.
- Comunicarse con acudientes en el contexto de sus casos.
- Emitir conceptos para procesos de promoción anticipada o reprobación excepcional en preescolar.

**No puede:**
- Ver información financiera.
- Modificar calificaciones.
- Acceder a los historiales de orientación de otros psicoorientadores.

**Vista principal:** Estudiantes con alertas activas (bajo rendimiento + ausencias + anotaciones), citas programadas del día.

---

#### C2.8 JEFE_AREA

**Quién es:** Docente con rol adicional de coordinación de un área curricular específica.

**Puede (en su área):**
- Ver calificaciones de todos los estudiantes en las asignaturas de su área.
- Gestionar la malla curricular del área (proponer logros, indicadores, ajustes).
- Ver informes de desempeño del área por grado y grupo.
- Convocar reuniones de docentes del área.
- Ver asignación de docentes de su área.
- Generar informes del área para entregarlos al coordinador académico.

**Además tiene todos los permisos de DOCENTE** para sus asignaturas propias.

---

#### C2.9 DOCENTE

**Quién es:** Profesional que dicta clases, evalúa y registra asistencia.

**Puede (solo en sus grupos y asignaturas asignadas):**
- Ver el listado de estudiantes de sus grupos.
- Registrar asistencia (por clase o diaria).
- Ingresar calificaciones por período (Ser, Saber, Hacer) para sus asignaturas.
- Ver el historial de calificaciones de sus estudiantes en su asignatura.
- Registrar actividades de nivelación.
- Registrar anotaciones de convivencia (positivas y negativas leves).
- Ver el horario de sus clases.
- Ver los logros e indicadores de su asignatura.
- Comunicarse con acudientes a través del módulo de comunicaciones.
- Ver el boletín de sus estudiantes en las asignaturas que dicta.
- Participar en la Comisión de Evaluación y Promoción de sus grados.
- Recibir y responder circulares institucionales.
- Ver reportes básicos de su asignatura (promedio, distribución de desempeño).

**No puede:**
- Ver calificaciones de asignaturas que no dicta.
- Modificar calificaciones de otros docentes.
- Acceder a información financiera.
- Crear o eliminar usuarios.
- Ver historiales de orientación.

**Vista principal (App Flutter):** Mis clases de hoy, lista de asistencia pendiente, calificaciones sin cerrar del período activo.

---

#### C2.10 DIRECTOR_GRUPO (Rol adicional sobre DOCENTE)

**Quién es:** Docente designado como responsable de un grupo específico (p.ej. director de 7°A).

**Puede (adicionalmente):**
- Ver el perfil completo de todos los estudiantes de su grupo (datos personales, documentos, acudientes).
- Ver calificaciones de su grupo en TODAS las asignaturas (no solo las suyas).
- Ver asistencia de su grupo en todas las clases.
- Ver anotaciones de convivencia de todos sus estudiantes.
- Emitir observaciones generales del grupo en el boletín.
- Convocar reuniones de padres de familia de su grupo.
- Generar el boletín de su grupo.
- Notificar individualmente a acudientes de su grupo.
- Registrar la asistencia diaria global del grupo.

---

#### C2.11 ESTUDIANTE

**Quién es:** Alumno matriculado.

**Puede ver (solo su propia información):**
- Sus calificaciones por período y año.
- Su horario de clases.
- Su asistencia por asignatura.
- Sus anotaciones de convivencia (las no confidenciales).
- Las circulares y comunicaciones publicadas.
- Su boletín digital.
- Sus logros e indicadores por asignatura.
- El estado de sus documentos en secretaría.

**No puede:**
- Ver calificaciones de otros estudiantes.
- Modificar ningún dato.
- Acceder a información financiera.

**Acceso principal:** App Flutter mobile.

---

#### C2.12 PADRE_ACUDIENTE

**Quién es:** Padre, madre o acudiente del estudiante.

**Puede ver (solo del/los estudiante(s) a su cargo):**
- Calificaciones por período y definitivas.
- Asistencia del estudiante.
- Boletines digitales.
- Anotaciones de convivencia del estudiante.
- Estado de pagos (pensiones, matrículas).
- Circulares y comunicaciones.
- Horario del estudiante.
- Información de contacto de los docentes.

**Puede hacer:**
- Descargar boletines en PDF.
- Responder a notificaciones de convivencia (confirmación de recibido).
- Solicitar citas con el director de grupo o psicoorientador (si se habilita).

**No puede:**
- Modificar calificaciones ni asistencia.
- Ver información de otros estudiantes.
- Acceder a módulos administrativos.

**Acceso principal:** App Flutter mobile.

---

## D. MODELO DE DATOS — SCHEMA PRISMA

> **Reglas de implementación:**
> - Usar `cuid()` como ID por defecto.
> - Todo modelo con datos del colegio lleva `colegioId`.
> - Fechas en UTC siempre.
> - `prisma db push` para sincronizar schema (no `migrate dev`).
> - Nunca hardcodear IDs ni nombres de entidades en el código.

```prisma
// ============================================================
// ENUMERACIONES
// ============================================================

enum Naturaleza {
  OFICIAL
  PRIVADO
  CONCESION
}

enum CalendarioTipo {
  A
  B
}

enum Jornada {
  MANANA
  TARDE
  NOCHE
  COMPLETA
  UNICA
}

enum Nivel {
  PREESCOLAR
  PRIMARIA
  SECUNDARIA
  MEDIA
}

enum ModalidadMedia {
  ACADEMICA
  TECNICA
  ARTISTICA
}

enum TipoArea {
  OBLIGATORIA_FUNDAMENTAL
  OPTATIVA
}

enum Rol {
  SUPERADMIN_PLATAFORMA
  RECTOR
  COORDINADOR_ACADEMICO
  COORDINADOR_CONVIVENCIA
  SECRETARIA
  FINANCIERO
  PSICOORIENTADOR
  JEFE_AREA
  DOCENTE
  DIRECTOR_GRUPO
  ESTUDIANTE
  PADRE_ACUDIENTE
}

enum TipoDocumento {
  CC   // Cédula de ciudadanía
  TI   // Tarjeta de identidad
  CE   // Cédula de extranjería
  PP   // Pasaporte
  RC   // Registro civil
  NIP  // Número de identificación personal (preescolar sin TI)
  NUIP // Número único de identificación personal
}

enum Genero {
  MASCULINO
  FEMENINO
  NO_BINARIO
  PREFIERO_NO_DECIR
}

enum Parentesco {
  PADRE
  MADRE
  ABUELO
  ABUELA
  TIO
  TIA
  HERMANO
  HERMANA
  ACUDIENTE_LEGAL
  OTRO
}

enum TipoContrato {
  PLANTA
  PROVISIONAL
  HORA_CATEDRA
  OPS          // Orden de prestación de servicios
}

enum Escalafon {
  DECRETO_2277  // Escalafón antiguo
  DECRETO_1278  // Escalafón nuevo
}

enum EstadoInscripcion {
  PENDIENTE
  EN_REVISION
  ADMITIDO
  EN_LISTA_ESPERA
  RECHAZADO
  CONVERTIDA_EN_MATRICULA
}

enum TipoMatricula {
  NUEVA
  RENOVACION
  TRASLADO_ENTRANTE
}

enum EstadoMatricula {
  ACTIVA
  RETIRADA
  TRASLADADA
  FINALIZADA_PROMOVIDO
  FINALIZADA_REPROBADO
  CANCELADA
}

enum Desempeno {
  SUPERIOR
  ALTO
  BASICO
  BAJO
}

enum EstadoAsistencia {
  PRESENTE
  AUSENTE
  TARDANZA
  JUSTIFICADO
  EXCUSA_MEDICA
}

enum TipoFranja {
  CLASE
  DESCANSO
  ALMUERZO
  IZADO_BANDERA
  OTRO
}

enum DiaSemana {
  LUNES
  MARTES
  MIERCOLES
  JUEVES
  VIERNES
  SABADO
}

enum TipoAnotacion {
  POSITIVA
  NEGATIVA
  INFORMATIVA
  COMPROMISO
  CITACION
}

enum NivelFalta {
  LEVE
  GRAVE
  GRAVISIMA
}

enum EstadoProtocolo {
  ABIERTO
  EN_SEGUIMIENTO
  CERRADO
  ESCALADO
}

enum TipoComision {
  FIN_PERIODO
  FIN_ANIO
  EXTRAORDINARIA
  PROMOCION_ANTICIPADA
}

enum TipoDecision {
  APROBADO_PERIODO
  PROMOVIDO
  REPROBADO
  EN_HABILITACION
  PROMOVIDO_ANTICIPADAMENTE
  REQUIERE_SEGUIMIENTO
}

enum TipoDocumentoSolicitado {
  CONSTANCIA_ESTUDIO
  CERTIFICADO_CALIFICACIONES
  PAZ_Y_SALVO_ACADEMICO
  PAZ_Y_SALVO_FINANCIERO
  PAZ_Y_SALVO_GENERAL
  DIPLOMA_BACHILLERATO
  ACTA_GRADO
  HISTORIAL_ACADEMICO
  CERTIFICADO_CONDUCTA
  FICHA_CARACTERIZACION
}

enum EstadoSolicitud {
  PENDIENTE
  EN_PROCESO
  LISTO
  ENTREGADO
  RECHAZADO
}

enum TipoConcepto {
  MATRICULA
  PENSION
  KIT_ESCOLAR
  TRANSPORTE
  ALIMENTACION
  ACTIVIDAD_EXTRACURRICULAR
  OTRO
}

enum MedioPago {
  EFECTIVO
  TRANSFERENCIA_BANCARIA
  DATAFONO
  CHEQUE
  OTRO
}

enum EstadoPago {
  PENDIENTE
  PAGADO
  PAGO_PARCIAL
  EXONERADO
  EN_MORA
}

enum EstadoCita {
  PROGRAMADA
  REALIZADA
  CANCELADA
  NO_ASISTIO
}

enum TipoDestinatario {
  TODOS
  SOLO_DOCENTES
  SOLO_ESTUDIANTES
  SOLO_PADRES
  GRADO_ESPECIFICO
  GRUPO_ESPECIFICO
}

// ============================================================
// INSTITUCIÓN Y CONFIGURACIÓN
// ============================================================

model Colegio {
  id                    String         @id @default(cuid())
  nombre                String
  nombreCorto           String?
  nit                   String         @unique
  codigoDane            String         @unique  // 12 dígitos
  naturaleza            Naturaleza
  calendarioTipo        CalendarioTipo
  jornadasActivas       Jornada[]
  nivelesActivos        Nivel[]
  modalidadMedia        ModalidadMedia?
  municipio             String
  departamento          String
  direccion             String
  telefono              String?
  emailInstitucional    String?
  sitioWeb              String?
  logoUrl               String?
  resolucionAprobacion  String?
  secretariaEducacion   String?         // Municipio o departamento certificado
  planEstudios          String?         // URL al PEI/plan de estudios
  activo                Boolean         @default(true)
  creadoEn              DateTime        @default(now())
  actualizadoEn         DateTime        @updatedAt

  // Relaciones
  aniosAcademicos       AnioAcademico[]
  usuarios              UsuarioColegio[]
  grados                Grado[]
  areas                 Area[]
  asignaturas           Asignatura[]
  inscripciones         Inscripcion[]
  circulares            Circular[]
  configuracionSIEE     ConfiguracionSIEE?
  conceptosCobro        ConceptoCobro[]
  solicitudesDocumento  SolicitudDocumento[]
  horarios              Horario[]
  comisiones            ComisionEvaluacion[]
}

model AnioAcademico {
  id            String    @id @default(cuid())
  colegioId     String
  colegio       Colegio   @relation(fields: [colegioId], references: [id])
  anio          Int
  fechaInicio   DateTime
  fechaFin      DateTime
  activo        Boolean   @default(false)
  creadoEn      DateTime  @default(now())

  // Relaciones
  periodos      PeriodoAcademico[]
  matriculas    Matricula[]
  inscripciones Inscripcion[]
  grupos        Grupo[]
  logros        Logro[]
  calificaciones Calificacion[]
  notasAnuales  NotaAnual[]
  asistencias   RegistroAsistencia[]
  pagos         Pago[]
  comisiones    ComisionEvaluacion[]
  horarios      Horario[]

  @@unique([colegioId, anio])
}

model PeriodoAcademico {
  id              String        @id @default(cuid())
  anioAcademicoId String
  anioAcademico   AnioAcademico @relation(fields: [anioAcademicoId], references: [id])
  numero          Int           // 1, 2, 3, 4
  nombre          String        // "Primer Período"
  fechaInicio     DateTime
  fechaFin        DateTime
  fechaCierreNotas DateTime?    // Fecha límite para ingresar notas
  porcentaje      Decimal       // Peso en nota final anual (ej: 25.00)
  abierto         Boolean       @default(true)
  creadoEn        DateTime      @default(now())

  // Relaciones
  calificaciones  Calificacion[]
  logros          Logro[]
  comisiones      ComisionEvaluacion[]

  @@unique([anioAcademicoId, numero])
}

// ============================================================
// ESTRUCTURA ACADÉMICA
// ============================================================

model Grado {
  id          String    @id @default(cuid())
  colegioId   String
  colegio     Colegio   @relation(fields: [colegioId], references: [id])
  nivel       Nivel
  nombre      String    // "Grado 1°", "Transición", "Grado 10°"
  numero      Int       // 0=Transición, 1-11
  orden       Int       // Para ordenar en listados
  activo      Boolean   @default(true)
  creadoEn    DateTime  @default(now())

  // Relaciones
  grupos         Grupo[]
  gradoAsignatura GradoAsignatura[]
  calificaciones  Calificacion[]
  logros          Logro[]
  notasAnuales    NotaAnual[]

  @@unique([colegioId, nivel, numero])
}

model Grupo {
  id                String    @id @default(cuid())
  anioAcademicoId   String
  anioAcademico     AnioAcademico @relation(fields: [anioAcademicoId], references: [id])
  gradoId           String
  grado             Grado     @relation(fields: [gradoId], references: [id])
  nombre            String    // "A", "B", "C"
  jornada           Jornada
  cupoMaximo        Int       @default(35)
  directorGrupoId   String?   // FK a UsuarioColegio
  activo            Boolean   @default(true)
  creadoEn          DateTime  @default(now())

  // Relaciones
  directorGrupo     UsuarioColegio? @relation("DirectorDeGrupo", fields: [directorGrupoId], references: [id])
  matriculas        Matricula[]
  asignaciones      AsignacionDocente[]
  calificaciones    Calificacion[]
  asistencias       RegistroAsistencia[]
  horarioClases     HorarioClase[]
  circulares        CircularGrupo[]
  notasAnuales      NotaAnual[]

  @@unique([anioAcademicoId, gradoId, nombre, jornada])
}

model Area {
  id          String    @id @default(cuid())
  colegioId   String
  colegio     Colegio   @relation(fields: [colegioId], references: [id])
  nombre      String    // "Matemáticas"
  tipo        TipoArea
  obligatoria Boolean   @default(true)
  orden       Int
  activo      Boolean   @default(true)
  creadoEn    DateTime  @default(now())

  // Relaciones
  asignaturas   Asignatura[]
  jefesArea     JefeArea[]

  @@unique([colegioId, nombre])
}

model Asignatura {
  id          String    @id @default(cuid())
  colegioId   String
  colegio     Colegio   @relation(fields: [colegioId], references: [id])
  areaId      String
  area        Area      @relation(fields: [areaId], references: [id])
  nombre      String    // "Álgebra", "Biología", "Inglés"
  codigo      String?   // Código interno
  activo      Boolean   @default(true)
  creadoEn    DateTime  @default(now())

  // Relaciones
  gradoAsignatura   GradoAsignatura[]
  asignaciones      AsignacionDocente[]
  calificaciones    Calificacion[]
  logros            Logro[]
  horarioClases     HorarioClase[]
  asistencias       RegistroAsistencia[]
  notasAnuales      NotaAnual[]

  @@unique([colegioId, areaId, nombre])
}

model GradoAsignatura {
  id                String     @id @default(cuid())
  gradoId           String
  grado             Grado      @relation(fields: [gradoId], references: [id])
  asignaturaId      String
  asignatura        Asignatura @relation(fields: [asignaturaId], references: [id])
  intensidadSemanal Int        // Horas por semana
  evaualcionIndependiente Boolean @default(true) // Si aparece en boletín
  creadoEn          DateTime   @default(now())

  @@unique([gradoId, asignaturaId])
}

// ============================================================
// USUARIOS Y PERSONAS
// ============================================================

model Usuario {
  id            String    @id @default(cuid())
  email         String    @unique
  passwordHash  String
  activo        Boolean   @default(true)
  creadoEn      DateTime  @default(now())
  actualizadoEn DateTime  @updatedAt

  // Relaciones
  colegios      UsuarioColegio[]
  persona       Persona?
}

model UsuarioColegio {
  id          String    @id @default(cuid())
  usuarioId   String
  usuario     Usuario   @relation(fields: [usuarioId], references: [id])
  colegioId   String
  colegio     Colegio   @relation(fields: [colegioId], references: [id])
  roles       Rol[]
  activo      Boolean   @default(true)
  creadoEn    DateTime  @default(now())

  // Relaciones
  docentePerfil    DocentePerfil?
  directorDeGrupo  Grupo[]           @relation("DirectorDeGrupo")
  jefesArea        JefeArea[]
  asignaciones     AsignacionDocente[]
  calificacionesRegistradas Calificacion[] @relation("RegistradaPor")
  asistenciasRegistradas    RegistroAsistencia[] @relation("RegistradaPor")
  anotacionesRegistradas    AnotacionConvivencia[] @relation("RegistradaPor")
  orientacionesRealizadas   CitaOrientacion[] @relation("OrientadorCita")

  @@unique([usuarioId, colegioId])
}

model Persona {
  id                String         @id @default(cuid())
  usuarioId         String         @unique
  usuario           Usuario        @relation(fields: [usuarioId], references: [id])
  tipoDocumento     TipoDocumento
  numeroDocumento   String
  primerNombre      String
  segundoNombre     String?
  primerApellido    String
  segundoApellido   String?
  fechaNacimiento   DateTime?
  genero            Genero?
  lugarNacimiento   String?
  telefono          String?
  celular           String?
  direccionResidencia String?
  municipioResidencia String?
  fotografiaUrl     String?
  creadoEn          DateTime       @default(now())
  actualizadoEn     DateTime       @updatedAt

  // Relaciones
  docentePerfil     DocentePerfil?
  estudiantePerfil  EstudiantePerfil?
  acudientePerfil   AcudientePerfil?

  @@unique([tipoDocumento, numeroDocumento])
}

model DocentePerfil {
  id                  String         @id @default(cuid())
  usuarioColegioId    String         @unique
  usuarioColegio      UsuarioColegio @relation(fields: [usuarioColegioId], references: [id])
  titulo              String?
  especializacion     String?
  escalafon           Escalafon?
  gradoEscalafon      String?        // "2A", "14"
  fechaVinculacion    DateTime?
  tipoContrato        TipoContrato
  resolucionNombramiento String?
  epsId               String?
  afp                 String?        // AFP (fondo de pensión)
  creadoEn            DateTime       @default(now())
  actualizadoEn       DateTime       @updatedAt
}

model EstudiantePerfil {
  id                  String         @id @default(cuid())
  usuarioId           String         @unique
  usuario             Usuario        @relation(fields: [usuarioId], references: [id]) // ← FK a Usuario directamente
  colegioId           String
  codigoEstudiante    String?        @unique // Código asignado por el colegio
  eps                 String?
  grupoSanguineo      String?
  estrato             Int?
  sisBenPuntaje       String?
  tieneDiscapacidad   Boolean        @default(false)
  descripcionDiscapacidad String?
  etnia               String?
  regimenSalud        String?        // CONTRIBUTIVO / SUBSIDIADO
  creadoEn            DateTime       @default(now())
  actualizadoEn       DateTime       @updatedAt

  // Relaciones
  acudientes          RelacionAcudiente[]
  matriculas          Matricula[]
  calificaciones      Calificacion[]
  notasAnuales        NotaAnual[]
  asistencias         RegistroAsistencia[]
  anotaciones         AnotacionConvivencia[]
  documentos          DocumentoEstudiante[]
  solicitudesDocumento SolicitudDocumento[]
  pagos               Pago[]
  citasOrientacion    CitaOrientacion[]
  decisiones          DecisionComision[]
}

model AcudientePerfil {
  id              String    @id @default(cuid())
  usuarioId       String    @unique
  usuario         Usuario   @relation(fields: [usuarioId], references: [id])
  ocupacion       String?
  lugarTrabajo    String?
  telefonoTrabajo String?
  creadoEn        DateTime  @default(now())

  // Relaciones
  estudiantesACargo RelacionAcudiente[]
}

model RelacionAcudiente {
  id                    String           @id @default(cuid())
  estudianteId          String
  estudiante            EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  acudienteId           String
  acudiente             AcudientePerfil  @relation(fields: [acudienteId], references: [id])
  parentesco            Parentesco
  esAcudientePrincipal  Boolean          @default(false)
  autorizadoRecoger     Boolean          @default(true)
  creadoEn              DateTime         @default(now())

  @@unique([estudianteId, acudienteId])
}

// ============================================================
// INSCRIPCIÓN Y MATRÍCULA
// ============================================================

model Inscripcion {
  id                  String            @id @default(cuid())
  colegioId           String
  colegio             Colegio           @relation(fields: [colegioId], references: [id])
  anioAcademicoId     String
  anioAcademico       AnioAcademico     @relation(fields: [anioAcademicoId], references: [id])
  // Datos del aspirante
  tipoDocumento       TipoDocumento
  numeroDocumento     String
  primerNombre        String
  segundoNombre       String?
  primerApellido      String
  segundoApellido     String?
  fechaNacimiento     DateTime
  genero              Genero?
  gradoSolicitado     String            // "6°", "1°", "Transición"
  gradoAprobadoAnterior String?         // Grado que aprobó antes
  colegioProcedenteNombre String?
  colegioProcedenteCity  String?
  // Datos del acudiente
  nombreAcudiente     String
  parentescoAcudiente Parentesco
  celularAcudiente    String
  emailAcudiente      String?
  // Proceso
  estado              EstadoInscripcion @default(PENDIENTE)
  observacionesRevision String?
  motivoRechazo       String?
  documentosAdjuntos  Json?             // URLs de documentos subidos
  fechaInscripcion    DateTime          @default(now())
  fechaRevision       DateTime?
  revisadaPorId       String?           // UsuarioColegio.id
  matriculaGenerada   Matricula?
}

model Matricula {
  id                  String          @id @default(cuid())
  numeroMatricula     String          @unique // Ej: 2025-001-0001
  estudianteId        String
  estudiante          EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  grupoId             String
  grupo               Grupo           @relation(fields: [grupoId], references: [id])
  anioAcademicoId     String
  anioAcademico       AnioAcademico   @relation(fields: [anioAcademicoId], references: [id])
  inscripcionId       String?         @unique
  inscripcion         Inscripcion?    @relation(fields: [inscripcionId], references: [id])
  tipo                TipoMatricula
  estado              EstadoMatricula @default(ACTIVA)
  fechaMatricula      DateTime        @default(now())
  contratoFirmado     Boolean         @default(false)
  fechaFirmaContrato  DateTime?
  documentosEntregados Json?          // Checklist de documentos
  observaciones       String?
  matriculadaPorId    String          // UsuarioColegio.id de la secretaria
  // Retiro
  fechaRetiro         DateTime?
  motivoRetiro        String?
  colegioDestino      String?
  creadoEn            DateTime        @default(now())
  actualizadoEn       DateTime        @updatedAt

  @@unique([estudianteId, anioAcademicoId])
}

model DocumentoEstudiante {
  id                String           @id @default(cuid())
  estudianteId      String
  estudiante        EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  tipo              String           // "REGISTRO_CIVIL", "TI", "FOTO", "BOLETIN_ANTERIOR"
  nombre            String
  url               String
  subidoEn          DateTime         @default(now())
  subidoPorId       String
}

// ============================================================
// ASIGNACIÓN DE DOCENTES
// ============================================================

model AsignacionDocente {
  id               String         @id @default(cuid())
  usuarioColegioId String
  usuarioColegio   UsuarioColegio @relation(fields: [usuarioColegioId], references: [id])
  grupoId          String
  grupo            Grupo          @relation(fields: [grupoId], references: [id])
  asignaturaId     String
  asignatura       Asignatura     @relation(fields: [asignaturaId], references: [id])
  anioAcademicoId  String
  intensidadSemanal Int           // Horas por semana asignadas
  activa           Boolean        @default(true)
  creadoEn         DateTime       @default(now())

  @@unique([usuarioColegioId, grupoId, asignaturaId, anioAcademicoId])
}

model JefeArea {
  id               String         @id @default(cuid())
  usuarioColegioId String
  usuarioColegio   UsuarioColegio @relation(fields: [usuarioColegioId], references: [id])
  areaId           String
  area             Area           @relation(fields: [areaId], references: [id])
  anioAcademicoId  String
  creadoEn         DateTime       @default(now())

  @@unique([areaId, anioAcademicoId])
}

// ============================================================
// SIEE — SISTEMA INSTITUCIONAL DE EVALUACIÓN
// ============================================================

model ConfiguracionSIEE {
  id                      String    @id @default(cuid())
  colegioId               String    @unique
  colegio                 Colegio   @relation(fields: [colegioId], references: [id])
  // Escala numérica
  notaMinima              Decimal   @default(1.0)
  notaMaxima              Decimal   @default(5.0)
  decimales               Int       @default(1)
  // Criterios de evaluación por período
  criterioSer             Boolean   @default(true)
  porcentajeSer           Int       @default(20)
  criterioSaber           Boolean   @default(true)
  porcentajeSaber         Int       @default(40)
  criterioHacer           Boolean   @default(true)
  criterioHacerNombre     String    @default("Hacer")
  porcentajeHacer         Int       @default(40)
  // Política de promoción
  maxAreasBajoSinHabilitar Int      @default(3)  // Máximo de Bajos que no requieren habilitación
  maxAreasHabilitacion    Int       @default(3)  // Máximo de áreas habilitables
  notaMinimaHabilitacion  Decimal   @default(3.0)
  promediarHabilitacion   Boolean   @default(false) // false = reemplaza, true = promedia
  // Regla de promoción
  maxAreasBajoParaPromocion Int     @default(2) // Máximo de Bajo para promover
  // Preescolar no reprueba automáticamente
  preescolarNoReprueba    Boolean   @default(true)
  // Otras configuraciones
  registrarAsistenciaPorClase Boolean @default(true)
  porcentajeAsistenciaMinima  Int   @default(75) // Mínimo % de asistencia para no perder por faltas
  actualizadoEn           DateTime  @updatedAt

  // Relaciones
  escalas                 EscalaValoracion[]
}

model EscalaValoracion {
  id          String           @id @default(cuid())
  sieeId      String
  siee        ConfiguracionSIEE @relation(fields: [sieeId], references: [id])
  desempeno   Desempeno
  valorMinimo Decimal
  valorMaximo Decimal
  descripcion String
  colorHex    String           @default("#000000") // Para UI

  @@unique([sieeId, desempeno])
}

// ============================================================
// LOGROS E INDICADORES
// ============================================================

model Logro {
  id              String           @id @default(cuid())
  asignaturaId    String
  asignatura      Asignatura       @relation(fields: [asignaturaId], references: [id])
  gradoId         String
  grado           Grado            @relation(fields: [gradoId], references: [id])
  periodoId       String
  periodo         PeriodoAcademico @relation(fields: [periodoId], references: [id])
  anioAcademicoId String
  anioAcademico   AnioAcademico    @relation(fields: [anioAcademicoId], references: [id])
  descripcion     String
  orden           Int              @default(1)
  creadoEn        DateTime         @default(now())

  // Relaciones
  indicadores     IndicadorLogro[]

  @@unique([asignaturaId, gradoId, periodoId])
}

model IndicadorLogro {
  id          String  @id @default(cuid())
  logroId     String
  logro       Logro   @relation(fields: [logroId], references: [id])
  descripcion String
  porcentaje  Decimal @default(100) // Si hay varios, suman 100
  orden       Int     @default(1)
}

// ============================================================
// CALIFICACIONES
// ============================================================

model Calificacion {
  id                  String           @id @default(cuid())
  // Qué se califica
  estudianteId        String
  estudiante          EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  asignaturaId        String
  asignatura          Asignatura       @relation(fields: [asignaturaId], references: [id])
  gradoId             String
  grado               Grado            @relation(fields: [gradoId], references: [id])
  grupoId             String
  grupo               Grupo            @relation(fields: [grupoId], references: [id])
  periodoId           String
  periodo             PeriodoAcademico @relation(fields: [periodoId], references: [id])
  anioAcademicoId     String
  anioAcademico       AnioAcademico    @relation(fields: [anioAcademicoId], references: [id])
  // Notas por criterio
  notaSer             Decimal?
  notaSaber           Decimal?
  notaHacer           Decimal?
  // Calculadas
  notaDefinitiva      Decimal          // (Ser*%Ser + Saber*%Saber + Hacer*%Hacer) / 100
  desempeno           Desempeno        // Calculado a partir de escala SIEE
  // Nivelación
  realizoNivelacion   Boolean          @default(false)
  notaNivelacion      Decimal?
  notaConNivelacion   Decimal?         // Nota ajustada tras nivelación
  desempenoConNivelacion Desempeno?
  // Observaciones del docente
  observaciones       String?
  // Control
  cerrada             Boolean          @default(false) // Solo rector/coordinador puede abrir
  registradaPorId     String
  registradaPor       UsuarioColegio   @relation("RegistradaPor", fields: [registradaPorId], references: [id])
  fechaRegistro       DateTime         @default(now())
  actualizadoEn       DateTime         @updatedAt

  @@unique([estudianteId, asignaturaId, periodoId])
}

model NotaAnual {
  id                  String           @id @default(cuid())
  estudianteId        String
  estudiante          EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  asignaturaId        String
  asignatura          Asignatura       @relation(fields: [asignaturaId], references: [id])
  gradoId             String
  grado               Grado            @relation(fields: [gradoId], references: [id])
  grupoId             String
  grupo               Grupo            @relation(fields: [grupoId], references: [id])
  anioAcademicoId     String
  anioAcademico       AnioAcademico    @relation(fields: [anioAcademicoId], references: [id])
  // Notas
  promedioPeriodos    Decimal          // Suma ponderada de los períodos
  desempeno           Desempeno
  // Habilitación
  requiereHabilitacion Boolean         @default(false)
  realizoHabilitacion  Boolean         @default(false)
  notaHabilitacion    Decimal?
  notaDefinitiva      Decimal          // Final después de habilitación (si aplica)
  desempenoDefinitivo Desempeno
  aprobada            Boolean
  // Control
  calculadaEn         DateTime         @default(now())
  actualizadoEn       DateTime         @updatedAt

  @@unique([estudianteId, asignaturaId, anioAcademicoId])
}

// ============================================================
// ASISTENCIA
// ============================================================

model RegistroAsistencia {
  id              String           @id @default(cuid())
  estudianteId    String
  estudiante      EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  grupoId         String
  grupo           Grupo            @relation(fields: [grupoId], references: [id])
  asignaturaId    String?          // null = asistencia diaria global
  asignatura      Asignatura?      @relation(fields: [asignaturaId], references: [id])
  anioAcademicoId String
  anioAcademico   AnioAcademico    @relation(fields: [anioAcademicoId], references: [id])
  fecha           DateTime         // Solo fecha, hora 00:00
  estado          EstadoAsistencia
  justificacion   String?
  documentoJustificacion String?   // URL
  registradaPorId String
  registradaPor   UsuarioColegio   @relation("RegistradaPor", fields: [registradaPorId], references: [id])
  creadoEn        DateTime         @default(now())

  @@unique([estudianteId, asignaturaId, fecha, grupoId])
}

// ============================================================
// HORARIOS
// ============================================================

model Horario {
  id              String        @id @default(cuid())
  colegioId       String
  colegio         Colegio       @relation(fields: [colegioId], references: [id])
  anioAcademicoId String
  anioAcademico   AnioAcademico @relation(fields: [anioAcademicoId], references: [id])
  nombre          String        // "Horario 2025 Jornada Mañana"
  jornada         Jornada
  activo          Boolean       @default(true)
  creadoEn        DateTime      @default(now())

  // Relaciones
  franjas         FranjaHoraria[]
  clases          HorarioClase[]
}

model FranjaHoraria {
  id          String    @id @default(cuid())
  horarioId   String
  horario     Horario   @relation(fields: [horarioId], references: [id])
  nombre      String    // "Primera hora", "Descanso"
  horaInicio  String    // "07:00"
  horaFin     String    // "08:00"
  tipo        TipoFranja
  orden       Int

  // Relaciones
  clases      HorarioClase[]
}

model HorarioClase {
  id               String         @id @default(cuid())
  horarioId        String
  horario          Horario        @relation(fields: [horarioId], references: [id])
  grupoId          String
  grupo            Grupo          @relation(fields: [grupoId], references: [id])
  asignaturaId     String
  asignatura       Asignatura     @relation(fields: [asignaturaId], references: [id])
  franjaId         String
  franja           FranjaHoraria  @relation(fields: [franjaId], references: [id])
  diaSemana        DiaSemana
  docenteId        String         // UsuarioColegio.id
  aula             String?        // Salón / aula

  @@unique([grupoId, franjaId, diaSemana])
  @@unique([docenteId, franjaId, diaSemana]) // Un docente no puede estar en 2 clases a la vez
}

// ============================================================
// CONVIVENCIA
// ============================================================

model AnotacionConvivencia {
  id                    String           @id @default(cuid())
  estudianteId          String
  estudiante            EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  tipo                  TipoAnotacion
  nivelFalta            NivelFalta?      // Solo para NEGATIVA
  descripcion           String
  lugarHecho            String?
  fechaHecho            DateTime
  medidaPedagogica      String?
  compromiso            String?
  seguimiento           String?
  confidencial          Boolean          @default(false)
  registradaPorId       String
  registradaPor         UsuarioColegio   @relation("RegistradaPor", fields: [registradaPorId], references: [id])
  creadoEn              DateTime         @default(now())
  actualizadoEn         DateTime         @updatedAt

  // Protocolo Ley 1620
  requiereProtocolo     Boolean          @default(false)
  protocoloId           String?
  protocolo             ProtocoloConvivencia? @relation(fields: [protocoloId], references: [id])

  // Notificación a acudiente
  acudienteNotificado   Boolean          @default(false)
  fechaNotificacionAcudiente DateTime?
  firmaAcudiente        Boolean          @default(false)
}

model ProtocoloConvivencia {
  id                String    @id @default(cuid())
  colegioId         String
  titulo            String
  descripcion       String
  estudiantesInvolucrados String[] // IDs de EstudiantePerfil
  tipoSituacion     String    // Según Art. 40 Decreto 1965: Tipo I, II, III
  estado            EstadoProtocolo @default(ABIERTO)
  medidasAcordadas  String?
  seguimientos      String[]
  actaUrl           String?
  responsableId     String    // UsuarioColegio.id (coordinador de convivencia)
  creadoEn          DateTime  @default(now())
  cerradoEn         DateTime?

  // Relaciones
  anotaciones       AnotacionConvivencia[]
}

// ============================================================
// COMUNICACIONES
// ============================================================

model Circular {
  id                String    @id @default(cuid())
  colegioId         String
  colegio           Colegio   @relation(fields: [colegioId], references: [id])
  numero            String    // "Circular 001-2025"
  titulo            String
  contenido         String
  tipoDestinatario  TipoDestinatario
  archivosAdjuntos  Json?     // [{nombre, url}]
  publicadoPorId    String    // UsuarioColegio.id
  fechaPublicacion  DateTime  @default(now())
  activo            Boolean   @default(true)

  // Relaciones
  gruposDestino     CircularGrupo[]
}

model CircularGrupo {
  circularId  String
  circular    Circular @relation(fields: [circularId], references: [id])
  grupoId     String
  grupo       Grupo    @relation(fields: [grupoId], references: [id])

  @@id([circularId, grupoId])
}

// ============================================================
// SECRETARÍA
// ============================================================

model SolicitudDocumento {
  id                String           @id @default(cuid())
  colegioId         String
  colegio           Colegio          @relation(fields: [colegioId], references: [id])
  estudianteId      String
  estudiante        EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  tipoDocumento     TipoDocumentoSolicitado
  anioAcademicoId   String?          // Para documentos de un año específico
  periodoId         String?          // Para certificado de un período
  proposito         String?          // Para qué requiere el documento
  estado            EstadoSolicitud  @default(PENDIENTE)
  observaciones     String?
  solicitadoPorId   String           // UsuarioColegio.id (o el mismo estudiante/padre)
  fechaSolicitud    DateTime         @default(now())
  asignadaAId       String?          // Secretaria que lo procesa
  fechaEmision      DateTime?
  documentoUrl      String?
  entregado         Boolean          @default(false)
  fechaEntrega      DateTime?
}

// ============================================================
// FINANCIERO
// ============================================================

model ConceptoCobro {
  id              String        @id @default(cuid())
  colegioId       String
  colegio         Colegio       @relation(fields: [colegioId], references: [id])
  anioAcademicoId String
  nombre          String        // "Pensión Marzo 2025"
  tipo            TipoConcepto
  mes             Int?          // 1-12 para pensiones
  monto           Decimal
  fechaLimite     DateTime?
  obligatorio     Boolean       @default(true)
  activo          Boolean       @default(true)
  creadoEn        DateTime      @default(now())

  // Relaciones
  pagos           Pago[]
}

model Pago {
  id              String        @id @default(cuid())
  estudianteId    String
  estudiante      EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  conceptoId      String
  concepto        ConceptoCobro @relation(fields: [conceptoId], references: [id])
  anioAcademicoId String
  anioAcademico   AnioAcademico @relation(fields: [anioAcademicoId], references: [id])
  montoCobrado    Decimal
  montoPagado     Decimal
  saldo           Decimal       // montoCobrado - montoPagado
  fechaPago       DateTime?
  medioPago       MedioPago?
  numeroRecibo    String?
  comprobante     String?       // URL
  observaciones   String?
  registradoPorId String
  estado          EstadoPago    @default(PENDIENTE)
  exoneracion     String?       // Motivo si está exonerado
  creadoEn        DateTime      @default(now())
  actualizadoEn   DateTime      @updatedAt
}

// ============================================================
// ORIENTACIÓN ESCOLAR
// ============================================================

model CitaOrientacion {
  id              String           @id @default(cuid())
  estudianteId    String
  estudiante      EstudiantePerfil @relation(fields: [estudianteId], references: [id])
  orientadorId    String
  orientador      UsuarioColegio   @relation("OrientadorCita", fields: [orientadorId], references: [id])
  motivo          String
  fecha           DateTime
  duracionMinutos Int              @default(60)
  notas           String?          // Confidencial
  seguimiento     String?
  remision        String?          // Si se remite a profesional externo
  estado          EstadoCita       @default(PROGRAMADA)
  acudienteInformado Boolean       @default(false)
  creadoEn        DateTime         @default(now())
}

// ============================================================
// COMISIÓN DE EVALUACIÓN Y PROMOCIÓN
// ============================================================

model ComisionEvaluacion {
  id                String          @id @default(cuid())
  colegioId         String
  colegio           Colegio         @relation(fields: [colegioId], references: [id])
  anioAcademicoId   String
  anioAcademico     AnioAcademico   @relation(fields: [anioAcademicoId], references: [id])
  periodoId         String?         // null = comisión fin de año
  periodo           PeriodoAcademico? @relation(fields: [periodoId], references: [id])
  tipo              TipoComision
  gradoId           String?         // Por grado, o null si es institucional
  fecha             DateTime
  actaNumero        String?
  actaUrl           String?
  observacionesGenerales String?
  presididaPorId    String          // UsuarioColegio.id
  participanteIds   String[]        // Array de UsuarioColegio.ids
  creadoEn          DateTime        @default(now())

  // Relaciones
  decisiones        DecisionComision[]
}

model DecisionComision {
  id              String             @id @default(cuid())
  comisionId      String
  comision        ComisionEvaluacion @relation(fields: [comisionId], references: [id])
  estudianteId    String
  estudiante      EstudiantePerfil   @relation(fields: [estudianteId], references: [id])
  decision        TipoDecision
  areasEnBajo     String[]           // IDs de asignaturas con Bajo
  areasHabilitar  String[]           // IDs de asignaturas a habilitar
  observaciones   String
  notificadoEstudiante  Boolean      @default(false)
  notificadoAcudiente   Boolean      @default(false)
  fechaNotificacion     DateTime?
}
```

---

## E. MÓDULOS DEL SISTEMA

### E1. MÓDULO: INSTITUCIÓN

**Responsable:** Rector / Superadmin
**NestJS:** `src/tenant/` y `src/institution/`

**Funcionalidades:**
- **Crear colegio:** NIT, nombre, DANE, naturaleza, calendario, jornadas.
- **Configurar institución:** logo, dirección, contacto, resolución de aprobación.
- **Gestionar años académicos:** crear año, definir fechas de inicio/fin, activar el año en curso.
- **Gestionar períodos:** crear 4 períodos por año, asignar porcentajes (deben sumar 100%), definir fechas de apertura y cierre de notas.
- **Configurar el SIEE:** escala numérica, criterios de evaluación y sus pesos (deben sumar 100%), escala de desempeño (cada nivel con rango min-max), política de promoción, habilitaciones.

**Validaciones críticas:**
- Los porcentajes de los períodos deben sumar exactamente 100%.
- Los porcentajes de los criterios de evaluación (Ser + Saber + Hacer) deben sumar 100%.
- Los rangos de la escala de valoración no deben solaparse.
- Solo puede haber un año académico activo a la vez por colegio.

---

### E2. MÓDULO: ESTRUCTURA ACADÉMICA

**Responsable:** Rector / Coordinador Académico
**NestJS:** `src/academic-structure/`

**Funcionalidades:**
- **Grados:** El sistema precarga los grados estándar al crear el colegio según los niveles seleccionados. El rector puede activar/desactivar grados.
- **Grupos:** Por cada año académico, crear los grupos de cada grado (A, B, C…), asignar jornada, cupo máximo, director de grupo.
- **Áreas:** El sistema precarga las 10 áreas obligatorias de la Ley 115. El colegio puede añadir áreas optativas.
- **Asignaturas:** Crear asignaturas dentro de cada área. Asignar a grados con intensidad horaria semanal.
- **Asignación de docentes:** Por año académico, asignar cada asignatura en cada grupo a un docente específico.
- **Jefes de área:** Designar un docente como jefe de área por año académico.

**Reglas de negocio:**
- Un grupo debe tener al menos un director de grupo asignado para poder cerrar matrícula.
- La intensidad horaria total de un grado no debe superar la jornada permitida.
- Una asignatura no puede tener el mismo docente en dos grupos al mismo horario (validar al crear horario).

---

### E3. MÓDULO: GESTIÓN DE USUARIOS Y PERSONAL

**Responsable:** Rector / Secretaría
**NestJS:** `src/users/`, `src/staff/`

**Funcionalidades:**
- **Crear usuario:** email, contraseña temporal, asignar rol(es) en el colegio.
- **Crear perfil de persona:** todos los datos personales, datos de contacto.
- **Crear perfil de docente:** título, escalafón, tipo de contrato, fecha de vinculación.
- **Editar datos:** actualizar información de cualquier usuario.
- **Suspender/reactivar usuario:** desactivar sin eliminar.
- **Resetear contraseña:** enviar correo de restablecimiento.
- **Ver directorio de docentes:** listado con filtros por área, jornada, contrato.
- **Ver carga académica de docente:** resumen de grupos y asignaturas asignados.

---

### E4. MÓDULO: INSCRIPCIONES Y MATRÍCULA

**Responsable:** Secretaría / Rector
**NestJS:** `src/enrollment/`

#### E4.1 Proceso de Inscripción (Nuevos Estudiantes)

1. **Formulario público de inscripción** (disponible sin login): padres llenan datos del aspirante y del acudiente, seleccionan grado al que aspiran, adjuntan documentos requeridos.
2. **Revisión por secretaría:** cambiar estado a EN_REVISION, adjuntar observaciones.
3. **Admisión:** cambiar a ADMITIDO o RECHAZADO (con motivo) o EN_LISTA_ESPERA.
4. **Conversión a matrícula:** al admitir, se crea automáticamente un Usuario para el estudiante y se inicia el proceso de matrícula.

#### E4.2 Proceso de Matrícula

**Para nuevos admitidos:**
1. Secretaría crea la matrícula a partir de la inscripción aprobada.
2. Asigna al estudiante a un grupo específico.
3. Registra documentos entregados (checklist).
4. Genera el número de matrícula único (formato: `{AÑO}-{GRADO}-{CONSECUTIVO}`).
5. Registra si se firmó el contrato de prestación de servicio educativo.

**Para renovaciones (estudiantes existentes):**
1. Al inicio del año académico, el sistema lista todos los estudiantes del año anterior.
2. Secretaría puede renovar en masa (promovidos) o individual.
3. Los reprobados se renuevan en el mismo grado.
4. Se actualiza el grupo (puede cambiar).

**Documentos requeridos para matrícula (checklist):**
- Fotocopia del documento de identidad del estudiante (CC/TI/RC/NIP).
- Fotocopia del documento de identidad del acudiente.
- Foto del estudiante (3x4 o digital).
- Carnet de vacunas (preescolar y primaria).
- Boletín del año anterior (grado que aprobó).
- Certificado médico (si tiene discapacidad o condición especial).

#### E4.3 Retiro de Estudiante

- Registro de fecha de retiro, motivo (traslado a otro colegio, deserción, otro) y colegio destino.
- La matrícula pasa a estado RETIRADA.
- El sistema genera automáticamente una constancia de estudio con la fecha de retiro.
- Se registra la paz y salvo académico y financiero al momento del retiro.

---

### E5. MÓDULO: SISTEMA DE EVALUACIÓN — CALIFICACIONES

**Responsable:** Docentes (ingresar notas) / Coordinador Académico (supervisar) / Rector (aprobar cierre)
**NestJS:** `src/grades/`, `src/annual-grades/`, `src/achievements/`

#### E5.1 Flujo de Calificación por Período

```
PERÍODO ABIERTO
    ↓
Docente ingresa notas por criterio (Ser, Saber, Hacer) por estudiante
    ↓ Sistema calcula automáticamente:
    notaDefinitiva = (notaSer * %Ser + notaSaber * %Saber + notaHacer * %Hacer) / 100
    desempeno = según escala SIEE
    ↓
Docente registra observaciones individuales (opcional)
    ↓
Coordinador revisa y cierra el período
    ↓ Sistema calcula estado de cada estudiante:
    - Cuántas áreas tiene en BAJO
    - Si requiere nivelación
    ↓
Comisión de Evaluación y Promoción (fin de período)
    ↓
Período CERRADO
```

#### E5.2 Reglas de Calificación

- El docente solo puede ingresar notas en períodos ABIERTOS.
- El docente solo puede calificar las asignaturas y grupos asignados.
- Las notas van de `notaMinima` a `notaMaxima` según SIEE (p.ej. 1.0 a 5.0).
- Si el SIEE no tiene criterio Ser, el sistema agrupa todo en Saber y Hacer.
- Si se registra una nivelación: `notaConNivelacion = max(notaDefinitiva, notaNivelacion)` o según política del SIEE.

#### E5.3 Cierre del Año y Nota Definitiva

```
FIN DEL AÑO ACADÉMICO
    ↓
Sistema calcula nota anual por área por estudiante:
    promedioPeriodos = Σ(notaPeriodoN * porcentajePeriodoN / 100)
    ↓
Identificar estudiantes con áreas en BAJO
    ↓
HABILITACIONES (si aplica)
    Docente o coordinador ingresa nota de habilitación
    Si promediarHabilitacion=false: notaDefinitiva = notaHabilitacion
    Si promediarHabilitacion=true: notaDefinitiva = (promedioPeriodos + notaHabilitacion) / 2
    ↓
Comisión de Evaluación y Promoción Final
    ↓
Decisión por estudiante: PROMOVIDO / REPROBADO / HABILITACIÓN_PENDIENTE
    ↓
Cierre del año académico
```

#### E5.4 Regla de Promoción (configurable en SIEE)

```
SI (áreasConBajoDefinitivo > maxAreasHabilitacion)
    → REPROBADO (sin posibilidad de habilitación)
SINO SI (áreasConBajoDefinitivo > 0)
    → EN_HABILITACION
SINO
    → PROMOVIDO
DESPUÉS DE HABILITACIONES:
SI (áreasConBajoDefinitivo > maxAreasParaPromocion)
    → REPROBADO
SINO
    → PROMOVIDO
```

#### E5.5 Asistencia y su Impacto en la Nota

```
SI (% de asistencia del estudiante en una asignatura < porcentajeAsistenciaMinima)
    → El sistema genera alerta
    → El coordinador puede registrar pérdida de la asignatura por inasistencia
    → La asignatura queda en BAJO por inasistencia (independiente de la nota académica)
```

---

### E6. MÓDULO: ASISTENCIA

**Responsable:** Docentes (registrar) / Director de Grupo (asistencia diaria) / Coordinador (supervisar)
**NestJS:** `src/attendance/`

**Tipos de registro:**
1. **Por clase:** el docente toma asistencia al inicio de cada clase. Requiere horario configurado.
2. **Diaria (global):** el director de grupo toma asistencia una vez al día para todo el grupo.

**Flujo:**
1. Docente accede a "Tomar asistencia" → ve el listado de estudiantes de su grupo/asignatura.
2. Marca cada estudiante como: PRESENTE, AUSENTE, TARDANZA, EXCUSA_MEDICA.
3. Las AUSENCIAS pueden justificarse posteriormente (por secretaría o coordinador).
4. El sistema acumula el total de ausencias por asignatura para el cálculo del porcentaje.

**Cálculo del porcentaje de asistencia:**
```
% asistencia = (clases asistidas / total de clases del período) * 100
```

**Alertas automáticas:**
- Al superar el 10% de ausencias: alerta al director de grupo.
- Al superar el 20% de ausencias: alerta al coordinador y al acudiente.
- Al superar el 25% de ausencias: alerta de riesgo de pérdida por inasistencia.

---

### E7. MÓDULO: HORARIOS

**Responsable:** Coordinador Académico
**NestJS:** `src/schedule/`

**Proceso de construcción del horario:**
1. Coordinador crea la estructura del horario (franjas horarias del día: horas de clase, descansos).
2. Por cada grupo, día de la semana y franja, asigna: asignatura + docente + aula.
3. El sistema valida que un docente no esté asignado a dos clases al mismo tiempo.
4. El sistema valida que un grupo no tenga dos clases al mismo tiempo.
5. El horario se publica y es visible para docentes, estudiantes y padres.

**Restricciones:**
- Un grupo no puede tener más clases semanales de una asignatura que la intensidad horaria definida en `GradoAsignatura`.
- El sistema detecta conflictos (mismo docente, misma franja, mismo día).

---

### E8. MÓDULO: CONVIVENCIA

**Responsable:** Coordinador de Convivencia / Docentes (anotaciones leves)
**NestJS:** `src/coexistence/`

**Tipos de Situaciones (Ley 1620, Decreto 1965):**

| Tipo | Definición | Protocolo |
|------|------------|-----------|
| **Tipo I** | Conflictos y situaciones esporádicas que no generan daños | Resolución por mediación en el aula |
| **Tipo II** | Situaciones que no constituyen delito pero afectan la convivencia | Comité de convivencia escolar, acudientes |
| **Tipo III** | Situaciones que constituyen presuntos delitos | Denuncia ante autoridades competentes |

**Proceso de anotación:**
1. Docente o coordinador registra anotación: tipo, nivel, descripción, fecha, lugar.
2. Si es NEGATIVA GRAVE o GRAVÍSIMA → el sistema activa automáticamente el protocolo Ley 1620.
3. Se notifica al acudiente principal (registro de notificación + firma de enterado).
4. Se define medida pedagógica y se hace seguimiento.

**Comité de Convivencia Escolar:**
- Composición: rector (preside), coordinador de convivencia, docente con funciones de orientación, representante de padres, personero estudiantil.
- Se reúne mínimo una vez por período.
- Las decisiones del comité se registran como actas en el sistema.

---

### E9. MÓDULO: BOLETINES E INFORMES

**Responsable:** Director de Grupo (genera), Coordinador (aprueba), Rector (firma)
**NestJS:** `src/reports/`

**Boletín de notas — Contenido:**

```
ENCABEZADO:
  - Logo del colegio
  - Nombre de la institución
  - "INFORME ACADÉMICO — Período N — Año XXXX"
  - Resolución de aprobación
  
DATOS DEL ESTUDIANTE:
  - Nombre completo
  - Documento de identidad
  - Grado y grupo
  - Director de grupo
  - Jornada

TABLA DE CALIFICACIONES:
  Área | Asignatura | Nota Ser | Nota Saber | Nota Hacer | Nota Definitiva | Desempeño
  (Totales por área si hay varias asignaturas)

RESUMEN:
  - Total de ausencias en el período (justificadas / injustificadas)
  - Puesto en el grupo (si el colegio lo define)
  - % de asistencia

OBSERVACIONES:
  - Del docente director de grupo
  - De cada asignatura (si se ingresaron)

FIRMA:
  - Director de grupo
  - Coordinador Académico
  - Rector
  
PIE DE PÁGINA:
  - "Este boletín es un documento oficial..."
  - Fecha de emisión
```

**Boletín Anual:**
- Muestra los 4 períodos lado a lado.
- Muestra la nota definitiva anual.
- Indica: PROMOVIDO al grado X / EN HABILITACIÓN (asignatura X) / REPROBADO.
- Requiere firma del rector.

**Generación:**
- Individual o en masa (todo el grupo o grado).
- Formato PDF descargable.
- Disponible digitalmente para padres/estudiantes una vez publicado.

---

### E10. MÓDULO: SECRETARÍA

**Responsable:** Secretaria
**NestJS:** `src/secretary/`

**Documentos emitibles:**

| Documento | Descripción | Requiere |
|-----------|-------------|----------|
| Constancia de estudio | Certifica que el estudiante está matriculado | Matrícula activa |
| Constancia de estudio con calificaciones | Incluye notas del período o año | Calificaciones cerradas |
| Certificado de calificaciones | Detalle de notas de un año o período | Año académico cerrado o período cerrado |
| Paz y salvo académico | No tiene deudas de documentos ni libros | Revisión secretaría |
| Paz y salvo financiero | No tiene deudas de pagos | Revisión financiero |
| Paz y salvo general | Académico + Financiero + Convivencia | Todos los módulos |
| Historial académico | Todos los años cursados en el colegio | Matrículas históricas |
| Certificado de conducta | Comportamiento durante el año | Anotaciones de convivencia |
| Diploma de bachiller | Grado 11° aprobado | Decisión de grado aprobada |

**Proceso de solicitud:**
1. Padre/estudiante o secretaria crea solicitud.
2. Secretaria procesa: verifica paz y salvo, genera el PDF con plantilla oficial.
3. Cambia estado a LISTO.
4. Registra entrega física o envía por email.

**Libro de matrícula digital:**
- Listado oficial de todos los estudiantes matriculados en el año académico.
- Exportable en Excel y PDF.
- Con firma del rector para certificación oficial.

---

### E11. MÓDULO: FINANCIERO

**Responsable:** Financiero / Tesorero
**NestJS:** `src/financial/`

**Conceptos de cobro:**
- Se crean por año académico.
- Tipos: MATRICULA (una vez al año), PENSION (mensual, meses 1-10 o 1-12), OTROS (kit escolar, transporte, actividades).
- Las pensiones se pueden crear en masa para todos los meses del año.

**Gestión de pagos:**
- Registrar pago por estudiante y concepto.
- El saldo = monto cobrado - monto pagado.
- Los pagos parciales quedan en estado PAGO_PARCIAL.
- Las exoneraciones requieren motivo y autorización del rector.

**Estado de cuenta por estudiante:**
- Lista todos los conceptos del año con su estado (PENDIENTE, PAGADO, EN_MORA, EXONERADO).
- Saldo total pendiente.
- Botón de generar paz y salvo financiero (solo si saldo = 0 en todos los conceptos obligatorios).

**Reportes financieros:**
- Recaudo del mes (total cobrado vs total recibido).
- Lista de morosos (estudiantes con pagos vencidos).
- Proyección de ingresos anuales.
- Reporte por concepto.

---

### E12. MÓDULO: PSICOORIENTACIÓN

**Responsable:** Psicoorientador
**NestJS:** `src/counseling/`

**Funcionalidades:**
- Agenda de citas (programar, confirmar, cancelar).
- Historial de sesiones por estudiante (confidencial — solo el psicoorientador y el rector pueden ver).
- Registro de observaciones y seguimiento.
- Alertas de riesgo: el sistema cruza datos de calificaciones + asistencia + anotaciones de convivencia para identificar estudiantes en riesgo académico o psicosocial.
- Remisiones a profesionales externos (médico, psicólogo externo, defensoría, ICBF).

**Dashboard de alertas:**
- Estudiantes con 3 o más asignaturas en Bajo en el último período.
- Estudiantes con más del 20% de inasistencias.
- Estudiantes con 2 o más anotaciones negativas en el período.
- Cruces (bajo rendimiento + inasistencias + anotaciones).

---

### E13. MÓDULO: ANALYTICS Y REPORTES

**Responsable:** Rector / Coordinadores
**NestJS:** `src/analytics/`

**Reportes disponibles:**

**Académicos:**
- Promedio institucional por área y grado.
- Distribución de desempeño (Superior/Alto/Básico/Bajo) por grupo/grado/área.
- Evolución del promedio de un estudiante por períodos.
- Top de estudiantes por grupo/grado.
- Estudiantes en riesgo de reprobación.
- Tasa de reprobación histórica por grado.

**Asistencia:**
- % de asistencia por grupo.
- Listado de estudiantes con inasistencias críticas.
- Ausencias por día del mes (para detectar patrones).

**Matrícula:**
- Total de estudiantes por grado y grupo.
- Comparativo de matrícula año vs año.
- Tasa de deserción.
- Tasa de promoción.

**Financiero:**
- % de cartera recuperada.
- Morosidad por grado.

**Convivencia:**
- Número de anotaciones por tipo y nivel.
- Grupos con mayor frecuencia de anotaciones negativas.
- Evolución mensual de la convivencia institucional.

---

## F. API ENDPOINTS NESTJS

> Todos los endpoints requieren `Authorization: Bearer {jwt}` excepto los marcados con `[PÚBLICO]`.
> El `colegioId` se extrae siempre del JWT — nunca como parámetro de body para evitar manipulación.

### F1. Autenticación — `/auth`

```
POST /auth/login                  [PÚBLICO] Login usuario
POST /auth/refresh                Renovar accessToken con refreshToken
POST /auth/logout                 Invalidar refreshToken
POST /auth/forgot-password        [PÚBLICO] Solicitar reset de contraseña
POST /auth/reset-password         [PÚBLICO] Establecer nueva contraseña con token
GET  /auth/me                     Datos del usuario autenticado + roles en el colegio
```

### F2. Institución — `/institution`

```
GET  /institution                  Datos de la institución del usuario autenticado
PUT  /institution                  Actualizar datos institucionales [RECTOR]
GET  /institution/siee             Obtener configuración SIEE
PUT  /institution/siee             Actualizar configuración SIEE [RECTOR]
GET  /institution/academic-years   Listar años académicos
POST /institution/academic-years   Crear año académico [RECTOR]
PUT  /institution/academic-years/:id/activate  Activar año académico [RECTOR]
GET  /institution/periods          Listar períodos del año activo
POST /institution/periods          Crear período [RECTOR/COORD_AC]
PUT  /institution/periods/:id      Editar período [RECTOR/COORD_AC]
PUT  /institution/periods/:id/close Cerrar período [RECTOR/COORD_AC]
```

### F3. Estructura Académica — `/structure`

```
GET  /structure/grades             Listar grados del colegio
POST /structure/grades             Crear grado [RECTOR]
PUT  /structure/grades/:id         Editar grado [RECTOR]
GET  /structure/groups             Listar grupos (año activo, filtro por grado)
POST /structure/groups             Crear grupo [RECTOR/COORD_AC]
PUT  /structure/groups/:id         Editar grupo [RECTOR/COORD_AC]
GET  /structure/areas              Listar áreas
POST /structure/areas              Crear área [RECTOR/COORD_AC]
PUT  /structure/areas/:id          Editar área [RECTOR/COORD_AC]
GET  /structure/subjects           Listar asignaturas (filtro por área, grado)
POST /structure/subjects           Crear asignatura [RECTOR/COORD_AC]
PUT  /structure/subjects/:id       Editar asignatura [RECTOR/COORD_AC]
GET  /structure/grade-subjects/:gradeId  Asignaturas de un grado con intensidad
POST /structure/grade-subjects     Asignar asignatura a grado [RECTOR/COORD_AC]
PUT  /structure/grade-subjects/:id Editar intensidad [RECTOR/COORD_AC]
```

### F4. Personal / Docentes — `/staff`

```
GET  /staff                        Listar docentes del colegio [RECTOR/COORD_AC]
POST /staff                        Crear docente (usuario + perfil) [RECTOR]
GET  /staff/:id                    Detalle de docente
PUT  /staff/:id                    Editar docente [RECTOR]
PUT  /staff/:id/deactivate         Desactivar docente [RECTOR]
GET  /staff/:id/assignments        Asignaciones del docente en año activo
POST /staff/assignments            Crear asignación docente-grupo-asignatura [RECTOR/COORD_AC]
DELETE /staff/assignments/:id      Eliminar asignación [RECTOR/COORD_AC]
POST /staff/area-heads             Asignar jefe de área [RECTOR/COORD_AC]
DELETE /staff/area-heads/:id       Remover jefe de área [RECTOR/COORD_AC]
PUT  /staff/groups/:groupId/director  Asignar director de grupo [RECTOR/COORD_AC]
```

### F5. Estudiantes — `/students`

```
GET  /students                     Listar estudiantes (filtros: grado, grupo, estado)
GET  /students/:id                 Perfil completo del estudiante
PUT  /students/:id                 Editar datos del estudiante [RECTOR/SECRETARIA]
GET  /students/:id/grades          Calificaciones del estudiante (por año/período)
GET  /students/:id/annual-grades   Notas anuales y estado de promoción
GET  /students/:id/attendance      Asistencia del estudiante
GET  /students/:id/coexistence     Anotaciones de convivencia
GET  /students/:id/payments        Estado de pagos
GET  /students/:id/documents       Documentos en secretaría
GET  /students/me                  El propio estudiante ve su info [ESTUDIANTE]
```

### F6. Acudientes — `/parents`

```
POST /parents                      Crear acudiente [RECTOR/SECRETARIA]
GET  /parents/:id                  Perfil del acudiente
PUT  /parents/:id                  Editar acudiente [RECTOR/SECRETARIA]
POST /parents/:id/students         Vincular estudiante a acudiente [RECTOR/SECRETARIA]
DELETE /parents/:id/students/:studentId  Desvincular [RECTOR/SECRETARIA]
GET  /parents/me/students          Estudiantes del acudiente autenticado [PADRE]
```

### F7. Inscripciones — `/enrollment/inscriptions`

```
POST /enrollment/inscriptions      [PÚBLICO] Formulario de inscripción
GET  /enrollment/inscriptions      Listar inscripciones [RECTOR/SECRETARIA]
GET  /enrollment/inscriptions/:id  Detalle de inscripción [RECTOR/SECRETARIA]
PUT  /enrollment/inscriptions/:id/review   Cambiar estado [SECRETARIA]
PUT  /enrollment/inscriptions/:id/admit    Admitir [RECTOR/SECRETARIA]
PUT  /enrollment/inscriptions/:id/reject   Rechazar [RECTOR/SECRETARIA]
POST /enrollment/inscriptions/:id/convert  Convertir a matrícula [SECRETARIA]
```

### F8. Matrículas — `/enrollment/registrations`

```
GET  /enrollment/registrations              Listar matrículas año activo
POST /enrollment/registrations              Crear matrícula [SECRETARIA]
GET  /enrollment/registrations/:id          Detalle de matrícula
PUT  /enrollment/registrations/:id          Editar matrícula [SECRETARIA]
PUT  /enrollment/registrations/:id/withdraw Registrar retiro [SECRETARIA/RECTOR]
POST /enrollment/registrations/renew-bulk   Renovar en masa (promovidos) [SECRETARIA/RECTOR]
GET  /enrollment/registrations/book         Libro de matrícula (PDF) [SECRETARIA/RECTOR]
```

### F9. Logros — `/achievements`

```
GET  /achievements                  Listar logros (filtro: asignatura, grado, período)
POST /achievements                  Crear logro [RECTOR/COORD_AC/DOCENTE]
PUT  /achievements/:id              Editar logro
DELETE /achievements/:id            Eliminar logro
POST /achievements/:id/indicators   Agregar indicador al logro
PUT  /achievements/indicators/:id   Editar indicador
DELETE /achievements/indicators/:id Eliminar indicador
```

### F10. Calificaciones — `/grades`

```
GET  /grades                              Consultar calificaciones (filtros: grupo, asignatura, período)
POST /grades                              Registrar calificación [DOCENTE]
PUT  /grades/:id                          Editar calificación [DOCENTE] (solo si período abierto)
PUT  /grades/:id/leveling                 Registrar nivelación [DOCENTE/COORD_AC]
GET  /grades/group/:groupId/period/:periodId  Planilla de notas del grupo [DOCENTE/COORD_AC]
GET  /grades/student/:studentId           Historial de calificaciones del estudiante
POST /grades/bulk                         Guardar múltiples calificaciones en una petición [DOCENTE]
```

### F11. Notas Anuales y Habilitaciones — `/annual-grades`

```
GET  /annual-grades                       Ver notas anuales (filtro: grado, grupo, año)
POST /annual-grades/calculate/:groupId    Calcular notas anuales de un grupo [COORD_AC/RECTOR]
PUT  /annual-grades/:id/habilitacion      Registrar nota de habilitación [DOCENTE/COORD_AC]
GET  /annual-grades/promotion-report/:gradeId  Reporte de promoción por grado [COORD_AC/RECTOR]
```

### F12. Asistencia — `/attendance`

```
GET  /attendance                          Consultar asistencia (filtros: grupo, asignatura, fecha)
POST /attendance                          Registrar asistencia [DOCENTE/DIRECTOR_GRUPO]
POST /attendance/bulk                     Registrar asistencia de todo el grupo en una petición
PUT  /attendance/:id/justify              Justificar ausencia [COORD_AC/SECRETARIA]
GET  /attendance/student/:studentId       Resumen de asistencia del estudiante
GET  /attendance/group/:groupId/summary   Resumen por grupo (% de asistencia)
GET  /attendance/alerts                   Estudiantes en alerta por inasistencias [COORD_AC]
```

### F13. Horarios — `/schedule`

```
GET  /schedule/templates                  Listar plantillas de horario [COORD_AC]
POST /schedule/templates                  Crear plantilla de horario [COORD_AC]
GET  /schedule/templates/:id/slots        Franjas horarias de la plantilla
POST /schedule/templates/:id/slots        Agregar franja [COORD_AC]
GET  /schedule/classes                    Listar clases (filtro: grupo, docente, asignatura)
POST /schedule/classes                    Asignar clase (franja + grupo + asignatura + docente) [COORD_AC]
DELETE /schedule/classes/:id              Eliminar clase [COORD_AC]
GET  /schedule/group/:groupId             Horario completo de un grupo
GET  /schedule/teacher/:teacherId         Horario completo de un docente
GET  /schedule/conflicts                  Detectar conflictos [COORD_AC]
GET  /schedule/me                         Horario del usuario autenticado (docente/estudiante)
```

### F14. Convivencia — `/coexistence`

```
GET  /coexistence/annotations             Listar anotaciones (filtro: estudiante, tipo, nivel, fecha)
POST /coexistence/annotations             Crear anotación [DOCENTE/COORD_CONV/RECTOR]
PUT  /coexistence/annotations/:id         Editar anotación [COORD_CONV/RECTOR]
GET  /coexistence/annotations/:studentId  Historial de un estudiante
POST /coexistence/protocols               Crear protocolo Ley 1620 [COORD_CONV]
PUT  /coexistence/protocols/:id           Actualizar protocolo
GET  /coexistence/protocols               Listar protocolos activos [COORD_CONV/RECTOR]
POST /coexistence/committee               Registrar reunión del comité [COORD_CONV/RECTOR]
```

### F15. Boletines — `/reports`

```
GET  /reports/bulletin/:studentId/:periodId         Datos del boletín de un estudiante (JSON)
GET  /reports/bulletin/:studentId/:periodId/pdf     Boletín en PDF
GET  /reports/bulletin-annual/:studentId            Boletín anual
GET  /reports/bulletin-annual/:studentId/pdf        Boletín anual en PDF
GET  /reports/bulletin-group/:groupId/:periodId/pdf  Boletines de todo un grupo (ZIP de PDFs)
POST /reports/bulletin/publish/:groupId/:periodId   Publicar boletines del grupo [RECTOR/COORD_AC]
```

### F16. Comisión de Evaluación — `/commission`

```
GET  /commission                          Listar comisiones [RECTOR/COORD_AC]
POST /commission                          Crear comisión [RECTOR/COORD_AC]
PUT  /commission/:id                      Editar comisión
GET  /commission/:id/decisions            Decisiones de la comisión
POST /commission/:id/decisions            Registrar decisión por estudiante [RECTOR/COORD_AC]
PUT  /commission/:id/decisions/:decisionId Editar decisión
PUT  /commission/:id/close                Cerrar comisión (sube acta)
```

### F17. Secretaría — `/secretary`

```
GET  /secretary/requests                  Listar solicitudes de documentos
POST /secretary/requests                  Crear solicitud
GET  /secretary/requests/:id              Detalle de solicitud
PUT  /secretary/requests/:id/process      Procesar solicitud [SECRETARIA]
GET  /secretary/requests/:id/document     Generar/descargar el documento PDF
PUT  /secretary/requests/:id/deliver      Registrar entrega [SECRETARIA]
GET  /secretary/enrollment-book           Libro de matrícula oficial [SECRETARIA/RECTOR]
```

### F18. Financiero — `/financial`

```
GET  /financial/concepts                  Listar conceptos de cobro del año activo
POST /financial/concepts                  Crear concepto [FINANCIERO/RECTOR]
PUT  /financial/concepts/:id              Editar concepto
POST /financial/concepts/bulk-pensions    Crear pensiones masivas para el año [FINANCIERO/RECTOR]
GET  /financial/payments                  Listar pagos (filtros: estudiante, concepto, estado)
POST /financial/payments                  Registrar pago [FINANCIERO]
PUT  /financial/payments/:id              Editar pago [FINANCIERO/RECTOR]
GET  /financial/student/:studentId        Estado de cuenta del estudiante
GET  /financial/student/:studentId/paz-y-salvo  Verificar paz y salvo financiero
GET  /financial/reports/monthly           Reporte mensual de recaudo [FINANCIERO/RECTOR]
GET  /financial/reports/debtors           Listado de morosos [FINANCIERO/RECTOR]
```

### F19. Psicoorientación — `/counseling`

```
GET  /counseling/appointments             Citas del psicoorientador autenticado
POST /counseling/appointments             Crear cita [PSICOORIENTADOR]
PUT  /counseling/appointments/:id         Editar cita
GET  /counseling/student/:studentId       Historial del estudiante [PSICOORIENTADOR/RECTOR]
GET  /counseling/alerts                   Estudiantes en riesgo (dashboard)
```

### F20. Comunicaciones — `/communications`

```
GET  /communications/circulars            Listar circulares (filtro por destinatario)
POST /communications/circulars            Crear circular [RECTOR/COORD/DIRECTOR_GRUPO]
PUT  /communications/circulars/:id        Editar circular
DELETE /communications/circulars/:id      Eliminar circular
GET  /communications/circulars/me         Circulares para el usuario autenticado
```

### F21. Analytics — `/analytics`

```
GET  /analytics/academic-summary          Resumen académico institucional [RECTOR/COORD_AC]
GET  /analytics/grade-distribution        Distribución de desempeño por grado/área
GET  /analytics/at-risk-students          Estudiantes en riesgo
GET  /analytics/attendance-summary        Resumen de asistencia
GET  /analytics/enrollment-stats          Estadísticas de matrícula
GET  /analytics/financial-summary         Resumen financiero [RECTOR/FINANCIERO]
GET  /analytics/coexistence-stats         Estadísticas de convivencia [RECTOR/COORD_CONV]
```

---

## G. PANTALLAS Y VISTAS

### G1. Next.js — Web (Admin/Docente)

#### Dashboard por rol

| Rol | KPIs mostrados |
|-----|----------------|
| Rector | Matrícula total, % asistencia institucional, promedio académico, alertas activas, estado financiero |
| Coordinador Académico | Períodos con notas pendientes, grupos sin cerrar, estudiantes en riesgo académico |
| Coordinador Convivencia | Protocolos abiertos, anotaciones del mes, estudiantes con historial crítico |
| Secretaría | Solicitudes de documentos pendientes, matrículas incompletas, documentos faltantes |
| Financiero | Recaudo del mes, % de cartera, lista de morosos del mes |
| Docente | Mis clases de hoy, asistencia pendiente de registrar, período activo con notas faltantes |

#### Pantallas clave

**Estructura → Grupos:** Tabla con columnas: Grado, Grupo, Jornada, Director de Grupo, # Estudiantes, % Cupo ocupado, Acciones.

**Matrícula → Nueva Matrícula:** Wizard de 3 pasos: (1) Seleccionar estudiante o crear nuevo, (2) Asignar al grupo, (3) Documentos y confirmar.

**Calificaciones → Planilla del docente:** Tabla donde filas = estudiantes, columnas = Ser / Saber / Hacer / Definitiva / Desempeño. Celdas editables inline. Botón "Guardar todo".

**Boletines → Generador:** Seleccionar grado/grupo + período. Preview del boletín. Botones: "Ver individual", "Descargar grupo (ZIP)", "Publicar para padres".

**Convivencia → Nueva Anotación:** Formulario: buscar estudiante, tipo, nivel, descripción, fecha, medida pedagógica. Si es GRAVE/GRAVÍSIMA → checkbox "Activar Protocolo Ley 1620".

**Financiero → Estado de cuenta:** Por estudiante, tabla de conceptos del año con semáforo (verde=pagado, amarillo=parcial, rojo=pendiente/mora). Total adeudado.

---

### G2. Flutter — Mobile (Docente, Estudiante, Padre)

#### Docente (Mobile)

```
HOME: Mis clases de hoy (tarjetas por hora con asignatura y grupo)
ASISTENCIA: Lista de estudiantes → marcar PRESENTE/AUSENTE/TARDANZA
CALIFICACIONES: Seleccionar período → planilla editable por asignatura
COMUNICACIONES: Circulares institucionales + botón de nueva anotación
PERFIL: Datos del usuario, configuración
```

#### Estudiante (Mobile)

```
HOME: Resumen del período activo (áreas, promedio, faltas)
MIS NOTAS: Por período → tabla de áreas y calificaciones con desempeño colorido
HORARIO: Vista semanal de clases
ASISTENCIA: Mi asistencia por asignatura (gráfico de barras)
COMUNICACIONES: Circulares, avisos
PERFIL: Datos personales
```

#### Padre/Acudiente (Mobile)

```
HOME: Resumen del hijo (o selector de hijos si tiene varios)
CALIFICACIONES: Notas por período con comparativo visual
BOLETÍN: Descargar boletín en PDF
ASISTENCIA: Faltas del mes (calendario visual con días marcados)
PAGOS: Estado de cuenta, pensiones al día o vencidas
COMUNICACIONES: Circulares y mensajes de la institución
PERFIL: Mis datos y datos del acudido
```

---

## H. INSTRUCCIONES PARA AGENTE DE CÓDIGO

### H1. Reglas Maestras (OBLIGATORIAS — nunca violar)

```
REGLA 1: NUNCA hardcodear IDs, nombres de colegios, emails, contraseñas, ni ningún dato de tenant.
REGLA 2: NUNCA inventar modelos, campos o relaciones de Prisma. Toda entidad se basa en este documento.
REGLA 3: NUNCA usar prisma migrate dev. Usar SIEMPRE prisma db push.
REGLA 4: NUNCA crear lógica de negocio que contradiga el Decreto 1290, Ley 115, Ley 1620.
REGLA 5: NUNCA omitir el colegioId en los where de Prisma. Aislamiento de tenant es sagrado.
REGLA 6: NUNCA implementar más de lo que está en el plan del checkpoint. Si hay ambigüedad, PREGUNTAR.
REGLA 7: SIEMPRE usar class-validator en los DTOs. NUNCA confiar en que el frontend envía datos correctos.
REGLA 8: SIEMPRE manejar errores con HttpException y códigos HTTP apropiados.
REGLA 9: NUNCA exponer el passwordHash en ningún response.
REGLA 10: SIEMPRE verificar que el rol del usuario tiene permiso para la acción solicitada (Guards).
```

### H2. Fase 0 — Auditoría y Discovery (ejecutar PRIMERO)

```
ANTES DE ESCRIBIR UNA SOLA LÍNEA DE CÓDIGO:

[ ] Lee package.json del backend, web y mobile para confirmar versiones exactas de dependencias.
[ ] Lee prisma/schema.prisma actual y lista TODO lo que ya existe vs. lo que falta.
[ ] Lee todos los archivos de src/ del backend y construye un mapa de módulos existentes.
[ ] Lee todas las páginas de app/ del frontend y construye un mapa de rutas existentes.
[ ] Lee lib/features/ del Flutter y construye un mapa de features existentes.
[ ] Identifica CONFLICTOS entre el código existente y este documento.
[ ] Genera un reporte de: (a) qué está implementado y es correcto, (b) qué está implementado pero incorrecto, (c) qué falta completamente.
[ ] PRESENTA EL REPORTE y ESPERA APROBACIÓN antes de continuar.
```

### H3. Fase 1 — Modelo de Datos

**Solo después de aprobación del reporte de Fase 0.**

```
CHECKLIST FASE 1:
[ ] Agrega todos los enums faltantes al schema.prisma.
[ ] Agrega todos los modelos faltantes al schema.prisma.
[ ] Verifica que las relaciones (1:N, N:M) están correctamente declaradas con @relation.
[ ] Verifica índices compuestos (@@unique, @@index) en modelos de alta consulta.
[ ] Ejecuta: prisma db push
[ ] Verifica que no haya errores de validación del schema.
[ ] Ejecuta: prisma generate
[ ] PRESENTA EL SCHEMA FINAL y ESPERA APROBACIÓN antes de continuar.
```

### H4. Fase 2 — Backend (NestJS por módulos)

**Orden de implementación (respetar dependencias):**

```
2.1  [ ] Auth module (login, JWT, refresh, guards)
2.2  [ ] Institution module (colegio, años académicos, períodos, SIEE)
2.3  [ ] Academic structure module (grados, grupos, áreas, asignaturas)
2.4  [ ] Users module (usuarios, personas, roles)
2.5  [ ] Staff module (docentes, asignaciones, jefes de área)
2.6  [ ] Students module (perfil estudiante, documentos)
2.7  [ ] Parents module (acudientes, relaciones)
2.8  [ ] Enrollment module (inscripciones, matrículas)
2.9  [ ] Achievements module (logros e indicadores)
2.10 [ ] Grades module (calificaciones por período)
2.11 [ ] Annual grades module (notas anuales, habilitaciones, promoción)
2.12 [ ] Attendance module (asistencia por clase y diaria)
2.13 [ ] Schedule module (horarios y franjas)
2.14 [ ] Coexistence module (convivencia, protocolos)
2.15 [ ] Secretary module (documentos, solicitudes)
2.16 [ ] Financial module (conceptos, pagos)
2.17 [ ] Counseling module (psicoorientación)
2.18 [ ] Commission module (comisión de evaluación)
2.19 [ ] Reports module (boletines PDF)
2.20 [ ] Communications module (circulares)
2.21 [ ] Analytics module (reportes y estadísticas)

CHECKPOINT después de cada módulo:
  → Prueba el endpoint con Swagger o curl.
  → Verifica que el TenantGuard rechaza colegioId incorrecto.
  → Verifica que el RoleGuard rechaza roles no autorizados.
  → Presenta el módulo implementado antes de pasar al siguiente.
```

**Estructura interna de cada módulo:**
```
modules/
└── nombre-modulo/
    ├── nombre-modulo.module.ts
    ├── nombre-modulo.controller.ts
    ├── nombre-modulo.service.ts
    ├── dto/
    │   ├── create-nombre.dto.ts
    │   ├── update-nombre.dto.ts
    │   └── filter-nombre.dto.ts
    └── entities/
        └── nombre.entity.ts    (solo si es necesario mapear)
```

### H5. Fase 3 — Frontend Next.js

**Orden de implementación:**
```
3.1  [ ] Layout base (sidebar con navegación por rol, header, breadcrumb)
3.2  [ ] Auth (login page, middleware de protección de rutas por rol)
3.3  [ ] Dashboard diferenciado por rol
3.4  [ ] Estructura académica (grados, grupos, áreas, asignaturas)
3.5  [ ] Gestión de personal (docentes, asignaciones)
3.6  [ ] Estudiantes (listado, perfil, ficha)
3.7  [ ] Inscripciones y matrículas (formulario público + gestión interna)
3.8  [ ] Horarios (constructor de horario)
3.9  [ ] Calificaciones (planilla de notas por docente)
3.10 [ ] Asistencia (registro por clase)
3.11 [ ] Boletines (generador y visor PDF)
3.12 [ ] Convivencia (anotaciones, protocolos)
3.13 [ ] Secretaría (solicitudes de documentos)
3.14 [ ] Financiero (estado de cuenta, pagos)
3.15 [ ] Psicoorientación (citas, alertas)
3.16 [ ] Analytics (tablero de reportes)

CHECKPOINT después de cada sección:
  → La página carga sin errores en la consola.
  → Los datos provienen de la API real (no hardcodeados).
  → Los componentes son responsivos.
  → Los roles incorrectos son redirigidos.
```

### H6. Fase 4 — Mobile Flutter

**Orden de implementación:**
```
4.1  [ ] Infraestructura (tema Material 3, go_router, Dio con interceptors JWT)
4.2  [ ] Auth (pantalla de login)
4.3  [ ] Dashboard diferenciado por rol (docente/estudiante/padre)
4.4  [ ] Asistencia (flujo de registro para docente)
4.5  [ ] Calificaciones (vista de notas para estudiante/padre; ingreso para docente)
4.6  [ ] Horario (vista semanal)
4.7  [ ] Boletín digital (ver y descargar PDF)
4.8  [ ] Comunicaciones (circulares)
4.9  [ ] Pagos (estado de cuenta para padre)
4.10 [ ] Convivencia (nueva anotación para docente; ver historial para padre)

CHECKPOINT después de cada feature:
  → La pantalla navega correctamente con go_router.
  → El estado se maneja con Riverpod (sin setState global).
  → El loading state es visible mientras carga la API.
  → Los errores de red muestran mensaje al usuario.
```

### H7. Convenciones de Código que DEBES Seguir

**NestJS:**
```typescript
// Guards: SIEMPRE en el orden correcto
@UseGuards(JwtAuthGuard, TenantGuard, RolesGuard)
@Roles(Rol.RECTOR, Rol.COORD_ACADEMICO)
@Controller('structure')

// Servicios: SIEMPRE extraer colegioId del request, nunca del body
async create(colegioId: string, dto: CreateAreaDto) {
  return this.prisma.area.create({
    data: { ...dto, colegioId }
  });
}

// DTOs: SIEMPRE con validación
export class CreateAreaDto {
  @IsString()
  @IsNotEmpty()
  @MaxLength(100)
  nombre: string;

  @IsEnum(TipoArea)
  tipo: TipoArea;
}
```

**Prisma queries:**
```typescript
// SIEMPRE incluir colegioId
const areas = await this.prisma.area.findMany({
  where: { colegioId, activo: true },
  include: { asignaturas: true },
  orderBy: { orden: 'asc' }
});

// NUNCA así (sin colegioId):
const areas = await this.prisma.area.findMany(); // ❌ PROHIBIDO
```

**Next.js:**
```typescript
// SIEMPRE usar React Query para datos del servidor
const { data: students, isLoading } = useQuery({
  queryKey: ['students', { gradoId, grupoId }],
  queryFn: () => studentsApi.list({ gradoId, grupoId })
});

// SIEMPRE manejar el estado de loading y error
if (isLoading) return <DataTableSkeleton />;
if (error) return <ErrorState message={error.message} />;
```

**Flutter:**
```dart
// SIEMPRE usar Riverpod providers
final attendanceProvider = StateNotifierProvider<AttendanceNotifier, AttendanceState>(
  (ref) => AttendanceNotifier(ref.read(attendanceRepositoryProvider))
);

// SIEMPRE manejar estados: loading, data, error
return attendanceState.when(
  loading: () => const CircularProgressIndicator(),
  data: (records) => AttendanceList(records: records),
  error: (e, _) => ErrorWidget(message: e.toString()),
);
```

### H8. Validaciones de Negocio Críticas a Implementar

```
CALIFICACIONES:
✓ No se puede ingresar nota fuera del rango [notaMinima, notaMaxima] del SIEE.
✓ Solo el docente asignado puede ingresar notas de esa asignatura/grupo.
✓ No se puede modificar notas de períodos cerrados (sin rol RECTOR o COORD_AC).
✓ Los porcentajes de criterios deben sumar 100.
✓ La nota definitiva se calcula automáticamente al guardar, nunca se ingresa manual.

ASISTENCIA:
✓ No se puede registrar asistencia con fecha futura.
✓ No se puede registrar asistencia en días no hábiles (sin override de rector).
✓ Un registro de asistencia por (estudiante, asignatura, fecha) es único.

MATRÍCULA:
✓ Un estudiante no puede tener dos matrículas activas en el mismo año académico.
✓ El grupo no puede superar el cupoMaximo.
✓ Solo se puede matricular si el año académico está activo.

INSCRIPCIONES:
✓ Un aspirante no puede inscribirse dos veces en el mismo año (por tipo+número de documento).

HORARIO:
✓ Un docente no puede tener dos clases a la misma hora en el mismo día.
✓ Un grupo no puede tener dos clases a la misma hora en el mismo día.
✓ El total de horas semanales de una asignatura en un grupo no puede superar la intensidad definida en GradoAsignatura.

PROMOCIÓN:
✓ La decisión de REPROBADO solo puede ser modificada por el RECTOR.
✓ Una vez cerrado el año académico, no se puede cambiar el resultado (solo con override RECTOR y log de auditoría).
```

### H9. Seed de Datos Iniciales al Crear un Colegio

Al crear un nuevo colegio, el sistema debe ejecutar automáticamente:

```typescript
async seedNewColegio(colegioId: string) {
  // 1. Grados estándar según niveles seleccionados
  await this.createDefaultGrades(colegioId, nivelesActivos);

  // 2. Áreas obligatorias de la Ley 115
  await this.createMandatoryAreas(colegioId);

  // 3. Asignaturas base por área y su intensidad horaria sugerida
  await this.createDefaultSubjects(colegioId);

  // 4. Configuración SIEE por defecto (modificable por el rector)
  await this.createDefaultSIEE(colegioId);

  // 5. Escala de valoración por defecto
  await this.createDefaultEscala(colegioId);
}

// Escala por defecto:
// Superior: 4.6 – 5.0
// Alto:     4.0 – 4.5
// Básico:   3.0 – 3.9
// Bajo:     1.0 – 2.9
```

---

## APÉNDICE A — GLOSARIO

| Término | Significado |
|---------|-------------|
| SIEE | Sistema Institucional de Evaluación del Estudiante (Decreto 1290) |
| DANE | Departamento Administrativo Nacional de Estadística — asigna código a cada IE |
| IE | Institución Educativa |
| PEI | Proyecto Educativo Institucional |
| DBA | Derechos Básicos de Aprendizaje (guía curricular del MEN) |
| MEN | Ministerio de Educación Nacional |
| Comisión de E&P | Comisión de Evaluación y Promoción (reunión al final de cada período y del año) |
| Nivelación | Actividad de refuerzo durante el período para estudiantes en Bajo |
| Habilitación | Prueba extraordinaria al final del año para aprobar áreas en Bajo |
| Director de grupo | Docente responsable de un grupo (antes "tutor" o "titular") |
| Escalafón | Sistema de clasificación de docentes del Estado (Decreto 2277 o 1278) |
| Paz y salvo | Documento que certifica que no se tienen deudas (académicas, financieras, de materiales) |
| Constancia de estudio | Documento que certifica que el estudiante está matriculado |
| Personero estudiantil | Representante elegido por estudiantes de grado 9° a 11° |

---

## APÉNDICE B — DOCUMENTOS REQUERIDOS PARA MATRÍCULA

### Preescolar (Transición, Jardín, Pre-jardín)
- Registro civil de nacimiento (original o fotocopia auténticada)
- Carnet de vacunas al día (PAI)
- Foto del estudiante (3x4)
- Fotocopia del documento del acudiente
- Carnet de afiliación a EPS o Sisbén

### Primaria (1° – 5°)
- Registro civil o Tarjeta de Identidad
- Boletín de calificaciones del año anterior (o certificado de aprobación del grado anterior)
- Foto del estudiante (3x4)
- Fotocopia del documento del acudiente
- Carnet de afiliación a EPS o Sisbén

### Secundaria y Media (6° – 11°)
- Tarjeta de Identidad o Cédula de Ciudadanía (mayores de 18)
- Boletín o certificado de calificaciones del grado anterior aprobado
- Foto del estudiante (3x4)
- Fotocopia del documento del acudiente
- Carnet de EPS o Sisbén
- Certificado médico (si tiene condición especial o discapacidad)

---

## APÉNDICE C — INTENSIDAD HORARIA SUGERIDA POR ASIGNATURA

(Según Decreto 1850 y Resolución 2343 — ajustable por institución)

| Asignatura | Primaria (h/sem) | Secundaria (h/sem) | Media (h/sem) |
|-----------|-----------------|-------------------|---------------|
| Matemáticas | 5 | 5 | 4 |
| Lengua Castellana | 5 | 4 | 4 |
| Inglés | 3 | 4 | 5 |
| Ciencias Naturales | 4 | 4 | 4 |
| Ciencias Sociales | 4 | 4 | 3 |
| Ed. Física | 2 | 2 | 2 |
| Ed. Artística | 2 | 2 | 2 |
| Ed. Ética | 1 | 1 | 1 |
| Ed. Religiosa | 1 | 1 | 1 |
| Tecnología e Informática | 2 | 2 | 2 |
| Filosofía | — | — | 3 |

---

## APÉNDICE D — FLUJO DE ESTADO DE MATRÍCULA

```
INSCRIPCION_PENDIENTE
    ↓ (secretaria revisa)
INSCRIPCION_EN_REVISION
    ↓ (admite)              ↓ (rechaza)
INSCRIPCION_ADMITIDO      INSCRIPCION_RECHAZADA
    ↓ (crea matrícula)
MATRICULA_ACTIVA
    ↓ (retiro)              ↓ (fin de año promovido)   ↓ (fin de año reprobado)
MATRICULA_RETIRADA         MATRICULA_FINALIZADA        MATRICULA_FINALIZADA
                            _PROMOVIDO                  _REPROBADO
                                ↓                           ↓
                        [Renovación año siguiente]   [Renovación mismo grado]
```

---

## APÉNDICE E — CÁLCULO DE NOTAS (ALGORITMOS)

```
NOTA DEFINITIVA DEL PERÍODO:
notaDef = (notaSer * porcentajeSer/100) 
        + (notaSaber * porcentajeSaber/100) 
        + (notaHacer * porcentajeHacer/100)

DESEMPEÑO DEL PERÍODO:
        ⎧ SUPERIOR  si notaDef >= siee.escalaSuperior.min
        ⎪ ALTO      si notaDef >= siee.escalaAlto.min
desempD =⎨ BASICO    si notaDef >= siee.escalaBasico.min
        ⎩ BAJO      si notaDef < siee.escalaBasico.min

NOTA ANUAL:
notaAnual = Σ(notaDefinitivaPeriodoN * porcentajePeriodoN / 100)  para N en [1..4]

NOTA DEFINITIVA ANUAL (sin habilitación):
  = notaAnual

NOTA DEFINITIVA ANUAL (con habilitación, siee.promediarHabilitacion = false):
  = notaHabilitacion

NOTA DEFINITIVA ANUAL (con habilitación, siee.promediarHabilitacion = true):
  = (notaAnual + notaHabilitacion) / 2

ESTADO DE PROMOCIÓN:
  areasEnBajo = count(notasAnuales where desempenoDefinitivo = BAJO)
  
  SI areasEnBajo = 0
    → PROMOVIDO
  SI areasEnBajo <= siee.maxAreasHabilitacion
    → EN_HABILITACION (pendiente de habilitaciones)
  SI areasEnBajo > siee.maxAreasHabilitacion
    → REPROBADO (sin derecho a habilitación)
    
  DESPUÉS DE HABILITACIONES:
  areasEnBajoFinal = count(notasAnuales where aprobada = false)
  SI areasEnBajoFinal <= siee.maxAreasParaPromocion
    → PROMOVIDO
  SINO
    → REPROBADO
```

---

*Documento generado para uso interno de desarrollo. Versión 1.0.*
*Marco legal vigente a 2025 en Colombia. Verificar actualizaciones del MEN periódicamente.*
