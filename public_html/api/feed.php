<?php
require_once __DIR__ . '/../includes/functions.php';

header('Content-Type: application/json; charset=utf-8');

$slug = $_GET['slug'] ?? '';
$cumpleanero = $slug ? obtenerCumpleaneroPorSlug($slug) : null;

if (!$cumpleanero) {
    http_response_code(404);
    echo json_encode(['error' => 'no encontrado']);
    exit;
}

$stmt = db()->prepare(
    'SELECT invitado_nombre, es_publico, texto_original, nombre_generado, descripcion_generada, icono, monto, creado_en
     FROM regalos
     WHERE cumpleanero_id = ? AND estado = "confirmado"
     ORDER BY creado_en DESC'
);
$stmt->execute([$cumpleanero['id']]);
$regalos = $stmt->fetchAll();

// Ocultar el nombre de quien no quiso ser público
foreach ($regalos as &$r) {
    if (!$r['es_publico']) {
        $r['invitado_nombre'] = null;
    }
    unset($r['es_publico']);
}

$total = array_sum(array_column($regalos, 'monto'));

echo json_encode([
    'total' => $total,
    'cantidad' => count($regalos),
    'regalos' => $regalos,
]);
