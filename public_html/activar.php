<?php
require_once __DIR__ . '/includes/functions.php';

$errores = [];
$exito = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        $nombre = trim($_POST['nombre'] ?? '');
        $email = trim($_POST['email'] ?? '');
        $telefono = trim($_POST['telefono'] ?? '');
        $aliasCobro = trim($_POST['alias_cobro'] ?? '');
        $traje = trim($_POST['traje'] ?? 'clasico');

        if ($nombre === '' || $email === '') {
            throw new RuntimeException('Nombre y email son obligatorios.');
        }
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            throw new RuntimeException('Email inválido.');
        }

        $qrPath = guardarImagenSubida('qr_pago', 'qr');
        $selfiePath = guardarImagenSubida('selfie', 'selfies');

        if ($aliasCobro === '' && !$qrPath) {
            throw new RuntimeException('Subí tu QR de cobro o escribí un alias/cuenta — necesitamos al menos uno de los dos para que te puedan pagar.');
        }

        $slug = generarSlugUnico($nombre);
        $token = generarToken();

        $stmt = db()->prepare(
            'INSERT INTO cumpleaneros
                (slug, nombre, email, telefono, token, alias_cobro, qr_pago_path, selfie_path, traje, monto_activacion)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        );
        $stmt->execute([
            $slug, $nombre, $email, $telefono ?: null, $token,
            $aliasCobro, $qrPath, $selfiePath, $traje, MONTO_ACTIVACION_DEFAULT,
        ]);

        $exito = [
            'slug' => $slug,
            'token' => $token,
        ];
    } catch (Throwable $e) {
        $errores[] = $e->getMessage();
    }
}
?>
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Activar mi cumpleaños — Vuelta al Sol</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h1>Activar mi cumpleaños</h1>

<?php if ($exito): ?>
    <p><strong>¡Listo!</strong> Tu página se creó.</p>
    <ul>
        <li>Página pública para compartir: <a href="u/<?= h($exito['slug']) ?>">/u/<?= h($exito['slug']) ?></a></li>
        <li>Tu panel privado (guardalo, es tu acceso): <a href="panel/<?= h($exito['token']) ?>">/panel/<?= h($exito['token']) ?></a></li>
    </ul>
    <p>
        Ahora falta pagar <?= h((string) MONTO_ACTIVACION_DEFAULT) ?> USD de activación
        (ver instrucciones en tu panel) — mientras tanto tu página existe pero no está activa
        para recibir regalos hasta que se confirme el pago.
    </p>
<?php else: ?>

    <?php foreach ($errores as $err): ?>
        <p style="color:red"><?= h($err) ?></p>
    <?php endforeach; ?>

    <form method="post" enctype="multipart/form-data">
        <p>
            <label>Tu nombre<br>
            <input type="text" name="nombre" required value="<?= h($_POST['nombre'] ?? '') ?>"></label>
        </p>
        <p>
            <label>Email<br>
            <input type="email" name="email" required value="<?= h($_POST['email'] ?? '') ?>"></label>
        </p>
        <p>
            <label>Teléfono (opcional)<br>
            <input type="text" name="telefono" value="<?= h($_POST['telefono'] ?? '') ?>"></label>
        </p>
        <p>
            <strong>Cómo te van a pagar</strong> — completá al menos uno de estos dos (los dos es mejor):
        </p>
        <p>
            <label>QR de cobro de tu banco (imagen)<br>
            <input type="file" name="qr_pago" accept="image/*"></label><br>
            <small>Sirve cuando quien te regala te ve desde una compu y paga con el celular.</small>
        </p>
        <p>
            <label>Alias / número de cuenta / celular (texto copiable)<br>
            <input type="text" name="alias_cobro" value="<?= h($_POST['alias_cobro'] ?? '') ?>"></label><br>
            <small>Sirve como respaldo cuando quien te regala está en su propio celular y no puede escanear su propia pantalla.</small>
        </p>
        <p>
            <label>Selfie (se recorta dentro del casco del traje)<br>
            <input type="file" name="selfie" accept="image/*"></label>
        </p>
        <p>
            <label>Traje<br>
            <select name="traje">
                <option value="clasico">Clásico</option>
                <option value="metalero">Metalero</option>
                <option value="explorador">Explorador</option>
            </select></label>
        </p>
        <p><button type="submit">Crear mi página</button></p>
    </form>
<?php endif; ?>

</body>
</html>
