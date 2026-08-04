# ADR 0043: MediaCMS LTI 1.3 release-pinned video delivery

**Estado:** aceptada para desarrollo local; producción condicionada a HTTPS y
registro de cliente propios.

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
3. `domain.publishing` copia el binding al release schema v5. El release es la
   fuente de verdad de la reproducción; cambiar la unidad después de publicar
   no modifica matrículas existentes.
4. `domain.learning` emite un descriptor de lanzamiento de vida corta sólo tras
   validar la matrícula efectiva. El descriptor no es parte del snapshot. El
   endpoint de autorización comprueba de nuevo el usuario autenticado y firma
   un `id_token` RS256 con claims LTI mínimos, contexto del release y recurso
   ligado. MediaCMS valida la firma mediante JWKS y controla su propia sesión,
   RBAC y entrega de media.
5. El adaptador local de URL de MediaCMS conserva en la sesión LTI el único
   `media_friendly_token` que llegó en el `id_token` ya verificado. El endpoint
   de embed rechaza cualquier token distinto, exige la pertenencia al grupo
   del contexto `release + unit` y sólo entonces asocia el medio privado a esa
   categoría y crea la permisión MediaCMS normal. No se habilita un catálogo
   público ni se acepta que pertenecer a otro grupo LTI autorice un vídeo.
6. Los secretos y claves privadas se suministran por variables de entorno. En
   desarrollo, una clave efímera existe únicamente durante el proceso Django;
   la configuración de producción falla cerrada si no se entrega una clave
   RSA, issuer HTTPS y orígenes HTTPS válidos.

## Consecuencias

- La interfaz de autoría permite registrar y sustituir el código de MediaCMS
  después de cargar/procesar el vídeo. La selección profunda de MediaCMS queda
  como mejora posterior: no se simula con una URL pública.
- El reproductor se carga en un iframe LTI con `referrerPolicy=no-referrer` y
  sandbox mínimo de reproducción. La unidad puede mantener un documento
  académico semántico alrededor del vídeo.
- MediaCMS 8.1.3 materializa `MediaPermission` después de un lanzamiento LTI.
  En local, los segmentos siguen requiriendo la sesión privada de MediaCMS y
  Nginx consulta su autorización. En producción falta un contrato de
  revocación/sincronización de esas permisiones cuando se suspenda, revoque o
  cambie una matrícula; no se declara cerrada esa garantía hasta diseñarlo y
  probarlo.
- La prueba local usa `localhost` de extremo a extremo. No constituye evidencia
  de despliegue productivo: antes de producción se exige TLS real, clave RSA
  persistente protegida, issuer/JWKS públicos y registro del cliente en
  MediaCMS bajo el dominio definitivo.
