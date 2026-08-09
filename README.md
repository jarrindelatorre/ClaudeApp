# Vuelta al Sol — Prototipo funcional

Prototipo en **PHP vanilla + MySQL**, sin frameworks, pensado para correr en
hosting compartido de Hostinger. Cero diseño todavía a propósito — el foco de
esta etapa es que la funcionalidad ande; el UI se trabaja después en Figma.

## Qué hace ahora mismo

1. **`/activar.php`** — el cumpleañero crea su página: nombre, email, alias/QR
   de cobro, selfie, traje. Genera un slug único (`/u/slug`) y un link privado
   de panel (`/panel/token`).
2. **`/admin.php`** — vos confirmás manualmente que el cumpleañero pagó la
   cuota de activación (1-2 USD) y ahí se activa su ventana de 30 horas.
3. **`/u/slug`** — página pública del cumpleañero (feed en vivo de regalos).
4. **`/regalo/slug`** — un invitado paga directo al QR/alias del cumpleañero
   (dinero peer-to-peer, la app nunca lo toca), sube su comprobante, y el
   regalo aparece al instante en el feed.
5. **`/panel/token`** — panel privado del cumpleañero: estado, links para
   compartir, feed en vivo, total recaudado.
6. **`/api/feed.php?slug=`** — endpoint JSON que consultan `u.php` y
   `panel.php` cada 5s (polling simple, sin websockets — corre bien en
   hosting compartido).

Todo probado localmente de punta a punta (activar → confirmar pago → regalar
→ ver en el feed) antes de entregarlo.

## Cosas simplificadas a propósito (para no bloquear el prototipo)

- **Interpretación de regalos con IA**: hoy `interpretarRegalo()` en
  `includes/functions.php` es un stub simple (agrega un prefijo temático).
  Cuando quieran la versión real con Claude, se reemplaza esa función por una
  llamada a la API — el resto del sistema no cambia.
- **Subdominios** (`valentina.vueltaalsol.com`): el código ya soporta rutas
  tipo `/u/slug`; para subdominios reales hay que activar un subdominio
  comodín (`*.vueltaalsol.com`) en hPanel más adelante — no bloquea nada hoy.
- **Confirmación de regalos**: sistema de honor + comprobante subido por el
  invitado (no hay forma técnica de verificar transferencias bancarias en
  tiempo real). La cuota de activación sí la confirmás vos a mano en
  `/admin.php`, porque ese es tu ingreso real.

## Instalación en Hostinger

### 1. Base de datos

En hPanel → Bases de datos → Bases de datos MySQL, creá una base y un
usuario con todos los privilegios sobre ella. Después, en phpMyAdmin, importá
`sql/schema.sql`.

### 2. Config

Copiá `public_html/includes/config.sample.php` a
`public_html/includes/config.php` (este último **no se sube a git**, tiene
credenciales) y completá:

- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` con lo que creaste en el paso 1
- `SITE_URL` → `https://vueltaalsol.com`
- `ADMIN_PASSWORD` → una contraseña tuya para `/admin.php`

### 3. Subir archivos

Solo se sube el **contenido** de `public_html/` a la raíz `public_html` de tu
hosting (no la carpeta `public_html` en sí, su contenido).

**Opción rápida (una vez)**: hPanel → Archivos → Administrador de archivos →
subir un `.zip` del contenido de `public_html/` y usar "Extraer".

**Opción para iterar seguido**: con FileZilla o la extensión FTP/SFTP de VS
Code, usando estos datos:

- Host: `217.21.76.150`
- Usuario: `u171435243.vueltaalsol.com`
- Puerto: `21`
- Carpeta destino: `public_html`

O corriendo `deploy/deploy.sh` desde tu computadora (no desde acá — ver
comentario en el script):

```bash
FTP_HOST=217.21.76.150 FTP_USER=u171435243.vueltaalsol.com FTP_PASS='...' ./deploy/deploy.sh
```

⚠️ Nunca subas `public_html/includes/config.php` a git ni lo compartas —
tiene las credenciales de tu base de datos.

## Probar localmente antes de subir (opcional)

```bash
php -S localhost:8090 -t public_html
```

(Ojo: las URLs "bonitas" `/u/slug` dependen de `.htaccess`, que el servidor
integrado de PHP no aplica — para probar local usá `u.php?slug=...` directo.)

## Próximos pasos sugeridos

- Definir pantallas finales en Figma sobre este flujo ya funcional.
- Conectar `interpretarRegalo()` a la API de Claude de verdad.
- Configurar subdominio comodín en hPanel para `nombre.vueltaalsol.com`.
- Reforzar el borrado/expiración de comprobantes bancarios (privacidad).
