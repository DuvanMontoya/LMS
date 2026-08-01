# ADR 0026: Transactional outbox and versioned domain events

- Estado: aceptada
- Fecha: 2026-07-31
- Responsables: plataforma académica

## Contexto

Publicación, learning, assessments y assets ya conservan hechos históricos
propios, pero las proyecciones transversales no pueden depender de señales,
llamadas posteriores al commit ni payloads enviados directamente a Redis.
Search y notifications necesitan una fuente durable, correlacionable e
idempotente sin convertir el monolito modular en event sourcing.

## Decisión

`domain.events` posee `DomainEvent`, `EventConsumerDelivery` y
`EventReplayRequest`. `record_domain_event()` valida un schema cerrado, escribe
evento y deliveries en la misma transacción de negocio y registra el dispatch
con `transaction.on_commit`. Celery recibe sólo el UUID del evento. PostgreSQL
es la autoridad; Redis sólo transporta IDs.

Los nombres siguen `<domain>.<aggregate>.<action>.v<schema>`. Los payloads
contienen IDs mínimos, nunca respuestas, grading payload, credenciales, URLs
firmadas ni cuerpos de correo. `DomainEvent` es append-only y un trigger bloquea
UPDATE/DELETE. Cada delivery tiene lease, intentos, backoff, estado terminal y
unicidad por evento/consumer. Replay exige capacidad, razón, organización,
consumer registrado y un máximo de 100.000 eventos; no muta el evento.

Los dominios de negocio sólo importan el contrato público de events. Events no
importa discovery ni notifications. Los consumidores se registran desde las
apps consumidoras y deben ser idempotentes.

## Alternativas rechazadas

- Señales Django: ocultan el límite transaccional y el orden de efectos.
- Publicar directamente a Celery: puede adelantar al commit y perder el hecho.
- Kafka, Debezium, CDC y event sourcing: añaden operación y semántica que esta
  fase no necesita.
- Replay global automático: riesgo de duplicación y fan-out no acotado.

## Consecuencias

El registro del hecho aumenta escrituras en PostgreSQL y exige retención y
runbooks. A cambio, dispatch, retry, dead-letter, replay, correlación y auditoría
son observables y reproducibles sin alterar los agregados históricos existentes.
