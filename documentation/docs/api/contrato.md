# Uso del contrato

## Paginación, filtros y errores

El esquema generado declara los parámetros disponibles en cada operación. No presuponga paginación, filtros, límites o códigos no presentes en él: cada dominio expone sólo los filtros permitidos después de limitar la visibilidad por organización y alcance.

Una respuesta de conflicto suele llevar un código de dominio, como `revision_conflict` o `content_version_conflict`. No debe resolverse con reintento ciego: lea la versión actual, conserve el trabajo local y aplique una nueva intención explícita.

## Ejemplos de cliente

El navegador no consume la API con un token. Para verificar una sesión local desde una terminal, primero autentíquese con el flujo de la aplicación y use una cookie de prueba que no se publique ni se guarde en scripts. Para integraciones de servidor, siga el esquema y las políticas de autorización del dominio; no hay una API pública de claves estáticas documentada.

```typescript
// El cliente generado se mantiene en apps/web/src/lib/api/generated/.
// Las llamadas del navegador pasan por el mismo origen de Next.js y CSRF.
await fetch('/api/v1/organizaciones/', {
  credentials: 'include',
  headers: { Accept: 'application/json' },
});
```

```python
# En código Django interno, use servicios del dominio. No llame la propia API
# HTTP para reemplazar reglas transaccionales o políticas.
from domain.organizations import services
```

El segundo ejemplo es deliberadamente interno: los servicios de dominio son la fuente de reglas y la API es un borde de transporte.
