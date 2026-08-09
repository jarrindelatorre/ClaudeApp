<?php
require_once __DIR__ . '/db.php';

function slugify(string $texto): string
{
    $texto = strtolower(trim($texto));
    $texto = iconv('UTF-8', 'ASCII//TRANSLIT', $texto) ?: $texto;
    $texto = preg_replace('/[^a-z0-9]+/', '-', $texto);
    return trim($texto, '-');
}

function generarSlugUnico(string $nombre): string
{
    $base = slugify($nombre) ?: 'invitado';
    $slug = $base . '-' . substr(bin2hex(random_bytes(2)), 0, 4);
    // Chequear colisión (muy improbable, pero por si acaso)
    $stmt = db()->prepare('SELECT id FROM cumpleaneros WHERE slug = ?');
    while (true) {
        $stmt->execute([$slug]);
        if (!$stmt->fetch()) {
            return $slug;
        }
        $slug = $base . '-' . substr(bin2hex(random_bytes(2)), 0, 4);
    }
}

function generarToken(): string
{
    return bin2hex(random_bytes(24));
}

/**
 * Guarda un archivo subido ($_FILES[campo]) en $carpetaDestino dentro de uploads/.
 * Valida tipo (jpg/png/webp) y tamaño (máx 5MB). Devuelve la ruta relativa o null.
 */
function guardarImagenSubida(string $campo, string $carpetaDestino): ?string
{
    if (empty($_FILES[$campo]) || $_FILES[$campo]['error'] !== UPLOAD_ERR_OK) {
        return null;
    }
    $archivo = $_FILES[$campo];

    if ($archivo['size'] > 5 * 1024 * 1024) {
        throw new RuntimeException('La imagen no puede pesar más de 5MB.');
    }

    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $mime = finfo_file($finfo, $archivo['tmp_name']);
    finfo_close($finfo);

    $extensiones = [
        'image/jpeg' => 'jpg',
        'image/png'  => 'png',
        'image/webp' => 'webp',
    ];
    if (!isset($extensiones[$mime])) {
        throw new RuntimeException('Formato de imagen no soportado (usar JPG, PNG o WEBP).');
    }

    $nombreArchivo = bin2hex(random_bytes(16)) . '.' . $extensiones[$mime];
    $rutaAbsoluta = __DIR__ . '/../uploads/' . $carpetaDestino . '/' . $nombreArchivo;

    if (!move_uploaded_file($archivo['tmp_name'], $rutaAbsoluta)) {
        throw new RuntimeException('No se pudo guardar la imagen.');
    }

    return 'uploads/' . $carpetaDestino . '/' . $nombreArchivo;
}

function obtenerCumpleaneroPorSlug(string $slug): ?array
{
    $stmt = db()->prepare('SELECT * FROM cumpleaneros WHERE slug = ?');
    $stmt->execute([$slug]);
    $fila = $stmt->fetch();
    return $fila ?: null;
}

function obtenerCumpleaneroPorToken(string $token): ?array
{
    $stmt = db()->prepare('SELECT * FROM cumpleaneros WHERE token = ?');
    $stmt->execute([$token]);
    $fila = $stmt->fetch();
    return $fila ?: null;
}

/**
 * Interpreta el texto libre del invitado y devuelve un regalo temático.
 * Stub simple sin IA real todavía — cuando se configure CLAUDE_API_KEY
 * en config.php, reemplazar el cuerpo de esta función por una llamada
 * real a la API de Claude (Messages API) pidiendo JSON estructurado.
 */
function interpretarRegalo(string $textoOriginal, float $monto): array
{
    $iconos = ['🚀', '🛸', '🪐', '☄️', '🌙', '⭐', '🧑‍🚀'];
    $prefijos = ['Suministro espacial:', 'Cargamento de la nave:', 'Provisión de viaje:'];

    return [
        'nombre'      => trim($prefijos[array_rand($prefijos)] . ' ' . $textoOriginal),
        'descripcion' => 'Un regalo para el viaje de vuelta al sol.',
        'icono'       => $iconos[array_rand($iconos)],
    ];
}

function ventanaActivaHasta(): string
{
    return date('Y-m-d H:i:s', strtotime('+' . VENTANA_HORAS . ' hours'));
}

function estaActivo(array $cumpleanero): bool
{
    if (!$cumpleanero['pago_confirmado']) {
        return false;
    }
    if (empty($cumpleanero['activo_desde']) || empty($cumpleanero['activo_hasta'])) {
        return false;
    }
    $ahora = date('Y-m-d H:i:s');
    return $ahora >= $cumpleanero['activo_desde'] && $ahora <= $cumpleanero['activo_hasta'];
}

function h(?string $texto): string
{
    return htmlspecialchars($texto ?? '', ENT_QUOTES, 'UTF-8');
}
