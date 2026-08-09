<?php
require_once __DIR__ . '/includes/functions.php';
session_start();

// --- Login simple ---
if (isset($_POST['password'])) {
    if (hash_equals(ADMIN_PASSWORD, $_POST['password'])) {
        $_SESSION['admin_ok'] = true;
    } else {
        $errorLogin = 'Contraseña incorrecta.';
    }
}
if (isset($_GET['logout'])) {
    unset($_SESSION['admin_ok']);
}

if (empty($_SESSION['admin_ok'])) {
?>
<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Admin — Vuelta al Sol</title></head>
<body>
<h1>Admin</h1>
<?php if (!empty($errorLogin)): ?><p style="color:red"><?= h($errorLogin) ?></p><?php endif; ?>
<form method="post">
    <input type="password" name="password" placeholder="Contraseña" required>
    <button type="submit">Entrar</button>
</form>
</body></html>
<?php
    exit;
}

// --- Acción: confirmar pago de activación ---
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['confirmar_id'])) {
    $id = (int) $_POST['confirmar_id'];
    $desde = date('Y-m-d H:i:s');
    $hasta = ventanaActivaHasta();
    $stmt = db()->prepare('UPDATE cumpleaneros SET pago_confirmado = 1, activo_desde = ?, activo_hasta = ? WHERE id = ?');
    $stmt->execute([$desde, $hasta, $id]);
    header('Location: admin.php');
    exit;
}

$cumpleaneros = db()->query('SELECT * FROM cumpleaneros ORDER BY creado_en DESC')->fetchAll();
?>
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Admin — Vuelta al Sol</title></head>
<body>
<h1>Admin — Vuelta al Sol</h1>
<p><a href="?logout=1">Cerrar sesión</a></p>

<table border="1" cellpadding="6" cellspacing="0">
<tr>
    <th>Nombre</th><th>Email</th><th>Slug</th><th>Alias cobro</th>
    <th>Monto activación</th><th>Pagado</th><th>Activo hasta</th><th></th>
</tr>
<?php foreach ($cumpleaneros as $c): ?>
<tr>
    <td><?= h($c['nombre']) ?></td>
    <td><?= h($c['email']) ?></td>
    <td><a href="u/<?= h($c['slug']) ?>" target="_blank"><?= h($c['slug']) ?></a></td>
    <td><?= h($c['alias_cobro']) ?></td>
    <td><?= h((string) $c['monto_activacion']) ?></td>
    <td><?= $c['pago_confirmado'] ? '✅' : '❌' ?></td>
    <td><?= h($c['activo_hasta'] ?? '-') ?></td>
    <td>
        <?php if (!$c['pago_confirmado']): ?>
        <form method="post" style="display:inline">
            <input type="hidden" name="confirmar_id" value="<?= (int) $c['id'] ?>">
            <button type="submit">Confirmar pago y activar</button>
        </form>
        <?php endif; ?>
    </td>
</tr>
<?php endforeach; ?>
</table>

</body>
</html>
