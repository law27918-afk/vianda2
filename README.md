# Vianda

App de meal planning para 2-4 personas: objetivos → plan semanal → recetas → lista de compras derivada del plan (con el precio más barato entre Super99 y Riba Smith).

## Arrancar

```bash
cp .env.example .env
# copia tu CSV a data/supermercados_unificado.csv
docker compose up --build
docker compose exec app python scripts/load_csv.py
```

API en http://localhost:8000/docs
Frontend en http://localhost:5173 (necesita internet en el navegador para cargar React/Babel desde CDN la primera vez).

## Flujo

1. Crear household (`POST /households`) y sus miembros.
2. Cargar el catálogo de precios: `scripts/load_csv.py` (correr cada vez que actualices el CSV).
3. Crear ingredientes propios (`POST /ingredients`) y vincularlos a productos del catálogo
   (`GET /ingredients/products/search?q=leche` → `POST /ingredients/{id}/link/{store_product_id}`).
4. Crear recetas manuales (`POST /recipes`) o importarlas de una URL (`POST /recipes/import`).
5. Crear un plan semanal (`POST /plans`) y agregar comidas día a día (`POST /plans/{id}/meals`),
   ajustando `servings_override` si ese día cocinan para menos o más personas.
6. Generar la lista de compras (`POST /plans/{id}/shopping-list/generate`).

## Por qué no hay microservicios

Para 2-4 usuarios, un monolito modular (un FastAPI, un Postgres) es más simple de mantener
que varios contenedores comunicándose entre sí. El optimizador (OR-Tools) y el ai-gateway (Ollama)
se agregan como módulos internos —no servicios— cuando de verdad se necesiten.

## Desplegar en Railway

1. Crea un servicio de **PostgreSQL** en el mismo proyecto de Railway (`+ New` → `Database` → `Add PostgreSQL`).
2. En el servicio del backend (este repo), pestaña **Variables**, agrega:
   - `DATABASE_URL` → referencia la del servicio Postgres (Railway te deja usar `${{Postgres.DATABASE_URL}}`
     si están en el mismo proyecto, o copia el connection string desde la pestaña "Connect" del Postgres).
   - `PORT` la inyecta Railway automáticamente, no hace falta configurarla a mano.
3. Redeploy. Revisa la pestaña **Deployments → Logs** si el servicio no arranca — la causa más común
   es que `DATABASE_URL` no esté seteada (por defecto el código intenta conectar a `db:5432`, que
   solo existe en el `docker-compose.yml` local).
4. Una vez arriba, carga el catálogo de precios corriendo `python scripts/load_csv.py` en el shell
   del servicio (Railway → servicio → `...` → "Run command", o vía `railway run`).
5. En `frontend/index.html`, la constante `API_BASE_URL` (arriba del todo del `<script>`) debe apuntar
   a la URL pública de tu servicio backend en Railway.

## Frontend

`frontend/index.html` es un único archivo HTML + JavaScript plano (sin frameworks, sin paso de build).
Todo el estado y la lógica de la app vive en ese archivo — se edita directamente, no requiere ninguna
herramienta externa para generarlo ni reconstruirlo.
