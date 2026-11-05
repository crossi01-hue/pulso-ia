<?php
// ───────────────────────────────────────────────────────────────────────────
// regenerar.php — Radar/Pulso IA. Reconstruye feed.xml desde episodios.json
// con el título actual de config.php, SIN publicar un episodio nuevo.
// Uso (una vez tras cambiar el nombre):  /regenerar.php?clave=TU_LLAVE
// También normaliza los títulos de episodios viejos al nombre actual.
// ───────────────────────────────────────────────────────────────────────────
require __DIR__ . '/config.php';
header('Content-Type: text/plain; charset=utf-8');

$clave = isset($_GET['clave']) ? $_GET['clave'] : (isset($_SERVER['HTTP_X_API_KEY']) ? $_SERVER['HTTP_X_API_KEY'] : '');
if (!is_string($clave) || !hash_equals(RADAR_CLAVE, $clave)) {
    http_response_code(403);
    exit('No autorizado');
}

$dir = __DIR__;
$jsonPath = $dir . '/episodios.json';
$eps = [];
if (is_file($jsonPath)) {
    $t = json_decode(file_get_contents($jsonPath), true);
    if (is_array($t)) $eps = $t;
}

// Normalizar títulos viejos ("Radar IA · ..." / "Pulso IA · ...") al nombre actual
$cambiado = false;
foreach ($eps as $i => $e) {
    if (isset($e['titulo'])) {
        $nuevo = preg_replace('/^(Radar IA|Pulso IA)/u', RADAR_TITULO, $e['titulo']);
        if ($nuevo !== $e['titulo']) { $eps[$i]['titulo'] = $nuevo; $cambiado = true; }
    }
}
if ($cambiado) {
    file_put_contents($jsonPath, json_encode($eps, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

generar_feed($eps, $dir);
echo "OK — feed.xml regenerado con titulo: " . RADAR_TITULO . " (" . count($eps) . " episodios)";

// ───────────────────────────────────────────────────────────────────────────
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
