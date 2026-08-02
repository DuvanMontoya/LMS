# Envío transaccional con Resend SMTP

Estado revisado al 2026-08-02: DNS público responde con DKIM en
`resend._domainkey.papyros.pro`, SPF y MX en `send.papyros.pro`, y DMARC
`v=DMARC1; p=none;`. `papyros.pro` aparecía `verified` en Resend en la revisión
local anterior. Django autenticó correctamente mediante STARTTLS en
`smtp.resend.com:587` y ya se observaron mensajes en el buzón, algunos
clasificados como spam. La autenticación DNS es necesaria, pero no prueba por sí
sola la colocación en bandeja.

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

Cuando un mensaje llegue a spam, el siguiente diagnóstico obligatorio es abrir
el original recibido y comprobar `Authentication-Results` (`spf`, `dkim` y
`dmarc`), alineación de `From`/`Return-Path`, Message-ID y cualquier causa que
muestre Deliverability Insights de Resend. Para correos sensibles de acceso se
mantiene deshabilitado el tracking de enlaces; habilitarlo no forma parte de
este runbook.

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
