<?php
// ───────────────────────────────────────────────────────────────────────────
// config.php — Radar IA (podcast). Parámetros del feed + llave del endpoint.
// Es PHP: no se sirve como texto. Igual queda protegido por .htaccess.
// ───────────────────────────────────────────────────────────────────────────

define('RADAR_CLAVE',       'PON_AQUI_TU_LLAVE_SECRETA'); // llave secreta del endpoint
define('RADAR_BASE_URL',    'https://podcast.isaligner.com');  // sin slash final
define('RADAR_TITULO',      'Pulso IA');
define('RADAR_DESCRIPCION', 'El resumen semanal de inteligencia artificial, locutado y en español, para quien dirige un negocio. Lo esencial de la semana, sin tecnicismos, cada martes.');
define('RADAR_AUTOR',       'Isaligner');
define('RADAR_EMAIL',       'info@isaligner.com');
define('RADAR_IDIOMA',      'es-cl');
define('RADAR_PORTADA',     'portada.jpg');   // archivo en esta misma carpeta
define('RADAR_CATEGORIA',   'Technology');
