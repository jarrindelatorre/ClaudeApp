-- Vuelta al Sol — Esquema MySQL (MVP)
-- Cargar en hPanel > Bases de datos > phpMyAdmin, o vía CLI:
--   mysql -u USUARIO -p NOMBRE_BASE < schema.sql

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS cumpleaneros (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    slug              VARCHAR(60)  NOT NULL UNIQUE,       -- ej: valentina-8f3a
    nombre            VARCHAR(100) NOT NULL,
    email             VARCHAR(150) NOT NULL,
    telefono          VARCHAR(30)  NULL,
    token             VARCHAR(64)  NOT NULL UNIQUE,        -- link mágico de acceso a su panel
    alias_cobro       VARCHAR(150) NOT NULL,               -- alias/cuenta/celular para mostrar como texto copiable
    qr_pago_path      VARCHAR(255) NULL,                   -- imagen del QR de cobro que subió
    selfie_path       VARCHAR(255) NULL,                   -- selfie recortada para el casco
    traje             VARCHAR(50)  NOT NULL DEFAULT 'clasico',
    monto_activacion  DECIMAL(6,2) NOT NULL DEFAULT 2.00,
    comprobante_activacion_path VARCHAR(255) NULL,
    pago_confirmado   TINYINT(1)   NOT NULL DEFAULT 0,     -- verificación manual del admin
    activo_desde      DATETIME NULL,
    activo_hasta      DATETIME NULL,
    creado_en         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token (token),
    INDEX idx_activo (activo_desde, activo_hasta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS regalos (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cumpleanero_id      INT UNSIGNED NOT NULL,
    invitado_nombre     VARCHAR(100) NULL,
    es_publico          TINYINT(1)   NOT NULL DEFAULT 1,
    texto_original      TEXT NOT NULL,          -- lo que el invitado escribió como idea de regalo
    nombre_generado     VARCHAR(150) NULL,       -- ej: "Caramelo de encebollado"
    descripcion_generada TEXT NULL,
    icono               VARCHAR(10)  NULL,       -- emoji/ícono corto
    monto               DECIMAL(6,2) NOT NULL,
    comprobante_path    VARCHAR(255) NULL,
    estado              ENUM('pendiente','confirmado') NOT NULL DEFAULT 'pendiente',
    creado_en           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cumpleanero_id) REFERENCES cumpleaneros(id) ON DELETE CASCADE,
    INDEX idx_cumpleanero (cumpleanero_id, estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
