# Respaldo editorial gratuito · Inteligencia Artificial al Día

Este flujo de GitHub Actions **no publica en Instagram**, **no modifica Spotify** y no utiliza credenciales de Meta ni BiBaY.

Cada día aproximadamente a las 17:37 (Europe/Madrid) consulta fuentes RSS públicas, selecciona hasta 5 candidatos, excluye noticias repetidas del episodio más reciente y guarda un archivo JSON en los **Artifacts** de la ejecución (retención: 14 días). También permite una ejecución manual en la pestaña **Actions**.

El resultado es siempre **BORRADOR_SIN_PUBLICAR**, sin textos definitivos en español, imágenes licenciadas o aprobación editorial. Requiere comprobar hechos, derechos de imagen y duplicados de Instagram antes de publicar mediante n8n.

Archivos instalados exclusivamente en `.github/workflows/ia-editorial-respaldo.yml` y `editorial_ia/`. La tarea usa permisos de solo lectura (`contents: read`) y no escribe en el repositorio.

**Cómo ver el resultado:** GitHub → Actions → "IA al Día - respaldo editorial gratuito" → ejecución → "Artifacts" → `iad-radar-<id>`. Las ejecuciones programadas pueden retrasarse y los flujos se desactivan tras 60 días sin actividad en un repositorio público.

Fuente oficial de la documentación: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
