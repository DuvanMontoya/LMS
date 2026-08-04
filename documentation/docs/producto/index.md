# Producto, usuarios y reglas

## Límite institucional

Una persona tiene una identidad global, pero sus permisos pertenecen a una membresía activa de una organización. La organización, las asignaciones de rol y la historia de cambios pertenecen a `domain.organizations`; no se copian a `User`, grupos genéricos ni almacenamiento del navegador.

| Rol | Propósito y facultad principal | Límite relevante |
| --- | --- | --- |
| Propietario | Gobierno institucional, miembros, invitaciones e integraciones. | No hereda acceso académico. |
| Administrador | Opera currículo, períodos, grupos, matrículas, releases y operación académica. | No crea o aprueba autoría ni califica por defecto. |
| Autor | Crea y envía cursos, contenido, bancos, preguntas y evaluaciones. | No aprueba su propio trabajo. |
| Revisor | Revisa y aprueba autoría académica. | No edita como autor. |
| Docente | Opera sus grupos, clases, entregas y calificaciones de alcance asignado. | No entra a cursos o grupos fuera de su responsabilidad. |
| Estudiante | Consulta su aprendizaje, calendario, clases y evaluaciones asignadas. | No ve recursos internos ni resultados ajenos. |
| Operador de plataforma | Configura registro global y aprovisiona instituciones. | No obtiene membresía ni acceso a tenants automáticamente. |

Las políticas de código son autoritativas. Una respuesta `404` a un recurso de otra organización evita revelar su existencia; la ausencia de un enlace visible tampoco sustituye esa comprobación del servidor.

## Conceptos académicos

| Concepto | Significado |
| --- | --- |
| Asignatura | Saber curricular estable con temas, conceptos, objetivos y prerrequisitos. |
| Curso | Experiencia de aprendizaje con estructura y revisión; se alinea a una asignatura. |
| Release | Snapshot completo e inmutable de un curso aprobado. |
| Cohorte o sección | Ejecución de un release dentro de una ventana y una institución. |
| Matrícula | Vínculo individual que fija un release para el estudiante. |
| Intento | Evidencia del estudiante frente a una evaluación asignada; las respuestas y calificaciones se versionan. |

## Reglas de negocio comprobables

- Una revisión aprobada no está publicada: publicación crea un `CourseRelease` con hash y cadena de integridad.
- Publicar no matrícula estudiantes. Sólo una matrícula efectiva permite leer el release asignado.
- Las posiciones de módulos y unidades activos son contiguas; las escrituras usan bloqueo y `expected_version` para rechazar conflictos con `409`.
- El contenido de unidades es JSON semántico versionado, nunca HTML como fuente canónica. El guardado es explícito y concurrente.
- Los recursos pasan por cuarentena y procesamiento antes de `READY`; las URL firmadas y claves de S3 no entran a contenido ni releases.
- Las claves, tolerancias de respuesta, semillas y material de calificación de evaluaciones no se exponen al estudiante.

Fuentes: `apps/api/domain/*`, `docs/architecture/DOMAIN_MODULES.md`, ADR 0017–0044 y pruebas de cada dominio.
