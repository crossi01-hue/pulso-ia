# Pulso IA — Boletín semanal de inteligencia artificial (correo + podcast)

Proyecto **independiente** de la clínica Isaligner. Resume cada semana lo más
importante de IA y lo entrega en **dos formatos**: un correo HTML y un **podcast
locutado** (voz chilena) publicado en un feed RSS propio.

- **Cadencia:** semanal, martes 08:00 (America/Santiago).
- **Correo:** se mantiene el que ya funcionaba, ahora semanal y con botón "Ir al podcast".
- **Podcast:** `https://podcast.isaligner.com/` (feed: `/feed.xml`).

## Arquitectura (n8n → servidor → apps)

```
n8n (flujo "Radar IA"):
  Ingesta (YouTube + RSS labs + Hacker News, ventana 7 días)
    → Selección (Gemini, máx. 2 por origen, 6–8 ítems)
    → Contenido:  videos → Supadata (mode=auto, lang=es) | artículos → r.jina.ai
    → Resumen por ítem (Gemini, siempre en español)
    → RAMA CORREO:   Armar Email → Enviar Email (BCC a la lista)
    → RAMA PODCAST:  Guion (Gemini) → TTS ElevenLabs (voz Victoria) +
                     cortina + 2 cuñas Isaligner → 1 MP3 → POST a subir.php
HostGator (podcast.isaligner.com):
  subir.php guarda el MP3 y regenera feed.xml → Pocket Casts / Apple / etc.
```

## Componentes

| Dónde | Archivo | Qué hace |
|---|---|---|
| Servidor | `servidor/subir.php` | Recibe el MP3 (llave `X-Api-Key`), lo guarda, regenera `feed.xml` |
| Servidor | `servidor/regenerar.php` | Reconstruye `feed.xml` desde `episodios.json` sin publicar (p. ej. tras cambiar el nombre) |
| Servidor | `servidor/index.php` | Página pública "Ir al podcast" (portada, reproductor, suscribir) |
| Servidor | `servidor/config.php` | Título, descripción, llave, etc. **(contiene secreto — no subir a git)** |
| Servidor | `servidor/.htaccess` | Protege `config.php` y `episodios.json` |
| Servidor | `servidor/feed.xml` | Feed RSS (se regenera solo) |
| Assets | `portada.jpg` | Portada 2000×2000 |
| Assets | `audio/cortina_tech_sobria.mp3` | Cortina (va embebida en el flujo n8n) |
| n8n | `n8n/Radar_IA_CONSOLIDADO_OFF.json` | Flujo completo (apagado, para importar) |
| Scripts | `scripts/*.py` | Generadores (portada, cortina, armado del flujo) |

Ruta en HostGator: `/home2/isalign1/podcast.isaligner.com/`

## Credenciales que usa el flujo (en n8n, no en el código)

- **Gemini** (selección, resumen, guion) — Header Auth `x-goog-api-key`.
- **Supadata** (transcripción de videos) — Header Auth `x-api-key`. Plan Free.
- **ElevenLabs** (voz) — Header Auth `xi-api-key`. Plan Starter. Voz: Victoria (Chile) `Fd38GRHtJllY0CuguAy9`.
- **Pulso IA / Podcast** (subir episodio) — Header Auth `X-Api-Key` = `RADAR_CLAVE` de `config.php`.

## Operaciones frecuentes

- **Cambiar nombre/portada/descripción:** editar `config.php`, re-subir, y abrir
  `regenerar.php?clave=...` una vez.
- **Publicar un episodio a mano:** ejecutar el nodo *Publicar episodio* en n8n.
- **Puesta en marcha:** encender el flujo semanal y apagar el diario viejo (en n8n).

> Nota de seguridad: `config.php` lleva la llave del endpoint. El `.gitignore`
> la excluye; en el repo va `config.sample.php` con un marcador.
