#!/usr/bin/env bash
# Sincroniza public_html/ de este repo al hosting de Hostinger vía FTP.
#
# Correr esto DESDE TU COMPUTADORA (no funciona desde el sandbox de Claude Code
# en la nube porque ese entorno bloquea el puerto FTP por política de red).
#
# Requiere lftp instalado:
#   macOS:   brew install lftp
#   Ubuntu:  sudo apt install lftp
#
# Uso:
#   FTP_HOST=217.21.76.150 FTP_USER=u171435243.vueltaalsol.com FTP_PASS='...' ./deploy/deploy.sh

set -euo pipefail

: "${FTP_HOST:?Falta FTP_HOST}"
: "${FTP_USER:?Falta FTP_USER}"
: "${FTP_PASS:?Falta FTP_PASS}"
FTP_PORT="${FTP_PORT:-21}"

cd "$(dirname "$0")/.."

lftp -u "$FTP_USER,$FTP_PASS" -p "$FTP_PORT" "$FTP_HOST" <<EOF
set ftp:ssl-allow no
mirror --reverse --verbose --delete \
    --exclude includes/config.php \
    --exclude uploads/ \
    public_html/ public_html/
bye
EOF

echo "Listo. No se tocó includes/config.php ni la carpeta uploads/ en el servidor."
