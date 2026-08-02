# ADR 0039: Private invitation onboarding and role-first workspaces

- Estado: aceptada
- Fecha: 2026-08-02
- Responsables: plataforma académica
- Amplía: ADR 0030, ADR 0037 y ADR 0038

## Contexto

La política global de registro se estaba usando para dos decisiones distintas:
permitir el alta pública y completar una invitación institucional. Cuando el
registro público estaba cerrado, la activación validaba correctamente el token
pero enviaba a `/auth/registro`, cuya página devolvía 404. Esto dejaba
instituciones pendientes imposibles de activar.

La navegación también mantenía cuatro accesos redundantes en todos los roles:
Inicio, Mi perfil, Buscar y Resumen institucional. `/estudiar` y la raíz de una
organización eran portadas intermedias sin una tarea propia.

Para entregabilidad se consultó el 2026-08-02 la documentación oficial de Resend
sobre verificación de dominios, SPF, DKIM, DMARC y diagnósticos de entrega:
https://resend.com/docs/dashboard/domains/introduction,
https://resend.com/docs/dashboard/domains/dmarc y
https://resend.com/docs/dashboard/emails/deliverability-insights.

## Decisión

- La política global controla únicamente el autoservicio público. Una invitación
  institucional vigente conserva su canal privado incluso cuando el alta
  pública está cerrada.
- El bearer token se intercambia una sola vez por estado de sesión rotado. La
  ruta `/invitaciones/crear-cuenta` exige ese estado en servidor y no recibe ni
  vuelve a exponer el token.
- El alta invitada queda vinculada al correo de la invitación tanto en la UI
  como en el adaptador de django-allauth. Un correo sustituido, una sesión sin
  invitación, una invitación vencida o revocada se deniegan por defecto.
- La organización permanece `pending_activation` y sin owner hasta que el correo
  se verifica y la invitación se acepta. Sólo entonces se crea la membresía y se
  activa la institución.
- El sidebar no contiene Inicio, Mi perfil, Buscar ni Resumen institucional. La
  institución y los roles ocupan su cabecera; perfil y preferencias permanecen
  en el menú de cuenta; buscar y notificaciones son acciones del header.
- La navegación institucional sigue dependencias de trabajo, no el orden
  histórico de módulos técnicos: preparación institucional, diseño académico y
  ejecución con grupos y matrículas. Un hijo que conduce al mismo destino que
  su padre no se muestra de nuevo.
- El menú de cuenta incorpora `Ayuda y guía de uso` inmediatamente antes de
  cerrar sesión. La ayuda explica la secuencia completa, las diferencias entre
  conceptos y un caso verificable; conserva todos los pasos, pero sólo enlaza
  acciones autorizadas por las capacidades del usuario.
- La autoría de estructura representa cada `CourseActivity` una sola vez. La
  lección contiene allí mismo estado, alineación, versión y acceso al contenido;
  no se vuelve a listar como una unidad paralela. El orden mixto usa el contrato
  canónico `/activities/order/`.
- `/estudiar` y la raíz compatible de organización redirigen al trabajo
  principal existente: owner a Personas, administrator a Grupos de curso,
  instructor a Mis asignaturas, author/reviewer a Cursos y learner a Mi
  aprendizaje. La raíz compatible no renderiza una portada.
- El plano global de instituciones nunca ofrece una entrada al tenant. Sólo
  muestra estado e invitaciones de bootstrap.
- Los correos transaccionales directos usan remitente alineado, Message-ID del
  dominio configurado, texto y HTML, idempotencia y cabeceras anti-respuesta
  automática. La ubicación en bandeja de entrada no se declara verificada sin
  revisar los encabezados recibidos y los diagnósticos del proveedor.

## Consecuencias

Cerrar el alta pública ya no rompe la incorporación delegada. La diferencia
entre una invitación y un formulario público se valida en el backend y no en un
parámetro de URL. Las rutas históricas siguen siendo compatibles mediante
redirección, pero dejan de producir pantallas redundantes.

El sidebar se convierte en una guía progresiva para administradores sin alterar
la navegación prioritaria de docentes o estudiantes. La ayuda es una superficie
de conocimiento, no una fuente paralela de permisos: las acciones continúan
fallando de forma segura en servidor y sus enlaces se derivan del contexto de
acceso vigente.

La entregabilidad continúa dependiendo de reputación, contenido, autenticación
observada por el receptor y política del buzón. El código puede garantizar
alineación y trazabilidad, no prometer que Gmail u otro proveedor nunca
clasificará un mensaje como spam.

## Alternativas rechazadas

- Abrir temporalmente el registro global: permitiría altas no invitadas.
- Confiar en `?invitation=1` o conservar el token en la URL: crea un bypass
  manipulable y aumenta la exposición del bearer secret.
- Ocultar el campo de correo sólo en React: una solicitud directa podría crear
  otra identidad.
- Conservar portadas vacías por uniformidad: añade pasos y navegación sin una
  tarea de usuario.
