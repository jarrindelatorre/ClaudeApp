#!/usr/bin/env python3
"""Agente de noticias para redacciones.

Lee los feeds RSS de fuentes.json, descarta las notas que un mismo medio vuelve
a publicar (cada medio conserva su versión), las clasifica por categoría, publica docs/noticias.json (lo consume el
tablero web docs/index.html) y envía las más relevantes a Telegram.

Uso:
    python agente.py                 # corre completo
    python agente.py --sin-telegram  # solo genera el tablero
    python agente.py --fuentes otro.json

Variables de entorno para Telegram: TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import feedparser

RAIZ = Path(__file__).resolve().parent
SALIDA_JSON = RAIZ / "docs" / "noticias.json"
ESTADO = RAIZ / "data" / "enviadas.json"
AGENTE_HTTP = "Mozilla/5.0 (compatible; AgenteNoticias/1.0; +lector RSS)"

AJUSTES_BASE = {
    "horas_ventana": 24,           # antigüedad máxima de una noticia
    "max_resumen": 280,            # caracteres del resumen
    "max_tablero": 400,            # noticias en el tablero web
    "telegram_max_por_categoria": 4,
    "telegram_max_por_corrida": 20,
    "telegram_pausa_segundos": 3,  # Telegram limita ~20 mensajes/minuto por grupo
    "similitud_mismo_medio": 0.6,  # 0-1: desde aquí es la misma nota republicada
    "similitud_entre_medios": 0.5, # 0-1: desde aquí dos medios hablan del mismo hecho
    "dias_memoria": 7,             # cuánto recordar lo ya enviado
}

PALABRAS_VACIAS = set(
    """a al algo ante con contra como de del desde donde el la las lo los en entre
    es esta este esto fue ha han hay mas más para pero por que qué se sin sobre su
    sus tras un una uno unos unas y ya o e ni no si sí le les tiene tienen ser son
    the of and to in on for with at by from is are was a an as its it this that
    """.split()
)

ICONOS = {
    "Política": "🏛", "Economía": "💰", "Seguridad": "🚨", "Deportes": "⚽",
    "Mundo": "🌎", "Tecnología": "💻", "Salud": "🩺", "Cultura": "🎭",
    "Sociedad": "👥", "General": "📰",
}


# ---------------------------------------------------------------- texto ----

def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos; para comparar y buscar palabras."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9ñ]+", texto))


def limpiar_html(texto: str) -> str:
    texto = re.sub(r"(?is)<(script|style).*?</\1>", " ", texto or "")
    texto = re.sub(r"(?s)<[^>]+>", " ", texto)
    return re.sub(r"\s+", " ", html.unescape(texto)).strip()


def recortar(texto: str, limite: int) -> str:
    if len(texto) <= limite:
        return texto
    corte = texto[:limite].rsplit(" ", 1)[0].rstrip(" ,;:.")
    return corte + "…"


def fichas_titulo(titulo: str) -> frozenset[str]:
    return frozenset(
        p for p in normalizar(titulo).split() if len(p) > 2 and p not in PALABRAS_VACIAS
    )


# ---------------------------------------------------------------- feeds ----

def descargar(url: str) -> bytes:
    pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE_HTTP})
    with urllib.request.urlopen(pedido, timeout=25) as r:
        return r.read()


def imagen_de(entrada) -> str | None:
    candidatos = []
    for clave in ("media_content", "media_thumbnail"):
        for m in entrada.get(clave) or []:
            tipo = m.get("type", "") or ""
            if m.get("url") and (not tipo or tipo.startswith("image")
                                 or m.get("medium") == "image"):
                candidatos.append(m["url"])
    for enlace in entrada.get("links") or []:
        if enlace.get("rel") == "enclosure" and (enlace.get("type") or "").startswith("image"):
            candidatos.append(enlace.get("href"))
    cuerpo = entrada.get("summary", "") or ""
    for c in entrada.get("content") or []:
        cuerpo += " " + (c.get("value") or "")
    encontrado = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', cuerpo, re.I)
    if encontrado:
        candidatos.append(html.unescape(encontrado.group(1)))
    for url in candidatos:
        if url and url.startswith("http"):
            return url
    return None


def leer_fuente(fuente: dict, ahora: float, ajustes: dict) -> tuple[list[dict], str | None]:
    """Devuelve (noticias, error). Nunca lanza: una fuente caída no frena al resto."""
    try:
        feed = feedparser.parse(descargar(fuente["url"]))
    except Exception as e:  # red, DNS, HTTP 4xx/5xx, tiempo de espera
        return [], f"{type(e).__name__}: {e}"
    if not feed.entries:
        return [], "el feed no trae noticias (¿URL cambiada?)"

    limite = ahora - ajustes["horas_ventana"] * 3600
    noticias = []
    for e in feed.entries:
        titulo = limpiar_html(e.get("title", ""))
        enlace = (e.get("link") or "").strip()
        if not titulo or not enlace.startswith("http"):
            continue
        fecha_tupla = e.get("published_parsed") or e.get("updated_parsed")
        fecha = calendar.timegm(fecha_tupla) if fecha_tupla else ahora
        fecha = min(fecha, ahora)  # algunos feeds traen fechas en el futuro
        if fecha < limite:
            continue
        cuerpo = e.get("summary") or ""
        if not cuerpo and e.get("content"):
            cuerpo = e["content"][0].get("value", "")
        resumen = limpiar_html(cuerpo)
        if normalizar(resumen) == normalizar(titulo):
            resumen = ""
        noticias.append({
            "id": hashlib.sha1(enlace.split("?")[0].encode()).hexdigest()[:16],
            "titulo": titulo,
            "enlace": enlace,
            "resumen": recortar(resumen, ajustes["max_resumen"]),
            "imagen": imagen_de(e),
            "fecha": int(fecha),
            "medio": fuente["medio"],
            "ambito": fuente.get("ambito", "nacional"),
            "categoria_fija": fuente.get("categoria"),
            "etiquetas": " ".join(t.get("term", "") for t in e.get("tags") or []),
        })
    return noticias, None


# -------------------------------------------------------- clasificación ----

def preparar_categorias(categorias: dict) -> list[tuple[str, list[str]]]:
    return [(nombre, [f" {normalizar(p)} " for p in palabras])
            for nombre, palabras in categorias.items()]


def clasificar(noticia: dict, categorias: list[tuple[str, list[str]]]) -> str:
    if noticia["categoria_fija"]:
        return noticia["categoria_fija"]
    # El título y las etiquetas del medio pesan más que el resumen.
    fuerte = f" {normalizar(noticia['titulo'] + ' ' + noticia['etiquetas'])} "
    debil = f" {normalizar(noticia['resumen'])} "
    mejor, mejor_puntaje = None, 0
    for nombre, palabras in categorias:
        puntaje = sum(2 * (p in fuerte) + (p in debil) for p in palabras)
        if puntaje > mejor_puntaje:
            mejor, mejor_puntaje = nombre, puntaje
    if mejor:
        return mejor
    return "Mundo" if noticia["ambito"] == "internacional" else "General"


# ---------------------------------------------- repetidas y relevancia ----

def parecidos(a: frozenset, b: frozenset, umbral: float) -> bool:
    if len(a) < 3 or len(b) < 3:
        return a == b and bool(a)
    return len(a & b) / len(a | b) >= umbral


def quitar_repetidas_del_medio(noticias: list[dict], umbral: float) -> list[dict]:
    """Si un medio vuelve a publicar su propia nota, queda solo la primera.

    Entre medios distintos NO se descarta nada: interesa la versión de cada uno.
    """
    vistas: dict[str, list[frozenset]] = {}
    unicas = []
    for n in sorted(noticias, key=lambda x: x["fecha"]):
        n["fichas"] = fichas_titulo(n["titulo"])
        previas = vistas.setdefault(n["medio"], [])
        if any(parecidos(n["fichas"], f, umbral) for f in previas):
            continue
        previas.append(n["fichas"])
        unicas.append(n)
    return unicas


def medir_cobertura(noticias: list[dict], umbral: float) -> list[dict]:
    """Cuenta cuántos medios tratan el mismo hecho (relevancia) y los enlaza.

    Cada nota sigue siendo una tarjeta aparte.
    """
    grupos: list[dict] = []
    for n in noticias:  # vienen de la más antigua a la más nueva
        destino = next((g for g in grupos if parecidos(n["fichas"], g["fichas"], umbral)), None)
        if destino is None:
            grupos.append({"fichas": n["fichas"], "miembros": [n]})
        else:
            destino["miembros"].append(n)

    historias = []
    for g in grupos:
        medios = {m["medio"] for m in g["miembros"]}
        for n in g["miembros"]:
            historias.append({
                "id": n["id"],
                "titulo": n["titulo"],
                "resumen": n["resumen"],
                "imagen": n["imagen"],
                "enlace": n["enlace"],
                "medio": n["medio"],
                "otros_medios": [{"medio": m["medio"], "enlace": m["enlace"]}
                                 for m in g["miembros"] if m["medio"] != n["medio"]],
                "cobertura": len(medios),
                "fecha": n["fecha"],
                "ambito": n["ambito"],
                "categoria": n["categoria"],
            })
    historias.sort(key=lambda h: (h["cobertura"], h["fecha"]), reverse=True)
    return historias


# ------------------------------------------------------------- telegram ----

def llamar_telegram(token: str, metodo: str, datos: dict) -> tuple[bool, str]:
    pedido = urllib.request.Request(
        f"{os.environ.get('TELEGRAM_API', 'https://api.telegram.org')}/bot{token}/{metodo}",
        data=json.dumps(datos).encode(),
        headers={"Content-Type": "application/json"},
    )
    for intento in range(2):
        try:
            with urllib.request.urlopen(pedido, timeout=30) as r:
                return True, ""
        except urllib.error.HTTPError as e:
            cuerpo = json.loads(e.read().decode() or "{}")
            espera = (cuerpo.get("parameters") or {}).get("retry_after")
            if e.code == 429 and espera and intento == 0:
                time.sleep(min(int(espera) + 1, 60))
                continue
            return False, cuerpo.get("description", f"HTTP {e.code}")
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
    return False, "límite de envíos de Telegram"


def texto_telegram(h: dict, limite: int) -> str:
    esc = html.escape
    icono = ICONOS.get(h["categoria"], "📰")
    cabecera = f"{icono} <b>{esc(h['categoria'])}</b> · {esc(h['ambito'].capitalize())}"
    pie = f"📰 {esc(h['medio'])}"
    if h["otros_medios"]:
        pie += " · también en " + ", ".join(esc(o["medio"]) for o in h["otros_medios"][:4])
    pie += f"\n<a href=\"{esc(h['enlace'], quote=True)}\">Leer la nota</a>"
    titulo = f"<b>{esc(h['titulo'])}</b>"
    fijo = len(cabecera) + len(titulo) + len(pie) + 8
    resumen = esc(recortar(h["resumen"], max(0, limite - fijo))) if limite - fijo > 40 else ""
    partes = [cabecera, titulo] + ([resumen] if resumen else []) + [pie]
    return "\n\n".join(partes)


def enviar_telegram(historias: list[dict], enviadas: dict, ajustes: dict,
                    token: str, chat: str, ahora: float) -> int:
    umbral = ajustes["similitud_mismo_medio"]
    ya_por_medio: dict[str, list[frozenset]] = {}
    for registro in enviadas.values():
        ya_por_medio.setdefault(registro["medio"], []).append(fichas_titulo(registro["titulo"]))

    def ya_enviada(h: dict) -> bool:
        # Mismo enlace, o el mismo medio republicando una nota que ya se envió.
        fichas = fichas_titulo(h["titulo"])
        return h["id"] in enviadas or any(
            parecidos(fichas, f, umbral) for f in ya_por_medio.get(h["medio"], []))

    nuevas = [h for h in historias if not ya_enviada(h)]
    cupo_categoria: dict[str, int] = {}
    cola = []
    for h in nuevas:  # ya vienen ordenadas por relevancia
        usados = cupo_categoria.get(h["categoria"], 0)
        if usados < ajustes["telegram_max_por_categoria"]:
            cupo_categoria[h["categoria"]] = usados + 1
            cola.append(h)
    cola = cola[: ajustes["telegram_max_por_corrida"]]
    cola.sort(key=lambda h: h["categoria"])

    exitos = 0
    for h in cola:
        ok, error = False, ""
        if h["imagen"]:
            ok, error = llamar_telegram(token, "sendPhoto", {
                "chat_id": chat, "photo": h["imagen"], "parse_mode": "HTML",
                "caption": texto_telegram(h, 1024),
            })
        if not ok:  # sin imagen, o Telegram no pudo descargarla
            ok, error = llamar_telegram(token, "sendMessage", {
                "chat_id": chat, "parse_mode": "HTML", "text": texto_telegram(h, 4096),
            })
        if ok:
            exitos += 1
            enviadas[h["id"]] = {"t": int(ahora), "medio": h["medio"], "titulo": h["titulo"]}
        else:
            print(f"  ! Telegram rechazó «{h['titulo'][:60]}»: {error}", file=sys.stderr)
        time.sleep(ajustes["telegram_pausa_segundos"])
    return exitos


# ----------------------------------------------------------------- main ----

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fuentes", default=str(RAIZ / "fuentes.json"))
    parser.add_argument("--sin-telegram", action="store_true")
    args = parser.parse_args()

    config = json.loads(Path(args.fuentes).read_text(encoding="utf-8"))
    ajustes = {**AJUSTES_BASE, **config.get("ajustes", {})}
    categorias = preparar_categorias(config["categorias"])
    fuentes = config["fuentes"]
    ahora = time.time()

    with ThreadPoolExecutor(max_workers=12) as pool:
        resultados = list(pool.map(lambda f: leer_fuente(f, ahora, ajustes), fuentes))

    noticias, estado_fuentes = [], []
    for fuente, (items, error) in zip(fuentes, resultados):
        estado_fuentes.append({"medio": fuente["medio"], "ambito": fuente.get("ambito", "nacional"),
                               "noticias": len(items), "error": error})
        noticias.extend(items)
        marca = f"ERROR {error}" if error else f"{len(items)} noticias"
        print(f"  {fuente['medio']:<28} {marca}")

    # Un mismo enlace puede venir en dos feeds del mismo medio.
    unicas = list({n["id"]: n for n in noticias}.values())
    for n in unicas:
        n["categoria"] = clasificar(n, categorias)
    sin_repetir = quitar_repetidas_del_medio(unicas, ajustes["similitud_mismo_medio"])
    historias = medir_cobertura(sin_repetir, ajustes["similitud_entre_medios"])

    caidas = [e for e in estado_fuentes if e["error"]]
    print(f"\n{len(fuentes) - len(caidas)}/{len(fuentes)} fuentes respondieron · "
          f"{len(unicas)} noticias · {len(unicas) - len(historias)} repetidas del mismo medio descartadas")

    if len(caidas) == len(fuentes):
        print("Ninguna fuente respondió; no se toca el tablero.", file=sys.stderr)
        return 1

    SALIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_JSON.write_text(json.dumps({
        "generado": int(ahora),
        "categorias": list(config["categorias"]) + ["Mundo", "General"],
        "fuentes": estado_fuentes,
        "historias": historias[: ajustes["max_tablero"]],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Tablero actualizado: {SALIDA_JSON.relative_to(RAIZ)}")

    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if args.sin_telegram:
        print("Telegram omitido (--sin-telegram).")
    elif not (token and chat):
        print("Telegram omitido: faltan TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.")
    else:
        enviadas = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
        cantidad = enviar_telegram(historias, enviadas, ajustes, token, chat, ahora)
        vence = ahora - ajustes["dias_memoria"] * 86400
        enviadas = {i: r for i, r in enviadas.items() if r["t"] >= vence}
        ESTADO.parent.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps(enviadas, indent=0), encoding="utf-8")
        print(f"Telegram: {cantidad} noticias enviadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
