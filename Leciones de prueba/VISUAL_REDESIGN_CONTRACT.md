# VISUAL_REDESIGN_CONTRACT.md

## Propósito

Este documento es el contrato operativo del rediseño visual. Codex debe usarlo como fuente de verdad para no caer en cambios superficiales.

La tarea no es “mejorar un poco la UI”. La tarea es ejecutar una intervención completa de UX/UI y diseño visual sobre una app Flutter ya funcional.

---

## Diagnóstico inicial esperado

Antes de editar código, debes producir un diagnóstico real en `codex/REDESIGN_PROGRESS.md` con esta estructura:

```md
# REDESIGN_PROGRESS.md

## Estado inicial
- Fecha/hora:
- Ruta del proyecto Flutter:
- Rama Git actual:
- Resultado de git status:
- Dispositivo Android detectado:

## Pantallas detectadas
| Pantalla | Archivo(s) | Rol funcional | Deuda visual | Prioridad |

## Componentes detectados
| Componente | Archivo | Uso | Problema visual | Acción sugerida |

## Sistema visual actual
- Theme:
- Colores:
- Tipografía:
- Espaciado:
- Cards:
- Inputs:
- Botones:
- Estados:

## Riesgos funcionales
- Archivos que NO se deben tocar:
- Flujos críticos:

## Plan de intervención visual
1.
2.
3.
```

Si no puedes crear o actualizar este archivo, explica por qué antes de modificar código.

---

## Principio de intervención

Piensa como diseñador de producto, no como programador que maquilla widgets.

Cada pantalla debe responder:

1. ¿Qué debe entender el usuario en los primeros tres segundos?
2. ¿Cuál es la acción principal?
3. ¿Qué información sobra, confunde o parece técnica?
4. ¿La jerarquía visual guía el ojo naturalmente?
5. ¿El espacio respira?
6. ¿Los componentes se sienten nativos de móvil?
7. ¿La pantalla se ve coherente con las demás?
8. ¿Se ve como producto terminado?

---

## Sistema de diseño mínimo obligatorio

Crea o consolida una capa compartida para diseño. Usa los nombres que mejor encajen con el proyecto existente, pero el sistema debe cubrir al menos:

### 1. Tokens

- Colores base.
- Colores semánticos: success, warning, error, info.
- Superficies.
- Bordes.
- Texto principal/secundario/terciario.
- Espaciados.
- Radios.
- Elevaciones.
- Duraciones de animación.

### 2. Theme

- `ThemeData` centralizado.
- `ColorScheme` coherente.
- `TextTheme` claro.
- `InputDecorationTheme`.
- `ElevatedButtonThemeData`.
- `FilledButtonThemeData`, si aplica.
- `OutlinedButtonThemeData`.
- `TextButtonThemeData`.
- `CardTheme`.
- `AppBarTheme`.
- `SnackBarThemeData`.
- `DialogTheme`.
- `BottomNavigationBarThemeData` o equivalente, si aplica.

### 3. Componentes UI base

Crea o mejora componentes reutilizables, según necesidad real:

- App scaffold o screen container.
- Page header.
- Section header.
- Primary button.
- Secondary button.
- Destructive button.
- App text field.
- App card.
- Info card.
- Evaluation card, si existe ese dominio.
- Status chip.
- Empty state.
- Error state.
- Loading state.
- Success/result state.
- Confirm dialog.

No dupliques visualmente el mismo patrón en muchas pantallas.

---

## Pantallas que deben revisarse

Codex debe identificar la estructura real del proyecto. Si existen pantallas parecidas a estas, deben rediseñarse:

### Login / autenticación

Objetivo: limpio, confiable, minimalista, nativo.

Requisitos:

- Eliminar textos técnicos innecesarios para usuario final.
- Reducir ruido visual.
- Hacer evidente la acción principal.
- Inputs limpios.
- Botón principal claro.
- Mensajes de error humanos.
- Si hay configuración técnica como host/IP/base URL, no debe invadir la experiencia principal del estudiante. Debe estar en una zona secundaria, avanzada o ajustes, sin romper funcionalidad.

### Home / dashboard

Objetivo: orientar al usuario rápidamente.

Requisitos:

- Jerarquía clara.
- Resumen útil.
- Acciones principales visibles.
- Cards limpias.
- Nada de saturación.
- Nada de datos crudos sin contexto.

### Lista de evaluaciones

Objetivo: que el estudiante entienda qué puede hacer.

Requisitos:

- Cards modernas.
- Estados de disponibilidad claros.
- Fechas, intentos, progreso o estado visualmente ordenados si existen.
- Empty state útil.
- Loading elegante.
- Errores comprensibles.

### Detalle de evaluación

Objetivo: preparar al usuario antes de iniciar.

Requisitos:

- Información organizada.
- Acción principal clara.
- Restricciones visibles sin lenguaje técnico.
- Advertencias limpias.
- No saturar con metadatos internos.

### Pantalla de pregunta / intento

Objetivo: concentración y claridad.

Requisitos:

- Progreso visible.
- Pregunta legible.
- Opciones cómodas táctilmente.
- Selección visual clara.
- Navegación obvia.
- Cronómetro, si existe, sobrio y no invasivo.
- Evitar ruido visual.
- Cuidar espacios verticales en celulares pequeños.

