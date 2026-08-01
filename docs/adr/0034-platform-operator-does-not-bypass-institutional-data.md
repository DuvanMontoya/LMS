# ADR 0034: Platform operators do not bypass institutional data boundaries

- Estado: aceptada
- Fecha: 2026-08-01
- Responsables: plataforma académica
- Modifica: ADR 0017; precisa ADR 0026, ADR 0027 y ADR 0028

## Contexto

`is_superuser` identifica al operador de la plataforma: puede gobernar la
política global de registro y aprovisionar instituciones. No representa una
membresía de cada institución. La auditoría de 2026-08-01 encontró que algunas
APIs operacionales listaban eventos, trabajos de búsqueda o entregas de correo
de todas las instituciones cuando el actor era superuser, aunque éste no
participara en ellas.

Eso mezcla administración de plataforma con acceso al contenido operativo de
un tenant y contradice el aislamiento ya aplicado a miembros, cursos, contenido
académico y entrega de aprendizaje.

## Decisión

Las lecturas y mutaciones institucionales exigen siempre una membresía activa
y la capability de esa membresía. `is_staff` e `is_superuser` no agregan una
membresía implícita ni amplían los querysets de eventos, búsqueda, correo,
contenido, cursos, evaluaciones, recursos o aprendizaje.

El superadministrador conserva únicamente superficies globales explícitas y
sin datos institucionales: configuración global de registro y directorio / alta
de instituciones. Al aprovisionar una institución, el propietario elegido
recibe una membresía real y auditable; el operador no la recibe de manera
automática.

Una futura necesidad legítima de soporte transversal deberá introducir un grant
temporal, de alcance institucional, con justificación, caducidad y auditoría.
No se implementa como bypass de `is_superuser`.

## Consecuencias

- Los endpoints operacionales filtran organizaciones mediante el mismo helper
  de membership/capability que las demás superficies institucionales.
- Un superadministrador sin membresía obtiene colecciones vacías y recursos
  ajenos como 404, sin revelar existencia ni metadatos.
- Las pruebas de aislamiento cubren índices de búsqueda, eventos y entregas de
  correo además de miembros y contenido.
