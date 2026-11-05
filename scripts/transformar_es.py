import json, sys, uuid, base64

src, dst = sys.argv[1], sys.argv[2]
cortina_path = sys.argv[3]
with open(src, encoding="utf-8") as f:
    wf = json.load(f)
with open(cortina_path, "rb") as f:
    CORTINA_B64 = base64.b64encode(f.read()).decode("ascii")

def node(name):
    for n in wf["nodes"]:
        if n.get("name") == name:
            return n
    raise SystemExit("No existe nodo: " + name)

def uid(): return str(uuid.uuid4())

# 1) Ventana 26h -> 168h
for n in wf["nodes"]:
    jc = n.get("parameters", {}).get("jsCode")
    if isinstance(jc, str) and "const HORAS = 26;" in jc:
        n["parameters"]["jsCode"] = jc.replace("const HORAS = 26;", "const HORAS = 168;")

# 2) Renombrar disparador
for n in wf["nodes"]:
    if n.get("name") == "Cada dia 8:00":
        n["name"] = "Cada martes 8:00"
if "Cada dia 8:00" in wf["connections"]:
    wf["connections"]["Cada martes 8:00"] = wf["connections"].pop("Cada dia 8:00")

# 3a) Parse resumen: nunca dejar item sin texto legible
node("Parse resumen")["parameters"]["jsCode"] = r"""const raw = ($json.candidates && $json.candidates[0] && $json.candidates[0].content && $json.candidates[0].content.parts[0].text) || '{}';
let res = [];
try { const o = JSON.parse(raw); res = o.resumenes || (Array.isArray(o) ? o : []); } catch (e) {}
const items = ($('Body Resumen').first().json.items) || [];
return items.map((v,idx) => {
  const r = res.find(x => x && x.id === idx) || res[idx] || {};
  let resumen = (r.resumen && String(r.resumen).trim()) ? String(r.resumen).trim() : '';
  if (!resumen) { resumen = String(v.texto || v.contenido || '').trim().slice(0,240); }
  return { json: Object.assign({}, v, { titular: r.titular || v.titulo, resumen: resumen, puntos: Array.isArray(r.puntos) ? r.puntos : [] }) };
});"""

# 3b) Body Resumen: GARANTIA de salida en espanol (traducir si la fuente esta en ingles)
br = node("Body Resumen")
old = "Escribe para cada uno un resumen legible en espanol, pensado para leer en el movil sin ver el video ni abrir el articulo."
new = ("Escribe para cada uno un resumen legible en espanol (es-CL), pensado para leer en el movil sin ver el video ni abrir el articulo. "
       "IMPORTANTE: el titular, el resumen y los puntos deben quedar SIEMPRE en espanol; si el contenido de la fuente viene en ingles u otro idioma, traducelo al espanol. Ningun texto de salida puede quedar en ingles.")
if old not in br["parameters"]["jsCode"]:
    raise SystemExit("No se encontro la frase a reemplazar en Body Resumen")
br["parameters"]["jsCode"] = br["parameters"]["jsCode"].replace(old, new)

# --- Fase 4: correo semanal + boton "Ir al podcast" ---
ae = node("Armar Email")
_jc = ae["parameters"]["jsCode"]
_reps = [
    ("Lo que paso hoy en IA", "Lo de la semana en IA"),
    ("cada manana", "cada martes"),
    ("RADAR IA", "PULSO IA"),
    ("Radar IA", "Pulso IA"),
    (
        'lectura de 3 minutos</div>\n  </td></tr>\n  <tr><td class="px" style="padding:6px 24px 0;">',
        'resumen de la semana</div>\n  </td></tr>\n'
        '  <tr><td class="px" style="padding:12px 24px 2px;">\n'
        '    <a href="https://podcast.isaligner.com/" style="display:inline-block;background:#0E9A8D;color:#ffffff;font-weight:800;font-size:14px;text-decoration:none;padding:12px 20px;border-radius:10px;">\U0001F3A7 Escuchar el podcast de la semana &rarr;</a>\n'
        '  </td></tr>\n  <tr><td class="px" style="padding:6px 24px 0;">',
    ),
]
for _o, _n in _reps:
    if _o not in _jc:
        raise SystemExit("Armar Email: no se encontro -> " + _o[:40])
    _jc = _jc.replace(_o, _n)
