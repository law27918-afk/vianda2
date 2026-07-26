from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.database import get_db

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("/", response_model=list[schemas.RecipeOut])
def list_recipes(q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Recipe)
    if q:
        query = query.filter(models.Recipe.name.ilike(f"%{q}%"))
    return query.order_by(models.Recipe.created_at.desc()).all()


@router.get("/{recipe_id}", response_model=schemas.RecipeOut)
def get_recipe(recipe_id: str, db: Session = Depends(get_db)):
    recipe = db.query(models.Recipe).get(recipe_id)
    if not recipe:
        raise HTTPException(404, "Receta no encontrada")
    return recipe


@router.post("/", response_model=schemas.RecipeOut)
def create_recipe(payload: schemas.RecipeCreate, db: Session = Depends(get_db)):
    """Alta manual de receta, con sus ingredientes como texto libre."""
    recipe = models.Recipe(
        name=payload.name,
        source=models.RecipeSource.manual,
        servings=payload.servings,
        instructions=payload.instructions,
        prep_time_minutes=payload.prep_time_minutes,
        image_url=payload.image_url,
    )
    db.add(recipe)
    db.flush()

    for ing in payload.ingredients:
        db.add(models.RecipeIngredient(
            recipe_id=recipe.id,
            raw_text=ing.raw_text,
            quantity=ing.quantity,
            unit=ing.unit,
            ingredient_id=ing.ingredient_id,
        ))

    db.commit()
    db.refresh(recipe)
    return recipe


@router.post("/import", response_model=schemas.RecipeOut)
def import_recipe(payload: schemas.RecipeImportRequest, db: Session = Depends(get_db)):
    """
    Importa una receta desde una URL usando recipe-scrapers, que lee el
    JSON-LD (schema.org/Recipe) que casi todo sitio de recetas incluye.
    Los ingredientes quedan como texto libre (raw_text); vincularlos a
    `ingredients` del catálogo propio se hace después, a mano, desde la UI.
    """
    try:
        from recipe_scrapers import scrape_me
    except ImportError:
        raise HTTPException(500, "recipe-scrapers no está instalado")

    try:
        scraper = scrape_me(payload.url)
    except Exception as e:
        raise HTTPException(400, f"No se pudo leer la receta de esa URL: {e}")

    try:
        servings_raw = scraper.yields()
        servings = int("".join(filter(str.isdigit, servings_raw)) or 4)
    except Exception:
        servings = 4

    try:
        prep_time = scraper.total_time()
    except Exception:
        prep_time = None

    try:
        image_url = scraper.image()
    except Exception:
        image_url = None

    try:
        instructions = scraper.instructions()
    except Exception:
        instructions = None

    recipe = models.Recipe(
        name=scraper.title(),
        source=models.RecipeSource.importada,
        source_url=payload.url,
        servings=servings,
        instructions=instructions,
        prep_time_minutes=prep_time,
        image_url=image_url,
    )
    db.add(recipe)
    db.flush()

    for line in scraper.ingredients():
        db.add(models.RecipeIngredient(recipe_id=recipe.id, raw_text=line))

    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: str, db: Session = Depends(get_db)):
    recipe = db.query(models.Recipe).get(recipe_id)
    if not recipe:
        raise HTTPException(404, "Receta no encontrada")
    db.delete(recipe)
    db.commit()
    return {"ok": True}
