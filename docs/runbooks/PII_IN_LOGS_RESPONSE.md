# Respuesta ante PII en logs

## Síntomas
Email, cookie, password, search query, grading payload o signed URL aparece en logs/Sentry.

## Impacto
Incidente de privacidad con posible exposición de credenciales o datos académicos.

## Diagnóstico
Detén la expansión, identifica fuente, ventana, destinos y acceso sin copiar el valor.

## Comandos seguros
Desactiva el export afectado, ejecuta pruebas de redaction y preserva hashes/IDs seguros.

## Mitigación
Revoca credenciales/URLs si aplica y corrige el scrubber en origen y destino.

## Recuperación
Aplica retención/borrado conforme al proveedor y política institucional autorizada.

## Verificación
Pruebas nested, email, password, query, grading y signed URL pasan sin fuga.

## Escalamiento
Escala inmediatamente a seguridad, privacidad y responsables operativos.

## Qué no hacer
No pegues PII en tickets, chat, commits ni nuevas trazas de diagnóstico.
