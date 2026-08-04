# ADR 0043: MediaCMS LTI 1.3 release-pinned video delivery

**Estado:** aceptada para desarrollo local; el despliegue productivo sigue
condicionado a su TLS, dominio y registro de cliente definitivos.

## Contexto

Una `CourseUnit` de modalidad `mediacms_video` ya identifica una decisión de
autoría, pero un enlace directo a MediaCMS permitiría ver un vídeo sin que la
LMS comprobara la matrícula, el release asignado ni el estado de acceso. Copiar
la cookie de MediaCMS al navegador de la LMS, exponer HLS, o guardar URLs
firmadas en contenido o snapshots sería igualmente incorrecto.

MediaCMS 8.1.3 incorpora LTI 1.3. Su flujo OIDC valida el JWT de la plataforma,
provisiona el usuario y otorga la permisión sobre el recurso dentro de su
contexto LTI. La consulta oficial del repositorio y release se realizó el
2026-08-03.

## Decisión

1. `domain.courses` posee una `MediaCMSVideoBinding` uno-a-uno con la unidad.
   Sólo conserva `media_friendly_token`, el identificador opaco estable de
   MediaCMS; no contiene URL, cookie, clave, objeto S3 ni URL HLS.
2. El cambio de binding usa la misma versión optimista de la revisión y sólo
   está disponible para una revisión editable, para autores con responsabilidad
   académica. Una unidad de vídeo sin binding bloquea el readiness.
3. `domain.publishing` copia el binding al `delivery` discriminado del release
   schema v6. El release es la
   fuente de verdad de la reproducción; cambiar la unidad después de publicar
   no modifica matrículas existentes.
4. `domain.learning` emite un descriptor de lanzamiento de vida corta sólo tras
   validar la matrícula efectiva. El descriptor no es parte del snapshot. El
   endpoint de autorización comprueba de nuevo el usuario autenticado y firma
   un `id_token` RS256 con claims LTI mínimos, contexto del release y recurso
   ligado. MediaCMS valida la firma mediante JWKS y controla su propia sesión,
   RBAC y entrega de media.
5. El adaptador local de URL de MediaCMS conserva en Redis, con vida limitada y
   ligado a la sesión LTI actual, el `media_friendly_token` y la capacidad que
   llegaron en el `id_token` ya verificado. El endpoint de embed rechaza
   cualquier token distinto, exige la pertenencia al grupo del contexto
   `release + unit` y sólo entonces asocia el medio privado a esa categoría y
   crea la permisión MediaCMS normal. No se habilita un catálogo público ni se
   acepta que pertenecer a otro grupo LTI autorice un vídeo.
6. Cada `id_token` lleva además una credencial RS256 de uso exclusivo
   `mediacms_media_access`, limitada a `user + enrollment + release + unit +
   media_friendly_token`. No contiene cookies, claves de MediaCMS ni URLs de
   archivos; MediaCMS la conserva sólo en su cache de servidor. El adaptador
   la elimina de los registros de lanzamiento antes de persistirlos y
   `mediacms:up` sanea los registros locales heredados.
7. Antes de cada source, encoded file o segmento HLS protegido, el endpoint
   interno de autorización de MediaCMS presenta esa credencial al endpoint LMS
   `lti/media-access/`. El LMS verifica firma, expiración, usuario, matrícula
   efectiva, release vigente y el vídeo exacto del snapshot. La respuesta
   positiva no se cachea; cualquier fallo de red o de validación deniega el
   archivo. Al denegar, el adaptador elimina la `MediaPermission` LTI y la
   membresía RBAC del contexto que habían quedado materializadas en MediaCMS;
   cada nuevo lanzamiento válido invalida una denegación cacheada de MediaCMS,
   y la revocación invalida el mismo registro de autorización.
8. La clave privada local se genera una sola vez bajo `.local/mediacms/`, que
   está ignorado por Git, y sobrevive reinicios de Django. Producción no tiene
   fallback: arranque falla si faltan la clave PEM RSA de al menos 2048 bits,
   los tres orígenes HTTPS (LMS, MediaCMS y validación) o si la clave no puede
   cargarse.
9. Para evitar que un desfase pequeño entre los relojes del LMS y de la
   herramienta rechace un `id_token` recién emitido, el claim `iat` se emite
   hasta cinco segundos antes del reloj de la LMS. `exp` continúa calculándose
   desde el instante real de emisión: el margen reduce la vida útil efectiva,
   no amplía ninguna autorización. El valor es configurable sólo entre 0 y 60
   segundos mediante `LMS_LTI_TOKEN_CLOCK_SKEW_SECONDS`.

## Consecuencias

- La interfaz de autoría permite registrar y sustituir el código de MediaCMS
  después de cargar/procesar el vídeo. La selección profunda de MediaCMS queda
  como mejora posterior: no se simula con una URL pública.
- El reproductor se carga en un iframe LTI con `referrerPolicy=no-referrer` y
  sandbox mínimo de reproducción. La unidad de vídeo no puede contener ni
  mostrar un documento académico, texto adicional ni otro recurso de entrega.
- MediaCMS 8.1.3 todavía materializa `MediaPermission` después de un
  lanzamiento LTI, pero ya no es la autoridad suficiente para servir bytes:
  la compuerta llama al LMS antes de cada acceso protegido. Una suspensión,
  revocación o cambio de release revoca el acceso a partir de la siguiente
  petición de media. Bytes ya entregados al buffer del navegador no pueden
  retirarse retrospectivamente.
- La prueba local usa `localhost` de extremo a extremo. No constituye evidencia
  de despliegue productivo: antes de producción se exige TLS real, clave RSA
  persistente protegida en el gestor de secretos, issuer/JWKS públicos,
  endpoint de validación HTTPS y registro del cliente en MediaCMS bajo el
  dominio definitivo. Esta tarea no modifica DNS, VPS ni certificados porque
  el alcance solicitado continúa siendo local.
