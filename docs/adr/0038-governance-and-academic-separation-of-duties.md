# ADR 0038: Governance and academic separation of duties

- Estado: aceptada
- Fecha: 2026-08-02
- Responsables: plataforma académica
- Amplía: ADR 0017, ADR 0034 y ADR 0037

## Contexto

La matriz histórica convertía `owner` y `administrator` en agregados de casi
todas las capacidades. Además, algunos servicios decidían autoridad consultando
directamente esos códigos de rol. Ese diseño confundía propiedad institucional
con competencia académica: una persona propietaria podía publicar, programar,
ver intentos o modificar calificaciones sin una responsabilidad docente.

El 2026-08-02 se consultaron el modelo RBAC y la separación de funciones de
NIST, que distinguen asignación de usuarios a roles, asignación de permisos a
roles y restricciones estáticas/dinámicas:
https://csrc.nist.gov/Projects/role-based-access-control/faqs y
https://csrc.nist.gov/glossary/term/separation_of_duty. También se consultó la
guía de autorización de OWASP, que exige mínimo privilegio, denegación por
defecto y validación de permisos en cada solicitud:
https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html.

## Decisión

- `owner` representa únicamente gobierno institucional: continuidad de la
  propiedad, personas, roles, políticas de membresía, sesiones administradas e
  integraciones. No recibe capacidades de currículo, cursos, publicación,
  grupos, agenda, clases, evaluaciones, resultados ni calificaciones.
- Una membresía `owner` es exclusiva y no puede combinarse con roles
  académicos. La transferencia de propiedad reemplaza atómicamente los roles de
  la membresía destino por `{owner}`; no agrega `owner` a una función previa.
- `administrator` opera la institución: currículo, releases aprobados,
  matrículas, grupos, agenda, entregas de evaluación y lectura institucional de
  resultados. No crea o aprueba contenido y no califica, recalifica ni altera
  gradebooks.
- `author` crea y envía contenido. `reviewer` revisa y aprueba. Ambos roles son
  incompatibles en una misma membresía para conservar el control maker-checker.
- `instructor` recibe operación docente y calificación sólo dentro de sus
  responsabilidades de asignatura, excepciones de curso y asignaciones activas
  a grupos. El rol por sí solo no amplía el alcance a toda la organización.
- `learner` sólo actúa sobre su aprendizaje, sesiones y evaluaciones asignadas.
- Toda autorización de dominio depende de `Capability` y de alcance objetivo;
  ningún servicio concede acceso académico por comparar directamente
  `RoleCode.OWNER` o `RoleCode.ADMINISTRATOR`.
- El sidebar y los guards de Next reflejan las capacidades efectivas, pero no
  son la barrera de seguridad. La API valida cada solicitud y usa 404 para
  recursos fuera de alcance cuando revelar su existencia produciría IDOR.
- El superadministrador de plataforma no recibe membresía ni capacidades de un
  tenant. En desarrollo puede sincronizarse desde variables locales ignoradas,
  siempre que conserve cero membresías.

## Matriz resumida

| Rol | Puede | No puede |
| --- | --- | --- |
| `owner` | Gobierno, personas, roles, configuración, integraciones | Currículo, cursos, clases, evaluaciones, resultados, notas |
| `administrator` | Operación institucional, grupos, matrículas, agenda, entregas, lectura de resultados | Autoría, aprobación académica, calificación, recalificación |
| `author` | Crear y enviar contenido y evaluaciones | Aprobar su trabajo, operar grupos, ver notas |
| `reviewer` | Revisar y aprobar contenido y evaluaciones | Crear como autor, operar grupos, calificar |
| `instructor` | Cursos/grupos asignados, clases, entregas y calificación de su alcance | Autoría institucional, otros grupos o cursos |
| `learner` | Su aprendizaje, calendario, clases y evaluaciones asignadas | Datos institucionales o de otras personas |

## Consecuencias

Ser dueño deja de equivaler a ser superusuario académico. Si una organización
necesita que una misma persona ejerza otra función, debe existir otra identidad
operativa gobernada y auditable; no se obtiene autoridad académica por
propiedad. Los fixtures y comandos locales deben crear actores separados para
gobierno, operación, autoría, revisión, docencia y aprendizaje.

La navegación será más corta por rol y las pruebas antiguas que usaban `owner`
como comodín deben migrar al actor competente. Esta adaptación no autoriza
reescribir historia académica ni relajar las restricciones de organización,
periodo, grupo, release o matrícula.

## Alternativas rechazadas

- Ocultar enlaces y conservar permisos backend amplios: deja rutas directas e
  IDOR funcionales.
- Mantener `owner` omnipotente con una advertencia visual: no aplica mínimo
  privilegio ni separación de funciones.
- Permitir `author + reviewer`: permite que una persona apruebe su propio
  trabajo.
- Dar al administrador capacidad de calificar: mezcla operación de tenant con
  juicio académico y permite alterar el registro sin responsabilidad docente.
