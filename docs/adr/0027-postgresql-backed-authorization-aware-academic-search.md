# ADR 0027: PostgreSQL-backed authorization-aware academic search

- Estado: aceptada
- Fecha: 2026-07-31
- Responsables: plataforma académica

## Contexto

La plataforma necesita búsqueda en releases asignados y autoría institucional
sin filtrar borradores, organizaciones, respuestas ni claves. PostgreSQL 18 ya
es la autoridad y ofrece full-text search, GIN y `pg_trgm`.

## Decisión

`domain.discovery` posee generaciones, documentos y jobs de índice. Cada
organización tiene como máximo una generación `building` y una `active`; el
rebuild crea una sombra y cambia el puntero atómicamente. El indexado incremental
consume eventos durables y usa digest para no-op.

`SearchDocument` guarda texto plano cerrado por source type, `SearchVectorField`
con pesos A/B/C y título normalizado. Se usan GIN para FTS y `gin_trgm_ops` sólo
sobre el título normalizado. La consulta usa `websearch_to_tsquery`, rank y
similarity con orden determinista. `ts_headline` sólo produce tokens de control;
el frontend crea segmentos y `<mark>` sin HTML crudo.

La autorización se aplica antes del ranking: learner limita release IDs por
matrícula efectiva y publicación activa; authoring exige capability por tipo;
toda consulta está acotada por organización y generación. Las queries crudas no
se persisten ni entran a logs, Sentry o labels.

## Alternativas rechazadas

Elasticsearch, OpenSearch y Meilisearch se aplazan: duplican infraestructura y
no mejoran el límite de autorización actual. `unaccent` en queries amplias se
rechaza por scans; la normalización NFKC/accent folding se materializa sólo para
trigram. Vector search, embeddings, RAG y analytics personales quedan fuera.

## Consecuencias

PostgreSQL soporta el volumen inicial con operación única y consistencia
transaccional. El costo de reindex y p95 debe medirse; una migración futura a un
motor externo conservará el contrato de generaciones y autorización.
