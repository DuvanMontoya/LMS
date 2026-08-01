# ADR 0033: Colombian member profiles and cross-course academic groups

Fecha: 2026-08-01  
Estado: Aceptada

## Contexto

La identidad mínima, las membresías institucionales, las cohortes ligadas a un
release y las matrículas ya existen. El registro necesita datos operativos para
Colombia y la institución necesita agrupar estudiantes, docentes y acompañantes
como promociones o grados, sin copiar roles a `User` ni convertir una cohorte de
curso en un grupo institucional reutilizable.

## Decisión

- `identity.User` conserva exclusivamente identidad, credenciales y estado de
  autenticación. No recibe campos demográficos ni roles académicos.
- `domain.organizations.OrganizationMemberProfile` conserva nombres, WhatsApp,
  nacimiento, documento, género, contexto educativo, ubicación, estrato y motivo
  de registro dentro de la organización. La edad se calcula; no se persiste.
- La sugerencia RC/TI/CC depende de la edad, pero el operador puede escoger un
  documento extranjero. Los valores heredados `student` y `Estudiante` se
  normalizan a `learner` para preservar contratos existentes.
- `domain.learning.AcademicGroup` representa una agrupación institucional por
  año, nivel y sección. Su roster relaciona membresías existentes con un único
  papel de estudiante, docente o acompañante y conserva las bajas. El roster se
  reemplaza completo en una sola transacción para impedir asignaciones parciales.
- `LearningCohort` puede apuntar a un grupo académico, pero continúa fijando un
  curso, un release y una ventana de acceso. Un grupo puede vincular varias
  cohortes; no concede acceso por sí solo.
- Toda activación manual exige capacidad administrativa, cuenta administrada
  pendiente, contraseña válida y confirmación expresa de verificación de
  identidad. La operación activa usuario, verifica email, crea membresía y deja
  auditoría transaccional.

## Consecuencias

Se evita una segunda identidad, un sistema de roles paralelo y la duplicación de
matrículas. Los datos de perfil son PII administrativa y no deben entrar en
eventos, búsqueda pública, snapshots, LiveKit ni analítica. La organización debe
definir retención y acceso antes de producción. La creación de cohortes expone el
grupo como vínculo opcional y aclara que dicho vínculo no matricula personas.
