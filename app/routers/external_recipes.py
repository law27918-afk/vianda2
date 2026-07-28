"""
Búsqueda de recetas en TheMealDB (API pública gratuita, en inglés).
Se usa como fuente externa además del recetario propio: el usuario busca,
ve el detalle, y decide si la importa a su recetario local (donde ya puede
editarla, vincular ingredientes a productos, etc.) o la descarta.

Nota: TheMealDB devuelve nombres/instrucciones en inglés. No se traduce
automáticamente — el usuario puede editar el nombre/ingredientes después
de importar si quiere.
"""

import re

import requests
from fastapi import APIRouter, HTTPException

from app import schemas

router = APIRouter(prefix="/external-recipes", tags=["external-recipes"])

THEMEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"


def _combinar_ingredientes(meal: dict) -> list[str]:
    """TheMealDB devuelve strIngredient1..20 y strMeasure1..20 por separado;
    los combinamos en líneas tipo '200g chicken breast'."""
    lineas = []
    for i in range(1, 21):
        ingrediente = (meal.get(f"strIngredient{i}") or "").strip()
        medida = (meal.get(f"strMeasure{i}") or "").strip()
        if not ingrediente:
            continue
        linea = f"{medida} {ingrediente}".strip() if medida else ingrediente
        lineas.append(linea)
    return lineas


@router.get("/search", response_model=list[schemas.ExternalRecipeSummary])
def search_external_recipes(q: str):
    try:
        resp = requests.get(f"{THEMEALDB_BASE}/search.php", params={"s": q}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(502, f"No se pudo conectar con la API de recetas externa: {e}")

    data = resp.json()
    meals = data.get("meals") or []
    return [
        schemas.ExternalRecipeSummary(
            external_id=m["idMeal"],
            name=m["strMeal"],
            image_url=m.get("strMealThumb"),
            category=m.get("strCategory"),
            area=m.get("strArea"),
        )
        for m in meals
    ]


@router.get("/{external_id}", response_model=schemas.ExternalRecipeDetail)
def get_external_recipe(external_id: str):
    try:
        resp = requests.get(f"{THEMEALDB_BASE}/lookup.php", params={"i": external_id}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(502, f"No se pudo conectar con la API de recetas externa: {e}")

    data = resp.json()
    meals = data.get("meals") or []
    if not meals:
        raise HTTPException(404, "Receta externa no encontrada")

    m = meals[0]
    return schemas.ExternalRecipeDetail(
        external_id=m["idMeal"],
        name=m["strMeal"],
        image_url=m.get("strMealThumb"),
        category=m.get("strCategory"),
        area=m.get("strArea"),
        instructions=m.get("strInstructions"),
        ingredients=_combinar_ingredientes(m),
    )
