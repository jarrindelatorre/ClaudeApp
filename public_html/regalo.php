<?php
require_once __DIR__ . '/includes/functions.php';

$slug = $_GET['slug'] ?? '';
$cumpleanero = $slug ? obtenerCumpleaneroPorSlug($slug) : null;

if (!$cumpleanero) {
    http_response_code(404);
    echo '<p>No existe esa página.</p>';
    exit;
}

if (!estaActivo($cumpleanero)) {
    echo '<p>Esta página no está activa para recibir regalos ahora mismo.</p>';
    exit;
}

$errores = [];
$exito = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        $monto = (float) ($_POST['monto'] ?? 0);
        $textoRegalo = trim($_POST['texto_regalo'] ?? '');
        $invitadoNombre = trim($_POST['invitado_nombre'] ?? '');
        $esPublico = isset($_POST['es_publico']) ? 1 : 0;

        if ($monto <= 0) {
            throw new RuntimeException('Elegí o escribí un monto válido.');
        }
        if ($textoRegalo === '') {
            throw new RuntimeException('Contanos qué le querés regalar (aunque sea una palabra).');
        }

        $comprobantePath = guardarImagenSubida('comprobante', 'receipts');
        if (!$comprobantePath) {
            throw new RuntimeException('Subí el comprobante de tu transferencia/pago para confirmar el regalo.');
        }

        $interpretado = interpretarRegalo($textoRegalo, $monto);

        $stmt = db()->prepare(
            'INSERT INTO regalos
                (cumpleanero_id, invitado_nombre, es_publico, texto_original, nombre_generado, descripcion_generada, icono, monto, comprobante_path, estado)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "confirmado")'
        );
        $stmt->execute([
            $cumpleanero['id'],
            $invitadoNombre ?: null,
            $esPublico,
            $textoRegalo,
            $interpretado['nombre'],
            $interpretado['descripcion'],
            $interpretado['icono'],
            $monto,
            $comprobantePath,
        ]);

        $exito = true;
    } catch (Throwable $e) {
        $errores[] = $e->getMessage();
    }
}
?>
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Regalarle a <?= h($cumpleanero['nombre']) ?> — Vuelta al Sol</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h1>Regalale algo a <?= h($cumpleanero['nombre']) ?> 🎁</h1>

<?php if ($exito): ?>
    <p><strong>¡Gracias! Tu regalo quedó registrado.</strong></p>
    <p><a href="../u/<?= h($cumpleanero['slug']) ?>">Ver el feed en vivo</a></p>
<?php else: ?>

    <?php foreach ($errores as $err): ?>
        <p style="color:red"><?= h($err) ?></p>
    <?php endforeach; ?>

    <h2>1. Pagá</h2>
    <?php if ($cumpleanero['alias_cobro'] !== ''): ?>
    <p>Alias / cuenta de <?= h($cumpleanero['nombre']) ?>:
       <strong id="alias"><?= h($cumpleanero['alias_cobro']) ?></strong>
       <button type="button" onclick="copiarAlias()">Copiar</button>
    </p>
    <?php endif; ?>

    <?php if ($cumpleanero['qr_pago_path']): ?>
        <div id="bloque-qr">
            <p>Escaneá este QR desde tu app del banco:</p>
            <img src="<?= h($cumpleanero['qr_pago_path']) ?>" alt="QR de pago" style="max-width:250px">
        </div>
        <div id="bloque-celular" style="display:none">
            <p>Estás entrando desde el celular, así que probablemente no puedas escanear tu propia pantalla.
               Guardá el QR en tu galería o copiá el alias de arriba:</p>
            <a id="descargar-qr" href="<?= h($cumpleanero['qr_pago_path']) ?>" download>Guardar QR en galería</a>
        </div>
    <?php endif; ?>

    <h2>2. Elegí el monto</h2>
    <p>
        <label><input type="radio" name="monto_preset" value="3"> $3</label>
        <label><input type="radio" name="monto_preset" value="5"> $5</label>
        <label><input type="radio" name="monto_preset" value="10"> $10</label>
        <label><input type="radio" name="monto_preset" value="otro"> Otro monto</label>
    </p>

    <h2>3. Contale a la app y subí tu comprobante</h2>
    <form method="post" enctype="multipart/form-data">
        <p>
            <label>Monto (USD)<br>
            <input type="number" step="0.01" min="0.5" name="monto" id="monto" required></label>
        </p>
        <p>
            <label>¿Qué le querés regalar? (en tus palabras, ej: "una patita asada de dinosaurio")<br>
            <input type="text" name="texto_regalo" required style="width:100%"></label>
        </p>
        <p>
            <label>Tu nombre (opcional)<br>
            <input type="text" name="invitado_nombre"></label>
        </p>
        <p>
            <label><input type="checkbox" name="es_publico" checked> Mostrar mi nombre en el feed público</label>
        </p>
        <p>
            <label>Comprobante de la transferencia/pago (captura de pantalla)<br>
            <input type="file" name="comprobante" accept="image/*" required></label>
        </p>
        <p><button type="submit">Confirmar regalo</button></p>
    </form>

    <script>
    // Autocompletar el campo monto con el preset elegido
    document.querySelectorAll('input[name=monto_preset]').forEach(function (radio) {
        radio.addEventListener('change', function () {
            if (this.value !== 'otro') {
                document.getElementById('monto').value = this.value;
            } else {
                document.getElementById('monto').value = '';
                document.getElementById('monto').focus();
            }
        });
    });

    function copiarAlias() {
        navigator.clipboard.writeText(document.getElementById('alias').textContent.trim());
        alert('Alias copiado');
    }

    // Adaptativo: compu muestra el QR grande, celular muestra el respaldo (guardar/copiar)
    if (window.innerWidth < 768) {
        var bq = document.getElementById('bloque-qr');
        var bc = document.getElementById('bloque-celular');
        if (bq) bq.style.display = 'none';
        if (bc) bc.style.display = 'block';
    }
    </script>
<?php endif; ?>

</body>
</html>
