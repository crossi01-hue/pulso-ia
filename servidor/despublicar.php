<?php
// ───────────────────────────────────────────────────────────────────────────
// despublicar.php — Radar/Pulso IA. Saca un episodio del feed por FECHA:
// borra su entrada de episodios.json y reconstruye feed.xml. NO sube nada.
//
// Uso (navegador o n8n):
//   /despublicar.php?clave=TU_LLAVE&fecha=2026-11-16
//   Opcional  &borrar_audio=1   → además borra el MP3 ep_<fecha>.mp3 (IRREVERSIBLE).
//
// Por defecto el MP3 se DEJA en el servidor: solo se quita del feed, que es lo
// que hace que Apple deje de mostrar el episodio cuando vuelve a leer el feed.
// Requiere la misma llave (RADAR_CLAVE) que subir.php / regenerar.php.
// ───────────────────────────────────────────────────────────────────────────
require __DIR__ . '/config.php';
header('Content-Type: application/json; charset=utf-8');

// --- Autenticación (igual que regenerar.php) ---
$clave = isset($_GET['clave'])
    ? $_GET['clave']
    : (isset($_SERVER['HTTP_X_API_KEY']) ? $_SERVER['HTTP_X_API_KEY'] : '');
if (!is_string($clave) || !hash_equals(RADAR_CLAVE, $clave)) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'error' => 'No autorizado']);
    exit;
}

// --- Fecha del episodio a despublicar (YYYY-MM-DD) ---
$fechaIn = isset($_GET['fecha'])
    ? $_GET['fecha']
    : (isset($_POST['fecha']) ? $_POST['fecha'] : '');
$fecha = preg_replace('/[^0-9\-]/', '', (string) $fechaIn);
if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $fecha)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Falta o es invalida la fecha (use fecha=YYYY-MM-DD)']);
    exit;
}

$dir = __DIR__;
$jsonPath = $dir . '/episodios.json';

$eps = [];
if (is_file($jsonPath)) {
    $t = json_decode(file_get_contents($jsonPath), true);
    if (is_array($t)) $eps = $t;
}

// --- Quitar la(s) entrada(s) de esa fecha ---
$antes = count($eps);
$eps = array_values(array_filter($eps, function ($e) use ($fecha) {
    return !isset($e['fecha']) || $e['fecha'] !== $fecha;
}));
$quitados = $antes - count($eps);

if ($quitados === 0) {
    http_response_code(404);
    echo json_encode([
        'ok'        => false,
        'error'     => 'No hay un episodio con esa fecha en el feed',
        'fecha'     => $fecha,
        'episodios' => count($eps),
    ]);
    exit;
}

// --- Guardar la lista y reconstruir el feed ---
usort($eps, function ($a, $b) { return strcmp($b['fecha'], $a['fecha']); });
file_put_contents($jsonPath, json_encode($eps, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
generar_feed($eps, $dir);

// --- Borrado opcional del MP3 (IRREVERSIBLE, solo si se pide explícito) ---
$nombreAudio = 'ep_' . $fecha . '.mp3';
$rutaAudio   = $dir . '/' . $nombreAudio;
$pedirBorrar = isset($_GET['borrar_audio']) ? $_GET['borrar_audio'] : (isset($_POST['borrar_audio']) ? $_POST['borrar_audio'] : '');
$audioBorrado = false;
if (($pedirBorrar === '1' || $pedirBorrar === 1) && is_file($rutaAudio)) {
    $real = realpath($rutaAudio);
    $baseDir = realpath($dir);
    // seguridad: el archivo a borrar debe estar dentro de la carpeta del podcast
    if ($real !== false && $baseDir !== false && strpos($real, $baseDir . DIRECTORY_SEPARATOR) === 0) {
        $audioBorrado = @unlink($real);
    }
}

echo json_encode([
    'ok'                      => true,
    'fecha'                   => $fecha,
    'quitados_del_feed'       => $quitados,
    'episodios_restantes'     => count($eps),
    'audio'                   => $nombreAudio,
    'audio_borrado'           => $audioBorrado,
    'audio_sigue_en_servidor' => is_file($rutaAudio),
    'nota'                    => 'Apple refresca el feed por su cuenta (de horas a ~1 dia).',
]);

// ───────────────────────────────────────────────────────────────────────────
// Mismo generador de feed que subir.php / regenerar.php (mantener IDENTICO).
function xml_esc($s) { return htmlspecialchars((string) $s, ENT_QUOTES | ENT_XML1, 'UTF-8'); }
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