ae["parameters"]["jsCode"] = _jc
# Asunto del correo
ev = node("Enviar Email")
ev["parameters"]["subject"] = ev["parameters"]["subject"].replace("Radar IA -", "Pulso IA -")

# 4) SPLIT de contenido: videos->Supadata (con lang=es), articulos->r.jina.ai (sin llave)
wf["nodes"] = [n for n in wf["nodes"] if n.get("name") not in ("Obtener contenido", "Normalizar contenido")]
for k in ("Obtener contenido", "Normalizar contenido"):
    wf["connections"].pop(k, None)

resp_text = {"response": {"response": {"neverError": True, "responseFormat": "text"}}}
es_video = {"parameters": {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
    "conditions": [{"id": uid(), "leftValue": "={{ $json.videoId }}", "rightValue": "",
        "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}}], "combinator": "and"}, "options": {}},
    "id": uid(), "name": "Es video?", "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [2240, 560]}
sup_options = {"response": {"response": {"neverError": True, "responseFormat": "text"}},
               "batching": {"batch": {"batchSize": 1, "batchInterval": 1500}}}  # <=1 llamada / 1.5s (limite Free = 1/s)
transcript_supadata = {"parameters": {
    "url": "=https://api.supadata.ai/v1/youtube/transcript?url={{ encodeURIComponent($json.link) }}&text=true&mode=auto&lang=es",
    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth", "options": sup_options},
    "id": uid(), "name": "Transcript Supadata", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
    "position": [2464, 480], "onError": "continueRegularOutput",
    "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 2000,  # reintenta fallos pasajeros
    "credentials": {"httpHeaderAuth": {"id": "qTCpnB49XEyyBaDj", "name": "Supadata"}}}
norm_video = {"parameters": {"mode": "runOnceForEachItem", "jsCode": r"""const v = $('Parse seleccion').item.json;
const raw = $json.data || '';
let texto = '';
try { const o = JSON.parse(raw); texto = o.content || o.transcript || ''; } catch (e) { texto = ''; }
texto = String(texto || '').trim();
if (!texto) { texto = String(v.texto || '').trim(); }
return { json: Object.assign({}, v, { contenido: texto.slice(0, 6000) }) };"""},
    "id": uid(), "name": "Norm video", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [2688, 480]}
leer_articulo = {"parameters": {"url": "=https://r.jina.ai/{{ $json.link }}", "options": resp_text},
    "id": uid(), "name": "Leer articulo", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
    "position": [2464, 640], "onError": "continueRegularOutput"}
norm_articulo = {"parameters": {"mode": "runOnceForEachItem", "jsCode": r"""const v = $('Parse seleccion').item.json;
const raw = $json.data || '';
let texto = String(typeof raw === 'string' ? raw : '').trim();
if (!texto) { texto = String(v.texto || '').trim(); }
return { json: Object.assign({}, v, { contenido: texto.slice(0, 6000) }) };"""},
    "id": uid(), "name": "Norm articulo", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [2688, 640]}
unir = {"parameters": {"numberInputs": 2}, "id": uid(), "name": "Unir contenido",
    "type": "n8n-nodes-base.merge", "typeVersion": 3, "position": [2912, 560]}
wf["nodes"].extend([es_video, transcript_supadata, norm_video, leer_articulo, norm_articulo, unir])
wf["connections"]["Parse seleccion"] = {"main": [[{"node": "Es video?", "type": "main", "index": 0}]]}
wf["connections"]["Es video?"] = {"main": [
    [{"node": "Transcript Supadata", "type": "main", "index": 0}],
    [{"node": "Leer articulo", "type": "main", "index": 0}]]}
wf["connections"]["Transcript Supadata"] = {"main": [[{"node": "Norm video", "type": "main", "index": 0}]]}
wf["connections"]["Norm video"] = {"main": [[{"node": "Unir contenido", "type": "main", "index": 0}]]}
wf["connections"]["Leer articulo"] = {"main": [[{"node": "Norm articulo", "type": "main", "index": 0}]]}
wf["connections"]["Norm articulo"] = {"main": [[{"node": "Unir contenido", "type": "main", "index": 1}]]}
wf["connections"]["Unir contenido"] = {"main": [[{"node": "Body Resumen", "type": "main", "index": 0}]]}

# 5) Rama del guion (con garantia de espanol)
body_guion_js = r"""const items = $input.all().map(i => i.json);
const fmt = d => new Date(d).toLocaleDateString('es-CL', { day:'2-digit', month:'long' });
const fechaFin = new Date();
const fechaIni = new Date(Date.now() - 7*24*3600*1000);
const lista = items.map((v, idx) => ({
  id: idx,
  origen: v.origen,
  titular: v.titular || v.titulo,
  contenido: String(v.contenido || v.texto || '').slice(0, 5000)
}));
const prompt = `Eres el guionista y locutor editorial de un podcast semanal en espanol sobre inteligencia artificial, dirigido a profesionales NO tecnicos (duenos de negocio, gerentes, personas con poco tiempo). Conviertes el material de la semana (del ${fmt(fechaIni)} al ${fmt(fechaFin)}) en un guion locutado, calido y con criterio propio, listo para leerse en voz alta.

RECIBES una lista (JSON) de items ya seleccionados de la semana. Cada item trae ORIGEN, TITULAR y CONTENIDO (texto completo de la fuente). Trabaja SIEMPRE sobre el contenido, no solo el titular. OJO: parte del contenido puede venir en ingles; en ese caso traducelo. TODO el guion se escribe en espanol (es-CL), sin dejar ninguna palabra ni frase en ingles (salvo nombres propios de productos o empresas).

QUE DEBES PRODUCIR: un unico guion locutado en espanol, autocontenido, para unos 8 a 9 minutos de audio (1300 a 1600 palabras).

LA VARA DE CALIDAD (lo mas importante): prioriza lo genuinamente interesante (impacto real, novedad, relevancia para quien dirige un negocio o una clinica). Si un item es flojo, repetido o irrelevante, DESCARTALO aunque venga en la lista. Mejor 4 temas buenos que 8 mediocres. De cada tema explica el "y esto por que me importa?". Nunca te quedes en el dato suelto.

ESTRUCTURA: 1) Saludo breve mas "la foto de la semana" en 1-2 frases (menciona el rango de fechas). 2) Los 3 temas mas importantes, a fondo, con transiciones naturales: que paso (en simple) y por que importa. 3) Barrido rapido: "y en un minuto, el resto de la semana", 3 a 5 titulares de una frase. 4) Cierre: 2 o 3 ideas para llevarse. 5) Despedida ("nos escuchamos la proxima semana").

PAUSAS DE PUBLICIDAD (obligatorio): inserta EXACTAMENTE dos marcas, cada una sola en su linea, en puntos naturales y bien separados: [PAUSA_PUBLICIDAD_1] justo despues del primer tema a fondo, y [PAUSA_PUBLICIDAD_2] justo antes del cierre. NO escribas el texto de la publicidad, solo coloca las marcas.

REGLAS DE ESTILO: espanol hablado, calido y cercano, sin tecnicismos innecesarios (explica toda sigla la primera vez). SIN links, SIN "ve a la fuente", SIN "segun el articulo o video", es 100% autocontenido. Numeros faciles de leer en voz alta (ej.: "diecisiete mil millones de dolares", no la cifra con todos los ceros). Nada de emojis, titulos, vinetas, nombres de seccion ni acotaciones de escena dentro del texto: solo lo que se va a leer en voz alta, mas las dos marcas de pausa. No inventes datos ni cifras; si algo no esta en el material, no lo menciones; si una cifra es dudosa o las fuentes no coinciden, usa lenguaje cualitativo ("del orden de", "cerca de"). Tono equilibrado, ni alarmista ni publicitario.

SALIDA: devuelve UNICAMENTE el texto del guion en espanol (con las dos marcas de pausa en su linea). Nada antes ni despues.

Items: ` + JSON.stringify(lista);
return [{ json: { body: { contents: [ { parts: [ { text: prompt } ] } ], generationConfig: { temperature: 0.55, maxOutputTokens: 8192 } } } }];"""
parse_guion_js = r"""const c = $json.candidates && $json.candidates[0] && $json.candidates[0].content;
const raw = (c && c.parts && c.parts[0] && c.parts[0].text) || '';
return [{ json: { guion: String(raw).trim() } }];"""
wf["nodes"].extend([
    {"parameters": {"jsCode": body_guion_js}, "id": uid(), "name": "Body Guion",
     "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [3360, 420]},
    {"parameters": {"method": "POST",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ $json.body }}", "options": {}},
     "id": uid(), "name": "Gemini Guion", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [3584, 420], "credentials": {"httpHeaderAuth": {"id": "ACCvb79mY219gpB1", "name": "x-goog-api-key"}}},
    {"parameters": {"jsCode": parse_guion_js}, "id": uid(), "name": "Parse guion",
     "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [3808, 420]},
])
wf["connections"].setdefault("Parse resumen", {"main": [[]]})
wf["connections"]["Parse resumen"]["main"][0].append({"node": "Body Guion", "type": "main", "index": 0})
wf["connections"]["Body Guion"] = {"main": [[{"node": "Gemini Guion", "type": "main", "index": 0}]]}
wf["connections"]["Gemini Guion"] = {"main": [[{"node": "Parse guion", "type": "main", "index": 0}]]}

# --- 7) FASE 2 (tramo 1): audio = voz Victoria + cuñas, pegados en un MP3 (sin cortina aun) ---
partir_guion_js = r'''const guion = ($input.first() && $input.first().json.guion) || '';
const CUNA1 = 'Una pausa, de la mano de Isaligner: alineadores invisibles con especialistas en ortodoncia, en Providencia y Los Ángeles. Convenios con seguros y facilidades de pago.';
const CUNA2 = 'Antes de terminar: Isaligner, tu sonrisa alineada sin complicarte. Agenda en isaligner punto com o escríbenos en Instagram, arroba isaligner. Te esperamos en Providencia y Los Ángeles.';
let seg1 = guion, seg2 = '', seg3 = '';
const M1 = '[PAUSA_PUBLICIDAD_1]', M2 = '[PAUSA_PUBLICIDAD_2]';
const i1 = guion.indexOf(M1), i2 = guion.indexOf(M2);
if (i1 >= 0 && i2 > i1) {
  seg1 = guion.slice(0, i1);
  seg2 = guion.slice(i1 + M1.length, i2);
  seg3 = guion.slice(i2 + M2.length);
}
const limpia = s => String(s).replace(/\[PAUSA_PUBLICIDAD_\d\]/g, '').trim();
const voice = { stability: 0.5, similarity_boost: 0.75, style: 0.0, use_speaker_boost: true };
const piezas = [
  { tipo: 'narracion', texto: limpia(seg1) },
  { tipo: 'cuna', texto: CUNA1 },
  { tipo: 'narracion', texto: limpia(seg2) },
  { tipo: 'cuna', texto: CUNA2 },
  { tipo: 'narracion', texto: limpia(seg3) }
].filter(p => p.texto && p.texto.length > 0);
return piezas.map((p, idx) => ({ json: { orden: idx, tipo: p.tipo, texto: p.texto, body: { text: p.texto, model_id: 'eleven_multilingual_v2', voice_settings: voice } } }));'''

unir_audio_js = r'''const items = $input.all();
const piezas = $('Partir guion').all().map(p => p.json);
let cortIdx = -1;
for (let i = 0; i < items.length; i++) { if (items[i].json && items[i].json.tipo === 'cortina') { cortIdx = i; break; } }
if (cortIdx < 0) cortIdx = items.length - 1;
const getBuf = async (i) => {
  const bin = (items[i] && items[i].binary) || {};
  const props = Object.keys(bin);
  const prop = props.indexOf('data') >= 0 ? 'data' : props[0];
  if (!prop) return Buffer.alloc(0);
  let b = null;
  try { b = await this.helpers.getBinaryDataBuffer(i, prop); } catch (e) {}
  if ((!b || !b.length) && bin[prop] && bin[prop].data) { try { b = Buffer.from(bin[prop].data, 'base64'); } catch (e) {} }
  return (b && b.length) ? b : Buffer.alloc(0);
};
const cortBuf = await getBuf(cortIdx);
const segIdx = [];
for (let i = 0; i < items.length; i++) { if (i !== cortIdx) segIdx.push(i); }
const partes = [];
for (let k = 0; k < segIdx.length; k++) {
  const tipo = (piezas[k] && piezas[k].tipo) || 'narracion';
  const buf = await getBuf(segIdx[k]);
  if (!buf.length) continue;
  if (tipo === 'cuna') {
    if (cortBuf.length) partes.push(cortBuf);
    partes.push(buf);
    if (cortBuf.length) partes.push(cortBuf);
  } else {
    partes.push(buf);
  }
}
const merged = Buffer.concat(partes);
const fecha = new Date().toISOString().slice(0,10);
let titulares = [];
try { titulares = $('Parse resumen').all().map(p => (p.json && p.json.titular) ? p.json.titular : '').filter(Boolean).slice(0,6); } catch (e) {}
const duracion = Math.round(merged.length * 8 / 128000);
const titulo = 'Pulso IA · ' + fecha;
const descripcion = titulares.length
  ? ('Resumen semanal de inteligencia artificial. En este episodio: ' + titulares.join(' · ') + '.')
  : 'Resumen semanal de inteligencia artificial.';
const out = { json: { fecha: fecha, titulo: titulo, descripcion: descripcion, duracion: duracion, segmentos: segIdx.length, bytes: merged.length } };
if (merged.length) {
  out.binary = { data: await this.helpers.prepareBinaryData(merged, 'episodio_' + fecha + '.mp3', 'audio/mpeg') };
}
return [out];'''

cortina_js = ("const b64 = '" + CORTINA_B64 + "';\n"
              "const buf = Buffer.from(b64, 'base64');\n"
              "const bin = await this.helpers.prepareBinaryData(buf, 'cortina.mp3', 'audio/mpeg');\n"
              "return [{ json: { tipo: 'cortina' }, binary: { data: bin } }];")

wf["nodes"].extend([
    {"parameters": {"jsCode": partir_guion_js}, "id": uid(), "name": "Partir guion",
     "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [4032, 300]},
    {"parameters": {"method": "POST",
        "url": "https://api.elevenlabs.io/v1/text-to-speech/Fd38GRHtJllY0CuguAy9",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ $json.body }}",
        "options": {"response": {"response": {"responseFormat": "file"}},
                    "batching": {"batch": {"batchSize": 1, "batchInterval": 1200}}}},
     "id": uid(), "name": "TTS ElevenLabs", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [4256, 300], "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 2000,
     "credentials": {"httpHeaderAuth": {"id": "AcogU8Vd9HuIPkyY", "name": "ElevenLabs"}}},
    {"parameters": {"jsCode": cortina_js}, "id": uid(), "name": "Cortina",
     "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [4256, 540]},
    {"parameters": {"numberInputs": 2}, "id": uid(), "name": "Juntar audio",
     "type": "n8n-nodes-base.merge", "typeVersion": 3, "position": [4480, 420]},
    {"parameters": {"jsCode": unir_audio_js}, "id": uid(), "name": "Unir audio",
     "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [4704, 420]},
    {"parameters": {
        "method": "POST", "url": "https://podcast.isaligner.com/subir.php",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "contentType": "multipart-form-data",
        "bodyParameters": {"parameters": [
            {"parameterType": "formBinaryData", "name": "audio", "inputDataFieldName": "data"},
            {"name": "titulo", "value": "={{ $json.titulo }}"},
            {"name": "descripcion", "value": "={{ $json.descripcion }}"},
            {"name": "fecha", "value": "={{ $json.fecha }}"},
            {"name": "duracion", "value": "={{ $json.duracion }}"}
        ]}, "options": {}},
     "id": uid(), "name": "Publicar episodio", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [4928, 420], "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 3000,
     "credentials": {"httpHeaderAuth": {"id": "VmOh5mO6Pm0adSpu", "name": "Radar Podcast"}}},
])
wf["connections"]["Parse guion"] = {"main": [[
    {"node": "Partir guion", "type": "main", "index": 0},
    {"node": "Cortina", "type": "main", "index": 0}]]}
wf["connections"]["Partir guion"] = {"main": [[{"node": "TTS ElevenLabs", "type": "main", "index": 0}]]}
wf["connections"]["TTS ElevenLabs"] = {"main": [[{"node": "Juntar audio", "type": "main", "index": 0}]]}
wf["connections"]["Cortina"] = {"main": [[{"node": "Juntar audio", "type": "main", "index": 1}]]}
wf["connections"]["Juntar audio"] = {"main": [[{"node": "Unir audio", "type": "main", "index": 0}]]}
wf["connections"]["Unir audio"] = {"main": [[{"node": "Publicar episodio", "type": "main", "index": 0}]]}

wf["name"] = "Radar IA (candidato CONSOLIDADO - semanal + podcast + audio) OFF"
wf["active"] = False
for k in ("id", "versionId", "meta"):
    wf.pop(k, None)
with open(dst, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)
print("OK ->", dst, "| nodos:", len(wf["nodes"]))
