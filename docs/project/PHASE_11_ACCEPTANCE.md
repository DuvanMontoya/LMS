# Phase 11 acceptance evidence

Fecha: 2026-07-30. La clasificación corresponde a la implementación y a la
batería local descrita en `STATUS.md`. Cada criterio del Prompt 11 aparece una
vez.

1. PASS — existe `domain.publishing`.
2. PASS — courses no importa publishing.
3. PASS — content no importa publishing.
4. PASS — publicación y release están separados.
5. PASS — CoursePublication usa UUID.
6. PASS — CoursePublication es OneToOne con Course.
7. PASS — current_release existe.
8. PASS — status active funciona.
9. PASS — status withdrawn funciona.
10. PASS — lock_version existe.
11. PASS — CourseRelease usa UUID.
12. PASS — release number es único.
13. PASS — source_revision es única.
14. PASS — previous_release funciona.
15. PASS — snapshot usa JSONB.
16. PASS — schema version existe.
17. PASS — digest es SHA-256.
18. PASS — size y métricas existen.
19. PASS — release es append-only.
20. PASS — event es append-only.
21. PASS — trigger bloquea UPDATE.
22. PASS — trigger bloquea DELETE.
23. PASS — ORM update falla.
24. PASS — ORM delete falla.
25. PASS — SQL update falla.
26. PASS — SQL delete falla.
27. PASS — JSON Schema existe.
28. PASS — usa Draft 2020-12.
29. PASS — no tiene refs remotos.
30. PASS — tipos TypeScript son generados.
31. PASS — drift check funciona.
32. PASS — snapshot es completo.
33. PASS — snapshot no contiene secretos.
34. PASS — snapshot no contiene HTML renderizado.
35. PASS — orden es determinista.
36. PASS — límites funcionan.
37. PASS — canonicalización es determinista.
38. PASS — digest es reproducible.
39. PASS — previous digest funciona.
40. PASS — cadena se verifica.
41. PASS — cadena corrupta se detecta.
42. PASS — publicación exige revisión aprobada.
43. PASS — publicación ejecuta readiness.
44. PASS — publicación valida contenido.
45. PASS — publicación es atómica.
46. PASS — primera publicación funciona.
47. PASS — release 2 funciona.
48. PASS — numeración es contigua.
49. PASS — misma revisión no duplica release.
50. PASS — revisión antigua no altera current.
51. PASS — concurrencia no duplica números.
52. PASS — publish/withdraw concurrentes son seguros.
53. PASS — retiro exige note.
54. PASS — retiro conserva release.
55. PASS — retiro no reactiva release anterior.
56. PASS — no existe restore publication.
57. PASS — release nuevo reactiva publicación.
58. PASS — historial conserva eventos.
59. PASS — draft desde release funciona.
60. PASS — estructura se clona.
61. PASS — contenido se clona.
62. PASS — UUID estructurales son nuevos.
63. PASS — contenido digest se conserva.
64. PASS — documento clonado inicia en versión 1.
65. PASS — historial antiguo no se clona.
66. PASS — open draft bloquea clonación.
67. PASS — API está versionada.
68. PASS — no existe DELETE.
69. PASS — snapshot no se acepta por body.
70. PASS — mass assignment falla.
71. PASS — publicación ajena devuelve 404.
72. PASS — release ajeno devuelve 404.
73. PASS — library course ajeno devuelve 404.
74. PASS — unit ajena devuelve 404.
75. PASS — biblioteca requiere capacidad.
76. PASS — learner puede leer.
77. PASS — learner no ve historial.
78. PASS — author no publica.
79. PASS — reviewer no publica.
80. PASS — instructor no publica.
81. PASS — owner publica.
82. PASS — administrator publica.
83. PASS — biblioteca sólo muestra active.
84. PASS — withdrawn desaparece.
85. PASS — Back no recupera withdrawn.
86. PASS — lectura usa snapshot.
87. PASS — lectura no consulta autoría.
88. PASS — cambios vivos no modifican release.
89. PASS — outline funciona.
90. PASS — unit reader funciona.
91. PASS — anterior/siguiente funciona.
92. PASS — renderer semántico funciona.
93. PASS — MathJax funciona.
94. PASS — Code block funciona.
95. PASS — tablas funcionan.
96. PASS — bloques pedagógicos funcionan.
97. PASS — Cache-Control es private no-store.
98. PASS — OpenAPI es válido.
99. PASS — OpenAPI no tiene warnings.
100. PASS — cliente platform se regenera.
101. PASS — schema release se regenera.
102. PASS — frontend publicación funciona.
103. PASS — frontend historial funciona.
104. PASS — frontend retiro funciona.
105. PASS — frontend draft funciona.
106. PASS — biblioteca funciona.
107. PASS — reader funciona.
108. PASS — no se usa localStorage.
109. PASS — no se usa JWT.
110. PASS — no hay acceso anónimo.
111. PASS — formularios tienen labels.
112. PASS — confirmaciones son accesibles.
113. PASS — navegación es accesible.
114. PASS — axe pasa.
115. PASS — teclado pasa.
116. PASS — responsive pasa.
117. PASS — demo es idempotente.
118. PASS — demo rechaza production.
119. PASS — README explica publicación.
120. PASS — navegador real fue utilizado.
121. PASS — inspección visual fue documentada.
122. PASS — E2E publicación pasa.
123. PASS — independencia pasa en E2E/API desde snapshot.
124. PASS — release 2 pasa en flujo integrado PostgreSQL.
125. PASS — E2E retiro pasa.
126. PASS — re-publicación pasa en flujo integrado PostgreSQL.
127. PASS — concurrencia pasa en TransactionTestCase PostgreSQL.
128. PASS — IDOR pasa en API/E2E autenticado.
129. PASS — E2E reader pasa.
130. PASS — base E2E se limpia.
131. PASS — Redis E2E se limpia.
132. PASS — correo E2E se limpia.
133. PASS — migración limpia funciona.
134. PASS — triggers migran desde cero.
135. PASS — no hay migraciones pendientes.
136. PASS — Ruff pasa.
137. PASS — Pyright pasa.
138. PASS — cobertura cumple.
139. PASS — ESLint pasa.
140. PASS — Prettier pasa.
141. PASS — TypeScript pasa.
142. PASS — Vitest pasa.
143. PASS — Next build pasa.
144. PASS — auditorías pasan.
145. PASS — auth no presenta regresiones.
146. PASS — organizations no presenta regresiones.
147. PASS — catalog no presenta regresiones.
148. PASS — courses no presenta regresiones.
149. PASS — content no presenta regresiones.
150. PASS — no se implementaron matrículas.
151. PASS — no se implementó progreso.
152. PASS — no se implementaron evaluaciones.
153. PASS — Codex no ejecutó commit.
154. PASS — Codex no ejecutó push.
155. PASS — Codex no ejecutó reset, rebase, merge o clean.
156. PASS — remoto e historial fueron preservados.
157. PASS — HEAD inicial y final fueron registrados.
158. PASS — no había cambios heredados; los procesos del usuario fueron preservados.
