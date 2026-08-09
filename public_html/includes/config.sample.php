<?php
/**
 * Copiar este archivo como config.php (mismo directorio) y completar
 * con los datos reales. config.php NUNCA se sube a git (ver .gitignore).
 */

// --- Base de datos MySQL (hPanel > Bases de datos) ---
define('DB_HOST', 'localhost');
define('DB_NAME', 'u000000000_vueltaalsol');
define('DB_USER', 'u000000000_admin');
define('DB_PASS', 'CAMBIAR_ESTO');

// --- General ---
define('SITE_URL', 'https://vueltaalsol.com');
define('MONTO_ACTIVACION_DEFAULT', 2.00); // USD que paga el cumpleañero por activar su día
define('VENTANA_HORAS', 30);              // duración de la campaña activa

// --- IA para interpretar regalos (opcional, se puede dejar vacío en el prototipo) ---
// Cuando quieran activar la interpretación real con Claude, poner la key acá.
define('CLAUDE_API_KEY', '');

// --- Panel de administración (para confirmar pagos de activación manualmente) ---
define('ADMIN_PASSWORD', 'CAMBIAR_ESTO_TAMBIEN');
