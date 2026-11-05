<?php
// index.php — Radar IA. Página "Ir al podcast": portada, suscripción y episodios.
require __DIR__ . '/config.php';
$eps = [];
$jsonPath = __DIR__ . '/episodios.json';
if (is_file($jsonPath)) {
    $t = json_decode(file_get_contents($jsonPath), true);
    if (is_array($t)) $eps = $t;
}
function h($s) { return htmlspecialchars((string) $s, ENT_QUOTES, 'UTF-8'); }
function mins($seg) { $m = (int) round(((int) $seg) / 60); return $m > 0 ? ($m . ' min') : ''; }
$host = parse_url(RADAR_BASE_URL, PHP_URL_HOST);
?>
<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= h(RADAR_TITULO) ?></title>
<meta name="description" content="<?= h(RADAR_DESCRIPCION) ?>">
<style>
  :root{ --bg:#0b1726; --card:#122236; --line:#223247; --teal:#18B3A6; --text:#e8eef6; --muted:#9fb0c3; }
  *{box-sizing:border-box} html,body{margin:0}
  body{background:var(--bg);color:var(--text);font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5}
  .wrap{max-width:780px;margin:0 auto;padding:30px 18px 70px}
  .head{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
  .cover{width:160px;height:160px;border-radius:16px;flex-shrink:0;box-shadow:0 10px 34px rgba(0,0,0,.45)}
  h1{margin:0 0 6px;font-size:30px}
  .desc{color:var(--muted);font-size:15px;margin:0 0 14px;max-width:460px}
  .subs{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
  .btn{display:inline-block;background:var(--teal);color:#04211f;text-decoration:none;font-weight:800;font-size:13.5px;padding:11px 18px;border-radius:10px}
  .btn.ghost{background:transparent;border:1px solid var(--line);color:var(--text);font-weight:600}
  .feedbox{margin-top:14px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;font-size:13px;color:var(--muted)}
  .feedbox code{color:var(--text);word-break:break-all}
  h2{font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin:30px 0 8px}
  .ep{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-top:14px}
  .ep h3{margin:0 0 3px;font-size:17px}
  .ep .meta{color:var(--muted);font-size:12.5px}
  .ep p{color:#c7d4e3;font-size:14px;margin:9px 0 2px}
  audio{width:100%;margin-top:10px}
  .foot{color:#6b7c90;font-size:12px;margin-top:34px;text-align:center}
</style></head>
<body><div class="wrap">
  <div class="head">
    <img class="cover" src="<?= h(RADAR_PORTADA) ?>" alt="<?= h(RADAR_TITULO) ?>">
    <div>
      <h1><?= h(RADAR_TITULO) ?></h1>
      <p class="desc"><?= h(RADAR_DESCRIPCION) ?></p>
      <div class="subs">
        <a class="btn" href="podcast://<?= h($host) ?>/feed.xml">Suscribirse</a>
        <a class="btn ghost" href="feed.xml">Ver feed RSS</a>
      </div>
      <div class="feedbox">¿Tu app no abrió sola? Pega este feed en Pocket Casts, Apple Podcasts, etc.:<br><code><?= h(RADAR_BASE_URL) ?>/feed.xml</code></div>
    </div>
  </div>

  <h2>Episodios</h2>
  <?php if (!$eps): ?>
    <div class="ep"><p>Aún no hay episodios. Vuelve pronto.</p></div>
  <?php else: foreach ($eps as $e): $url = RADAR_BASE_URL . '/' . $e['archivo']; ?>
    <div class="ep">
      <h3><?= h($e['titulo']) ?></h3>
      <div class="meta"><?= h($e['fecha']) ?><?php if (mins($e['duracion'] ?? 0)): ?> &middot; <?= h(mins($e['duracion'])) ?><?php endif; ?></div>
      <?php if (!empty($e['descripcion'])): ?><p><?= h($e['descripcion']) ?></p><?php endif; ?>
      <audio controls preload="none" src="<?= h($url) ?>"></audio>
    </div>
  <?php endforeach; endif; ?>

  <div class="foot"><?= h(RADAR_TITULO) ?> · por <?= h(RADAR_AUTOR) ?></div>
</div></body></html>
