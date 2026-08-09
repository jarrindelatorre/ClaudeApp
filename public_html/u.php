<?php
require_once __DIR__ . '/includes/functions.php';

$slug = $_GET['slug'] ?? '';
$cumpleanero = $slug ? obtenerCumpleaneroPorSlug($slug) : null;

if (!$cumpleanero) {
    http_response_code(404);
    echo '<p>No existe esa página.</p>';
    exit;
}

$activo = estaActivo($cumpleanero);

// Total recaudado (regalos confirmados)
$stmt = db()->prepare('SELECT COALESCE(SUM(monto),0) AS total, COUNT(*) AS cantidad FROM regalos WHERE cumpleanero_id = ? AND estado = "confirmado"');
$stmt->execute([$cumpleanero['id']]);
$resumen = $stmt->fetch();
?>
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title><?= h($cumpleanero['nombre']) ?> — Vuelta al Sol</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h1>🎉 Hoy es el cumpleaños de <?= h($cumpleanero['nombre']) ?></h1>

<?php if (!$activo): ?>
    <p style="color:#a60">Esta página todavía no está activa (falta confirmar el pago de activación,
    o la ventana de 30 horas ya venció).</p>
<?php else: ?>
    <p>Regálale algo para su viaje de Vuelta al Sol 🚀</p>
    <p>Recaudado hasta ahora: <strong><?= h(number_format((float)$resumen['total'], 2)) ?> USD</strong>
       (<?= (int)$resumen['cantidad'] ?> regalos)</p>
    <p><a href="../regalo/<?= h($cumpleanero['slug']) ?>"><button>Regalar algo</button></a></p>

    <h2>Feed en vivo</h2>
    <div id="feed">Cargando...</div>

    <script>
    const slug = <?= json_encode($cumpleanero['slug']) ?>;
    async function actualizarFeed() {
        try {
            const res = await fetch('../api/feed/' + slug);
            const data = await res.json();
            const feed = document.getElementById('feed');
            if (!data.regalos.length) {
                feed.innerHTML = '<p>Todavía no hay regalos, ¡sé el primero!</p>';
                return;
            }
            feed.innerHTML = '<ul>' + data.regalos.map(r =>
                `<li>${r.icono || '🎁'} <strong>${r.nombre_generado || r.texto_original}</strong>
                 — $${r.monto}${r.invitado_nombre ? ' de ' + r.invitado_nombre : ''}</li>`
            ).join('') + '</ul>';
        } catch (e) {
            console.error('Error actualizando feed', e);
        }
    }
    actualizarFeed();
    setInterval(actualizarFeed, 5000);
    </script>
<?php endif; ?>

</body>
</html>
