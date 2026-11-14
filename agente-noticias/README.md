# Agente de noticias

Monitor de noticias para una redacción. Cada 30 minutos lee los feeds RSS de
medios nacionales e internacionales, los clasifica por categoría y entrega:

- **Tablero web** (`docs/index.html`): tarjetas con imagen, resumen, medio,
  filtros por categoría y ámbito, buscador y botón "Copiar".
- **Telegram**: las noticias nuevas más relevantes, con foto, resumen y enlace.

Todo es gratuito: corre en GitHub Actions, el tablero se publica con GitHub
Pages y Telegram no cobra por los bots. No usa ninguna API de pago; el resumen
es el que publica cada medio en su feed.

## Reglas de repetidas

- Entre medios distintos **no se descarta nada**: cada medio conserva su
  versión. La etiqueta "N medios" indica cuántos tratan el mismo hecho y sirve
  para ordenar por relevancia.
- Dentro de un mismo medio, si vuelve a publicar su propia nota (título muy
  parecido), queda solo la primera. Tampoco se reenvía a Telegram.

## Puesta en marcha

1. **Repositorio propio.** Sube el contenido de esta carpeta a la raíz de un
   repositorio nuevo y **público** (así Actions y Pages son gratis sin límite).
2. **Bot de Telegram.** En Telegram habla con `@BotFather`, envía `/newbot` y
   guarda el token que te da.
3. **Grupo.** Crea el grupo de la redacción, agrega el bot y escribe cualquier
   mensaje. Abre `https://api.telegram.org/bot<TOKEN>/getUpdates` y copia el
   número de `"chat":{"id": ...}` (en grupos empieza con `-`).
4. **Secretos.** En el repositorio: Settings → Secrets and variables → Actions
   → New repository secret. Crea `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
5. **Tablero.** Settings → Pages → Source: "Deploy from a branch", rama `main`,
   carpeta `/docs`.
6. **Primera corrida.** Pestaña Actions → "Agente de noticias" → Run workflow.
   El registro lista cada fuente con sus noticias o su error.

## Ajustar

Todo se edita en `fuentes.json`:

- `fuentes`: medio, `ambito` (`nacional` o `internacional`) y URL del feed.
  Con `"categoria": "Deportes"` se fija la categoría de un feed temático.
- `categorias`: palabras clave de cada categoría.
- `ajustes`: `horas_ventana`, `telegram_max_por_categoria`,
  `telegram_max_por_corrida`, `similitud_mismo_medio`, entre otros (la lista
  completa está al inicio de `agente.py`).

## Probar en tu computadora

```bash
pip install -r requirements.txt
```

```bash
python agente.py --sin-telegram
```

```bash
python -m http.server 8000 -d docs
```

Luego abre `http://localhost:8000`.
