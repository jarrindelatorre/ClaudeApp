<?php
require_once __DIR__ . '/includes/functions.php';

$token = $_GET['token'] ?? '';
$cumpleanero = $token ? obtenerCumpleaneroPorToken($token) : null;

if (!$cumpleanero) {
    http_response_code(404);
    echo '<p>Panel no encontrado. Revisá el link que te dimos al activar tu página.</p>';
    exit;
}

$activo = estaActivo($cumpleanero);
$urlPublica = SITE_URL . '/u/' . $cumpleanero['slug'];
$urlRegalo = SITE_URL . '/regalo/' . $cumpleanero['slug'];
?>
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Mi panel — Vuelta al Sol</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h1>Hola <?= h($cumpleanero['nombre']) ?> 👋</h1>

<h2>Estado</h2>
<?php if (!$cumpleanero['pago_confirmado']): ?>
    <p style="color:#a60">
        Tu pago de activación (<?= h((string) $cumpleanero['monto_activacion']) ?> USD) todavía
        no fue confirmado. Transferí a nuestra cuenta y avisanos — mientras tanto tu página no
        puede recibir regalos.
    </p>
<?php elseif (!$activo): ?>
    <p style="color:#a60">Tu ventana de <?= VENTANA_HORAS ?> horas ya venció.</p>
<?php else: ?>
    <p style="color:green">
        ¡Activo! Vence: <?= h($cumpleanero['activo_hasta']) ?>
    </p>
<?php endif; ?>

<h2>Compartí tu link</h2>
<p>Página pública: <a href="<?= h($urlPublica) ?>"><?= h($urlPublica) ?></a></p>
<p>Link directo para regalar: <a href="<?= h($urlRegalo) ?>"><?= h($urlRegalo) ?></a></p>
<p>
    Mensaje sugerido para tu historia:<br>
    <textarea readonly style="width:100%" rows="3">HOY ES MI CUMPLEAÑOS 🎂🚀 Podés regalarme lo que quieras acá: <?= h($urlRegalo) ?></textarea>
</p>

<h2>Feed en vivo</h2>
<div id="feed">Cargando...</div>
<p>Total: <strong id="total">-</strong></p>

<script>
const slug = <?= json_encode($cumpleanero['slug']) ?>;
async function actualizarFeed() {
    try {
        const res = await fetch('api/feed.php?slug=' + encodeURIComponent(slug));
        const data = await res.json();
        document.getElementById('total').textContent = '$' + data.total;
        const feed = document.getElementById('feed');
        if (!data.regalos.length) {
            feed.innerHTML = '<p>Todavía no hay regalos.</p>';
            return;
        }
        feed.innerHTML = '<ul>' + data.regalos.map(r =>
            `<li>${r.icono || '🎁'} <strong>${r.nombre_generado || r.texto_original}</strong>
             — $${r.monto}${r.invitado_nombre ? ' de ' + r.invitado_nombre : ' (anónimo)'}</li>`
        ).join('') + '</ul>';
    } catch (e) {
        console.error('Error actualizando feed', e);
    }
}
actualizarFeed();
setInterval(actualizarFeed, 5000);
</script>

</body>
</html>
