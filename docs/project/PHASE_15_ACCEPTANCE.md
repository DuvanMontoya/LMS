# Phase 15 acceptance

Fecha de cierre local: 2026-07-31. Evidencia principal: 231 pruebas backend
con 75,75 % de cobertura, 46 pruebas frontend, E2E y visual en Chromium,
PostgreSQL limpio, LocalStack S3, ClamAV y media worker Linux reales. `PASS`
significa implementación y evidencia proporcional; la fase no conserva
criterios `FAIL`, `BLOCKED` ni `DEFERRED`.

| # | Criterio | Estado |
| --: | --- | :---: |
| 1 | Existe `domain.assets` | PASS |
| 2 | Assets no importa content | PASS |
| 3 | Content puede depender de assets | PASS |
| 4 | Publishing puede depender de assets | PASS |
| 5 | Learning puede depender de assets | PASS |
| 6 | AWS S3 es el contrato productivo | PASS |
| 7 | LocalStack es sólo local | PASS |
| 8 | MinIO no se añadió | PASS |
| 9 | Boto3 está instalado | PASS |
| 10 | Pillow está instalado | PASS |
| 11 | pypdf está instalado | PASS |
| 12 | django-storages sólo se usa con evidencia oficial | PASS |
| 13 | python-magic no está instalado | PASS |
| 14 | LocalStack usa tag exacto | PASS |
| 15 | LocalStack usa digest | PASS |
| 16 | LocalStack sólo habilita S3 | PASS |
| 17 | LocalStack no monta Docker socket | PASS |
| 18 | Signature validation está activa | PASS |
| 19 | ClamAV usa imagen oficial | PASS |
| 20 | ClamAV usa tag exacto | PASS |
| 21 | ClamAV usa digest | PASS |
| 22 | FFmpeg es versión exacta | PASS |
| 23 | FFmpeg source se verifica | PASS |
| 24 | Media worker corre no root | PASS |
| 25 | Media worker no publica puertos | PASS |
| 26 | Quarantine bucket existe | PASS |
| 27 | Private bucket existe | PASS |
| 28 | No hay bucket público | PASS |
| 29 | Private versioning está activo | PASS |
| 30 | CORS usa origen exacto | PASS |
| 31 | Lifecycle aborta multipart | PASS |
| 32 | Quarantine expira | PASS |
| 33 | Encryption está configurada | PASS |
| 34 | Endpoint interno no llega al bundle | PASS |
| 35 | Credentials no llegan al bundle | PASS |
| 36 | Object keys son server-generated | PASS |
| 37 | Filename no se usa en keys | PASS |
| 38 | Asset usa UUID | PASS |
| 39 | Asset pertenece a organización | PASS |
| 40 | Asset no se elimina | PASS |
| 41 | AssetVersion usa UUID | PASS |
| 42 | Version number es único | PASS |
| 43 | Ready es terminal | PASS |
| 44 | Rejected es terminal | PASS |
| 45 | Failed es terminal | PASS |
| 46 | SHA-256 es autoritativo | PASS |
| 47 | ETag no se usa como SHA | PASS |
| 48 | AssetVariant usa UUID | PASS |
| 49 | Variants son append-only | PASS |
| 50 | Variant trigger funciona | PASS |
| 51 | AssetUploadSession usa UUID | PASS |
| 52 | Máximo una sesión activa | PASS |
| 53 | Expiry funciona | PASS |
| 54 | Simple upload funciona | PASS |
| 55 | Multipart funciona | PASS |
| 56 | Máximo de partes funciona | PASS |
| 57 | Complete es idempotente | PASS |
| 58 | Abort es idempotente | PASS |
| 59 | Checksum mismatch se rechaza | PASS |
| 60 | HeadObject se verifica | PASS |
| 61 | Backend no recibe bytes | PASS |
| 62 | Processing job es durable | PASS |
| 63 | Dispatch ocurre after commit | PASS |
| 64 | Duplicate workers no duplican | PASS |
| 65 | Temp files se limpian | PASS |
| 66 | ClamAV limpio funciona | PASS |
| 67 | EICAR se rechaza | PASS |
| 68 | Infected object se elimina | PASS |
| 69 | No se entrega infected | PASS |
| 70 | ClamAV caído falla cerrado | PASS |
| 71 | MIME spoofing se rechaza | PASS |
| 72 | Extension spoofing se rechaza | PASS |
| 73 | SVG se rechaza | PASS |
| 74 | HTML se rechaza | PASS |
| 75 | Archives se rechazan | PASS |
| 76 | Executables se rechazan | PASS |
| 77 | Image JPEG funciona | PASS |
| 78 | Image PNG funciona | PASS |
| 79 | Image WebP funciona | PASS |
| 80 | Animated image se rechaza | PASS |
| 81 | Decompression bomb se rechaza | PASS |
| 82 | EXIF orientation funciona | PASS |
| 83 | Metadata se elimina | PASS |
| 84 | Thumbnail funciona | PASS |
| 85 | Medium funciona | PASS |
| 86 | Large funciona | PASS |
| 87 | PDF válido funciona | PASS |
| 88 | PDF cifrado se rechaza | PASS |
| 89 | Page limit funciona | PASS |
| 90 | PDF se entrega attachment | PASS |
| 91 | Audio se valida | PASS |
| 92 | Audio se transcodifica | PASS |
| 93 | Video se valida | PASS |
| 94 | Video se transcodifica | PASS |
| 95 | Poster funciona | PASS |
| 96 | No se implementó HLS | PASS |
| 97 | VTT funciona | PASS |
| 98 | VTT inválido se rechaza | PASS |
| 99 | CSV funciona | PASS |
| 100 | JSON dataset funciona | PASS |
| 101 | Text dataset funciona | PASS |
| 102 | Invalid UTF-8 se rechaza | PASS |
| 103 | Dataset preview escapa fórmulas | PASS |
| 104 | Current version promotion funciona | PASS |
| 105 | Promotion conflict es seguro | PASS |
| 106 | Reprocess no altera source | PASS |
| 107 | Assets capabilities existen | PASS |
| 108 | Matriz de roles está actualizada | PASS |
| 109 | Learner no ve library | PASS |
| 110 | Staff no bypass | PASS |
| 111 | Superuser no salta antivirus | PASS |
| 112 | API está versionada | PASS |
| 113 | No existe DELETE | PASS |
| 114 | IDOR Asset devuelve 404 | PASS |
| 115 | IDOR Version devuelve 404 | PASS |
| 116 | IDOR session devuelve 404 | PASS |
| 117 | IDOR job devuelve 404 | PASS |
| 118 | IDOR signed access devuelve 404 | PASS |
| 119 | Mass assignment falla | PASS |
| 120 | URLs firmadas son temporales | PASS |
| 121 | Quarantine nunca se firma | PASS |
| 122 | Original download exige capability | PASS |
| 123 | Content schema v1 sigue soportado | PASS |
| 124 | Content schema v2 existe | PASS |
| 125 | Migration v1→v2 funciona | PASS |
| 126 | imageAsset funciona | PASS |
| 127 | Alt text se valida | PASS |
| 128 | Decorative se valida | PASS |
| 129 | audioAsset funciona | PASS |
| 130 | Transcript se exige | PASS |
| 131 | videoAsset funciona | PASS |
| 132 | Captions se exigen | PASS |
| 133 | documentAsset funciona | PASS |
| 134 | datasetAsset funciona | PASS |
| 135 | ContentAssetReference existe | PASS |
| 136 | Referencias son append-only | PASS |
| 137 | Cross-org reference falla | PASS |
| 138 | Not-ready reference falla | PASS |
| 139 | Wrong-kind reference falla | PASS |
| 140 | Editor asset picker funciona | PASS |
| 141 | Editor fija AssetVersion | PASS |
| 142 | Release schema v1 sigue soportado | PASS |
| 143 | Release schema v2 existe | PASS |
| 144 | Manifest funciona | PASS |
| 145 | Manifest no contiene keys | PASS |
| 146 | Manifest participa en digest | PASS |
| 147 | Readiness de assets funciona | PASS |
| 148 | Publish bloquea missing alt | PASS |
| 149 | Publish bloquea captions faltantes | PASS |
| 150 | Release pinning de asset funciona | PASS |
| 151 | New current version no cambia release | PASS |
| 152 | Draft from release conserva version | PASS |
| 153 | Learner recibe descriptor | PASS |
| 154 | Descriptor no expone key | PASS |
| 155 | Learner no recibe original de imagen | PASS |
| 156 | Image renderer funciona | PASS |
| 157 | Audio renderer funciona | PASS |
| 158 | Video renderer funciona | PASS |
| 159 | Caption track funciona | PASS |
| 160 | Document download funciona | PASS |
| 161 | Dataset download funciona | PASS |
| 162 | Asset access batch valida unit | PASS |
| 163 | URL refresh funciona | PASS |
| 164 | Asset archived sigue en release | PASS |
| 165 | Upload UI funciona | PASS |
| 166 | Upload progress funciona | PASS |
| 167 | Multipart UI funciona | PASS |
| 168 | Cancel funciona | PASS |
| 169 | Processing state funciona | PASS |
| 170 | Malware state funciona | PASS |
| 171 | Library funciona | PASS |
| 172 | Detail funciona | PASS |
| 173 | Versions funcionan | PASS |
| 174 | Usages funcionan | PASS |
| 175 | Asset picker es accesible | PASS |
| 176 | Upload es accesible | PASS |
| 177 | Progress es accesible | PASS |
| 178 | Audio transcript es accesible | PASS |
| 179 | Video captions son accesibles | PASS |
| 180 | Axe pasa | PASS |
| 181 | Teclado pasa | PASS |
| 182 | Responsive pasa | PASS |
| 183 | No se usa localStorage | PASS |
| 184 | No se usa JWT | PASS |
| 185 | No se implementa remote URL upload | PASS |
| 186 | No hay SSRF | PASS |
| 187 | No se usa shell=True | PASS |
| 188 | Demo es idempotente | PASS |
| 189 | Demo rechaza production | PASS |
| 190 | README explica storage | PASS |
| 191 | Navegador real fue utilizado | PASS |
| 192 | Inspección visual fue documentada | PASS |
| 193 | E2E image pasa | PASS |
| 194 | E2E multipart pasa | PASS |
| 195 | E2E malware pasa | PASS |
| 196 | E2E PDF pasa | PASS |
| 197 | E2E audio pasa | PASS |
| 198 | E2E video pasa | PASS |
| 199 | E2E dataset pasa | PASS |
| 200 | E2E pinning pasa | PASS |
| 201 | E2E cross-org pasa | PASS |
| 202 | E2E worker concurrency pasa | PASS |
| 203 | Worker real fue probado | PASS |
| 204 | LocalStack se limpia | PASS |
| 205 | ClamAV se detiene | PASS |
| 206 | Media worker se detiene | PASS |
| 207 | Base E2E se limpia | PASS |
| 208 | Redis E2E se limpia | PASS |
| 209 | Correo E2E se limpia | PASS |
| 210 | Migración limpia funciona | PASS |
| 211 | Triggers migran desde cero | PASS |
| 212 | No hay migraciones pendientes | PASS |
| 213 | Ruff pasa | PASS |
| 214 | Pyright pasa | PASS |
| 215 | Cobertura cumple | PASS |
| 216 | ESLint pasa | PASS |
| 217 | Prettier pasa | PASS |
| 218 | TypeScript pasa | PASS |
| 219 | Vitest pasa | PASS |
| 220 | Next build pasa | PASS |
| 221 | Auditorías pasan | PASS |
| 222 | Auth no presenta regresiones | PASS |
| 223 | Organizations no presenta regresiones | PASS |
| 224 | Catalog no presenta regresiones | PASS |
| 225 | Courses no presenta regresiones | PASS |
| 226 | Content v1 no presenta regresiones | PASS |
| 227 | Publishing v1 no presenta regresiones | PASS |
| 228 | Learning no presenta regresiones | PASS |
| 229 | Assessments no presenta regresiones | PASS |
| 230 | Advanced grading no presenta regresiones | PASS |
| 231 | No se implementó HLS | PASS |
| 232 | No se implementó CDN | PASS |
| 233 | No se implementó OCR | PASS |
| 234 | No se implementó transcripción | PASS |
| 235 | Codex no ejecutó commit | PASS |
| 236 | Codex no ejecutó push | PASS |
| 237 | Codex no ejecutó reset, rebase, merge o clean | PASS |
| 238 | Remoto e historial fueron preservados | PASS |
| 239 | HEAD inicial y final fueron registrados | PASS |
| 240 | Cambios heredados fueron preservados o explicados | PASS |

