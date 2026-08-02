# ADR 0017: Organization-scoped role-based access control

**Estado:** aceptada — 2026-07-29.

## Decisión

`identity` conserva exclusivamente la identidad global. La nueva aplicación
`organizations` posee organizaciones, membresías UUID, asignaciones históricas
de roles y eventos. Los seis roles (`owner`, `administrator`, `author`,
`reviewer`, `instructor`, `learner`) se asignan a una membresía, pueden
combinarse y se traducen mediante una matriz explícita de capacidades en código;
no hay nivel numérico ni herencia implícita.

Las lecturas parten de querysets filtrados por membresía activa y las escrituras
atraviesan servicios transaccionales que bloquean la organización y las filas
afectadas. La última asignación activa de owner no puede revocarse, suspenderse
ni terminarse; el bloqueo común de organización conserva esa invariante frente
a solicitudes concurrentes. Los eventos y asignaciones se preservan como
historia; no hay borrado físico por API.

> **Nota de vigencia:** ADR 0034 y ADR 0038 reemplazan el supuesto histórico
> de bypass de superuser. `is_staff` e `is_superuser` no conceden capacidades
> institucionales ni membresía implícita. El operador de plataforma conserva
> únicamente superficies globales explícitas; Django admin es de lectura para
> los hechos institucionales y el alta inicial reutiliza el servicio.

La URL representa el contexto institucional en Next.js. El navegador no guarda
organización, roles ni capacidades; los Server Components vuelven a consultar
Django sin caché y la API vuelve a autorizar cada solicitud.

## Alternativas rechazadas y evolución

Se rechazan `Group`, permisos dinámicos, django-guardian, paquetes RBAC,
booleanos en `User`, roles jerárquicos, JWT y un selector autoritativo en el
navegador: todos difuminarían el límite de tenant o permitirían privilegios
globales accidentales. Una futura evolución podrá agregar grants o auditoría
transversal mediante un ADR y migraciones nuevas, sin alterar `identity.0001`.
