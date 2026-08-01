# Envío transaccional con Resend SMTP

Estado local al 2026-08-01: `papyros.pro` aparece `verified` en Resend. En
Hostinger existen DKIM, SPF, MX de `send` y DMARC; los registros web existentes
no fueron reemplazados. Django autenticó correctamente mediante STARTTLS en
`smtp.resend.com:587`; todavía no se ha transmitido un correo real.

## Configuración privada local

Conservar el modo de archivos mientras no se quiera transmitir correo. La clave
mostrada como `re_...` en el panel no se puede recuperar después de crearla.
Una clave de envío nueva o recién creada debe existir únicamente en
`infrastructure/local/.env` (archivo ignorado):

```env
EMAIL_DELIVERY_MODE=smtp
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=re_REEMPLAZAR_LOCALMENTE
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_TIMEOUT=15
DEFAULT_FROM_EMAIL=Plataforma Académica <cuentas@papyros.pro>
EMAIL_MESSAGE_ID_DOMAIN=papyros.pro
```

Reiniciar sólo el entorno local y ejecutar:

```powershell
pnpm dev:restart
pnpm notifications:email-smoke
```

`notifications:email-smoke` fuerza SMTP únicamente para ese proceso, negocia
STARTTLS y autentica contra Resend. No envía mensajes ni necesita un destinatario.
Un correo real se envía después, con un destinatario de prueba autorizado, para
comprobar recepción y no sólo transporte.

Tras obtener autorización explícita del destinatario:

```powershell
pwsh -NoProfile -File scripts/notifications.ps1 `
  -Action EmailSendSmoke `
  -Recipient persona@dominio.com
```

El comando exige internamente `--confirm`, rechaza backends distintos de SMTP y
transmite una sola alternativa texto/HTML con idempotencia de Resend.

La contraseña SMTP nunca se coloca en Next.js, Git, OpenAPI, navegador o base de
datos. En desarrollo, `EMAIL_DELIVERY_MODE=file` sigue siendo el valor seguro por
defecto. En producción se configura después, en el gestor de secretos elegido
por el despliegue; este runbook no autoriza ni realiza un despliegue.

Las notificaciones asíncronas usan `EmailDelivery` y Celery. Los correos de
invitación usan Django SMTP con texto y HTML, remitente explícito e idempotencia
de Resend. Los flujos de registro y recuperación siguen siendo propiedad de
django-allauth; no se introdujo un token de activación paralelo.
