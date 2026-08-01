# ADR 0028: Internal notifications and asynchronous transactional email

- Estado: aceptada
- Fecha: 2026-07-31
- Responsables: plataforma académica

## Contexto

Los hechos académicos necesitan avisos internos y correo transaccional sin
enviar SMTP dentro de una transacción, duplicar entregas ni exponer identidad o
grading material.

## Decisión

`domain.notifications` posee `Notification`, preferencias, `EmailDelivery` y
su historial append-only. El router consume eventos con handlers explícitos,
resuelve recipients desde IDs mínimos, aplica defaults en código y crea inbox y
email durable de forma idempotente. SMTP ocurre en Celery después del commit y
recibe sólo el UUID de delivery.

Notification almacena texto plano y URL relativa allowlisted. Email se renderiza
desde templates español text/plain y text/html sin recursos remotos, tracking,
scripts, respuestas ni claves. El destinatario durable se identifica mediante
HMAC-SHA256 operacional; la API nunca lo expone. Eventos obligatorios conservan
in-app aun con opt-out. No hay DELETE, cambio de recipient ni reenvío arbitrario.

## Alternativas rechazadas

Email síncrono, señales, marketing, Web Push, Service Workers, WebSockets, SMS,
WhatsApp, Slack, Teams, digests y Celery Beat quedan fuera. `List-Unsubscribe`
no se simula para correo estrictamente transaccional.

## Consecuencias

El producto gana inbox, estado leído, preferencias, retry y dead-letter, a
cambio de operar una cola y plantillas versionadas. El fan-out mayor a 10.000
se rechaza hasta diseñar un job durable específico.