### Revisión / resumen antes de finalizar

Objetivo: confianza antes de enviar.

Requisitos:

- Resumen claro.
- Estados respondida/no respondida visibles.
- Acción final destacada.
- Confirmación seria y humana.

### Resultado

Objetivo: feedback claro y profesional.

Requisitos:

- Resultado destacado visualmente.
- Aprobado/no aprobado o estado equivalente claro.
- Detalles ordenados.
- Acciones siguientes claras.
- Diseño motivador, no frío.

### Ajustes / perfil / diagnóstico

Objetivo: separar lo técnico de lo cotidiano.

Requisitos:

- Lo técnico debe estar en sección secundaria.
- No mostrar información innecesaria al usuario final salvo que sea indispensable.
- Diseño limpio y sobrio.

---

## Estados visuales obligatorios

No olvides los estados. Una app premium no solo se ve bien cuando hay datos perfectos.

Revisar y mejorar:

- Loading.
- Empty.
- Error.
- Offline o conexión fallida, si existe.
- Unauthorized/session expired.
- Disabled.
- Success.
- Warning.
- Confirmación destructiva.

Cada estado debe tener:

- Icono o señal visual sobria.
- Título claro.
- Mensaje humano.
- Acción sugerida cuando aplique.
- Diseño consistente.

---

## Microcopy

Puedes mejorar textos visibles siempre que no cambies el significado funcional.

Principios:

- Usuario final primero.
- Menos lenguaje técnico.
- Frases cortas.
- Claridad.
- Tono profesional y humano.
- Nada de explicar arquitectura interna.

Ejemplos de mala dirección:

- “Tu sesión se valida en servidor”.
- “Ingresa el host asignado”.
- “Endpoint base”.
- “Error 401”.
- “Payload inválido”.

Dirección deseada:

- “No pudimos iniciar sesión. Revisa tus datos e inténtalo de nuevo.”
- “No hay evaluaciones disponibles por ahora.”
- “Tu sesión expiró. Vuelve a iniciar sesión.”
- “Revisa tu conexión e inténtalo nuevamente.”

---

## Validación visual real

No basta con que el código compile. Debe verse bien en pantalla real.

Si hay Android real por USB:

1. Detecta el dispositivo.
2. Ejecuta la app.
3. Captura pantallas principales.
4. Guarda evidencias.
5. Evalúa con checklist.
6. Itera.

Carpeta esperada:

```text
artifacts/ui-redesign/screenshots/
```

Nombres sugeridos:

```text
01-login.png
02-home.png
03-evaluations-list.png
04-evaluation-detail.png
05-question.png
06-review.png
07-result.png
08-error-state.png
09-empty-state.png
```

Si no puedes navegar automáticamente a cada pantalla, pide al usuario solo la navegación manual mínima o documenta qué capturas sí pudiste obtener. No uses esa dificultad como excusa para terminar superficialmente.

---

## Criterio “no superficial”

Antes de terminar, revisa el diff.

Debe haber evidencia de intervención real en al menos estas capas:

1. Sistema visual o theme.
2. Componentes reutilizables.
3. Pantallas principales.
4. Estados visuales.
5. Validación técnica.
6. Validación visual en dispositivo real o bloqueo documentado.

Si solo modificaste `theme.dart`, no es suficiente.

Si solo modificaste login, no es suficiente.

Si no creaste o consolidaste componentes compartidos y la app tiene UI repetida, no es suficiente.

Si no corriste validaciones, no es suficiente.

Si no revisaste capturas o dispositivo real cuando estaba disponible, no es suficiente.

---

## Modo de avance

Trabaja en ciclos:

```text
Auditar → Diseñar sistema → Implementar lote → Validar → Capturar → Evaluar → Corregir → Repetir
```

Después de cada ciclo importante, actualiza `codex/REDESIGN_PROGRESS.md`:

```md
## Ciclo N
- Cambios realizados:
- Pantallas afectadas:
- Archivos modificados:
- Validaciones:
- Capturas:
- Puntaje checklist:
- Qué sigue:
```

---

## Prohibición de cierre prematuro

No digas “terminado” si:

- No identificaste todas las pantallas principales.
- No actualizaste `codex/REDESIGN_PROGRESS.md`.
- No hiciste checklist.
- No ejecutaste validaciones.
- No revisaste dispositivo real cuando estaba disponible.
- No cubriste estados visuales.
- No hay cambios visibles profundos.
- Solo hiciste cambios de color o espaciado.
- No puedes explicar por qué la app ahora se siente premium.

---

## Entrega final esperada

Al finalizar, el reporte debe incluir:

```md
# Reporte final de rediseño UI/UX

## Auditoría inicial
...

## Sistema visual
...

## Pantallas intervenidas
...

## Componentes intervenidos
...

## Estados visuales intervenidos
...

## Validaciones técnicas
- flutter analyze:
- flutter test:
- flutter build apk --debug:

## Validación en celular real
- adb devices:
- flutter devices:
- device id:
- capturas generadas:

## Checklist visual
- Puntaje total:
- Categorías débiles:

## Archivos modificados
...

## Confirmación funcional
No se modificaron endpoints, contratos API, modelos, autenticación, permisos, reglas de negocio ni funcionamiento existente.

## Deuda pendiente
...
```
