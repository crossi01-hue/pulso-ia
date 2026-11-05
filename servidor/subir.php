<?php
// ───────────────────────────────────────────────────────────────────────────
// subir.php — Radar IA. Recibe el MP3 del episodio (desde n8n), lo guarda y
// regenera feed.xml. Requiere la llave en la cabecera X-Api-Key.
// Envío esperado: POST multipart/form-data con:
//   - campo archivo  "audio"       (el MP3)
//   - campos texto   "titulo", "descripcion", "fecha" (YYYY-MM-DD), "duracion" (seg, opcional)
// ───────────────────────────────────────────────────────────────────────────
require __DIR__ . '/config.php';
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Metodo no permitido']);
    exit;
}

// --- Autenticación ---
$clave = isset($_SERVER['HTTP_X_API_KEY']) ? $_SERVER['HTTP_X_API_KEY'] : '';
if (!is_string($clave) || !hash_equals(RADAR_CLAVE, $clave)) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'error' => 'No autorizado']);
    exit;
}

$dir = __DIR__;

// --- Metadatos ---
$fecha = isset($_POST['fecha']) ? preg_replace('/[^0-9\-]/', '', $_POST['fecha']) : '';
if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $fecha)) {
    $fecha = date('Y-m-d');
}
$titulo = (isset($_POST['titulo']) && trim($_POST['titulo']) !== '')
    ? trim($_POST['titulo'])
    : ('Radar IA · ' . $fecha);
$descripcion = isset($_POST['descripcion']) ? trim($_POST['descripcion']) : '';

// --- Recibir el audio ---
if (!isset($_FILES['audio']) || $_FILES['audio']['error'] !== UPLOAD_ERR_OK) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Falta el archivo de audio (campo "audio")']);
    exit;
}
$nombreArchivo = 'ep_' . $fecha . '.mp3';
$destino = $dir . '/' . $nombreArchivo;
if (!move_uploaded_file($_FILES['audio']['tmp_name'], $destino)) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'No se pudo guardar el audio']);
    exit;
}
$bytes = filesize($destino);
$dur = (isset($_POST['duracion']) && intval($_POST['duracion']) > 0)
    ? intval($_POST['duracion'])
    : (int) round($bytes * 8 / 128000); // estimación a 128 kbps

// --- Actualizar lista de episodios ---
$jsonPath = $dir . '/episodios.json';
$eps = [];
if (is_file($jsonPath)) {
    $tmp = json_decode(file_get_contents($jsonPath), true);
    if (is_array($tmp)) $eps = $tmp;
}
// quitar una re-subida de la misma fecha
$eps = array_values(array_filter($eps, function ($e) use ($fecha) {
    return !isset($e['fecha']) || $e['fecha'] !== $fecha;
}));
$eps[] = [
    'fecha'       => $fecha,
    'titulo'      => $titulo,
    'descripcion' => $descripcion,
    'archivo'     => $nombreArchivo,
    'bytes'       => $bytes,
    'duracion'    => $dur,
    'ts'          => time(),
];
usort($eps, function ($a, $b) { return strcmp($b['fecha'], $a['fecha']); });
file_put_contents($jsonPath, json_encode($eps, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

generar_feed($eps, $dir);

echo json_encode([
    'ok'         => true,
    'archivo'    => $nombreArchivo,
    'url'        => RADAR_BASE_URL . '/' . $nombreArchivo,
    'episodios'  => count($eps),
]);

// ───────────────────────────────────────────────────────────────────────────
function xml_esc($s) {
    return htmlspecialchars((string) $s, ENT_QUOTES | ENT_XML1, 'UTF-8');
}
function hms($seg) {
    $seg = max(0, (int) $seg);
    return sprintf('%02d:%02d:%02d', floor($seg / 3600), floor(($seg % 3600) / 60), $seg % 60);
}
function generar_feed($eps, $dir) {
    $base    = RADAR_BASE_URL;
    $portada = $base . '/' . RADAR_PORTADA;
    $ahora   = gmdate('D, d M Y H:i:s') . ' +0000';

    $x  = '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
    $x .= '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">' . "\n";
    $x .= "<channel>\n";
    $x .= '<title>' . xml_esc(RADAR_TITULO) . "</title>\n";
    $x .= '<link>' . xml_esc($base) . "</link>\n";
    $x .= '<language>' . xml_esc(RADAR_IDIOMA) . "</language>\n";
    $x .= '<description>' . xml_esc(RADAR_DESCRIPCION) . "</description>\n";
    $x .= '<itunes:author>' . xml_esc(RADAR_AUTOR) . "</itunes:author>\n";
    $x .= '<itunes:summary>' . xml_esc(RADAR_DESCRIPCION) . "</itunes:summary>\n";
    $x .= "<itunes:explicit>false</itunes:explicit>\n";
    $x .= "<itunes:type>episodic</itunes:type>\n";
    $x .= '<itunes:image href="' . xml_esc($portada) . "\"/>\n";
    $x .= '<image><url>' . xml_esc($portada) . '</url><title>' . xml_esc(RADAR_TITULO) . '</title><link>' . xml_esc($base) . "</link></image>\n";
    $x .= '<itunes:category text="' . xml_esc(RADAR_CATEGORIA) . "\"/>\n";
    $x .= '<itunes:owner><itunes:name>' . xml_esc(RADAR_AUTOR) . '</itunes:name><itunes:email>' . xml_esc(RADAR_EMAIL) . "</itunes:email></itunes:owner>\n";
    $x .= '<lastBuildDate>' . $ahora . "</lastBuildDate>\n";

    foreach ($eps as $e) {
        $url = $base . '/' . $e['archivo'];
        $pub = gmdate('D, d M Y H:i:s', strtotime($e['fecha'] . ' 08:00:00')) . ' +0000';
        $x .= "<item>\n";
        $x .= '<title>' . xml_esc($e['titulo']) . "</title>\n";
        $x .= '<description>' . xml_esc($e['descripcion']) . "</description>\n";
        $x .= '<enclosure url="' . xml_esc($url) . '" length="' . intval($e['bytes']) . "\" type=\"audio/mpeg\"/>\n";
        $x .= '<guid isPermaLink="false">' . xml_esc($url) . "</guid>\n";
        $x .= '<pubDate>' . $pub . "</pubDate>\n";
        $x .= '<itunes:duration>' . hms($e['duracion']) . "</itunes:duration>\n";
        $x .= "<itunes:explicit>false</itunes:explicit>\n";
        $x .= "</item>\n";
    }
    $x .= "</channel>\n</rss>\n";
    file_put_contents($dir . '/feed.xml', $x);
}
