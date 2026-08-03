# Auditoria real del VPS para video y MediaCMS

Fecha de medicion: 2026-08-03. Todas las cifras de sistema, red y servicios proceden de la instancia en ejecucion.

## Acceso recuperado

La cuenta administrativa correcta es `debian`, no `root`. SSH esta configurado para permitir exclusivamente claves publicas a `debian`; dicha cuenta tiene `sudo` sin contraseña. Se preservo esta politica. La clave privada para este acceso esta junto a este informe, en `contabo-vmi3156908-debian-rsa`.

```powershell
ssh -i .\contabo-vmi3156908-debian-rsa debian@185.192.96.27
```

Despues de entrar: `sudo -i`.

## Hardware y sistema

| Elemento | Resultado real |
|---|---|
| Virtualizacion | KVM completa sobre QEMU / virtio |
| Sistema operativo | Debian GNU/Linux 13.6 (trixie), x86-64 |
| Kernel | 6.12.100+deb13-cloud-amd64 |
| CPU visible | 10 vCPU, AMD EPYC Processor (with IBPB), familia 23 modelo 1, 1 socket/NUMA, 10 hilos visibles |
| CPU no expuesta | El hipervisor no entrega SKU fisico ni frecuencia; no se puede afirmar un modelo EPYC exacto ni GHz sostenidos |
| Instrucciones | AES-NI, AVX, AVX2, FMA, BMI1/2, SHA-NI; no AVX-512 visible |
| Cache visible | L1d 320 KiB, L1i 640 KiB, L2 5 MiB, L3 8 MiB |
| RAM | 35.24 GiB visibles; 33 GiB disponibles al medir |
| Swap | No hay swap |
| Disco | Un disco virtual QEMU no rotacional de 500 GiB, ext4, sin RAID/LVM |
| Particion raiz | 491.9 GiB; 460.5 GiB libres; 31 millones de inodos libres |
| Disco - lectura | 1 GiB de lectura directa secuencial: 3,694 MiB/s. Es solo lectura secuencial en una VM; no equivale a IOPS ni a escritura aleatoria. |
| GPU/VAAPI/NVIDIA | No hay GPU asignada. Solo VGA virtual QEMU, sin `/dev/dri`, sin NVIDIA y sin FFmpeg instalado. |

## Red real para streaming

La interfaz publica es `eth0` virtio, MTU 1500. El invitado no conoce la velocidad nominal del puerto (`Speed: Unknown`), pero se midio salida real desde el VPS hacia Cloudflare:

| Prueba | Resultado |
|---|---:|
| 50 MB de salida | 406 Mbit/s |
| 200 MB de salida | 481 Mbit/s sostenidos durante 3.32 s |

Para planificar video directo, usar como presupuesto inicial 360 Mbit/s (25% de reserva para picos, TLS, HLS y otros servicios), no el maximo medido. Eso da aproximadamente 180 espectadores a 2 Mbit/s, 90 a 4 Mbit/s, 60 a 6 Mbit/s, 45 a 8 Mbit/s o 24 a 15 Mbit/s, simultaneos. Es capacidad de entrega, no de transcodificacion.

TCP usa CUBIC y `fq_codel`; los maximos de buffer son conservadores (rmem 6 MiB, wmem 4 MiB). Conviene medir con audiencia real antes de ajustarlos.

## Estado actual y compatibilidad con MediaCMS

El VPS no esta vacio. Ya ejecuta Docker 26.1.5 con cuatro contenedores sanos: `laila-web-1`, `laila-caddy-1`, `laila-wordpress-1` y `laila-db-1`. Caddy publica 80/443 y el firewall UFW permite solamente 22, 80 y 443. Tambien estan activos Fail2Ban y copias automaticas de Contabo.

Por ello MediaCMS debe coexistir mediante un nuevo hostname y enrutamiento de Caddy, sin tomar directamente 80/443 ni alterar los contenedores existentes.

La RAM y CPU bastan para una primera plataforma MediaCMS pequena o mediana. No hay aceleracion de video: cada perfil HLS se codificara por CPU. Se debe empezar con una cola de transcodificacion de uno o dos trabajos y medir antes de aumentar concurrencia. No es apropiado prometer capacidad de codificacion 1080p sin instalar FFmpeg y hacer una prueba con un video representativo.

MediaCMS conserva original, codificaciones y HLS. Con un factor aproximado 3x y reserva operativa, los 460.5 GiB libres equivalen prudentemente a unos 100--120 GiB de videos fuente. A 10 Mbit/s de fuente, eso es aproximadamente 22--27 horas de catalogo; sin multicalidad serian unas 100 horas.

## Limites y decisiones importantes antes de desplegar

1. No usar este VPS como unico CDN para una audiencia grande o continua; usar HLS con CDN/object storage cuando la audiencia crezca.
2. Mantener el acceso por clave a `debian`; `root` esta bloqueado por SSH deliberadamente.
3. Crear un snapshot manual antes del despliegue de MediaCMS. El panel confirma Auto Backup, pero no habia snapshots manuales.
4. Definir dominio/subdominio y coexistencia con el Caddy actual antes de crear contenedores.
5. Incorporar almacenamiento externo o CDN antes de que el catalogo se acerque al limite de disco.
6. Considerar swap pequena y limites `nofile` explicitos para los contenedores de MediaCMS cuando se pase a produccion.
