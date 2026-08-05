import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.database import get_db

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("/", response_model=list[schemas.IngredientOut])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(models.Ingredient).all()


@router.post("/", response_model=schemas.IngredientOut)
def create_ingredient(payload: schemas.IngredientCreate, db: Session = Depends(get_db)):
    ing = models.Ingredient(**payload.model_dump())
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


@router.patch("/{ingredient_id}", response_model=schemas.IngredientOut)
def update_ingredient(ingredient_id: str, payload: schemas.IngredientCreate, db: Session = Depends(get_db)):
    """Permite, entre otras cosas, ajustar exclude_keywords para afinar la
    búsqueda de productos de este ingrediente (ej: evitar que "arroz" traiga
    "arroz con leche")."""
    ing = db.query(models.Ingredient).get(ingredient_id)
    if not ing:
        raise HTTPException(404, "Ingrediente no encontrado")
    for k, v in payload.model_dump().items():
        setattr(ing, k, v)
    db.commit()
    db.refresh(ing)
    return ing


@router.post("/{ingredient_id}/link/{store_product_id}")
def link_ingredient_to_product(ingredient_id: str, store_product_id: str, is_preferred: bool = False, db: Session = Depends(get_db)):
    ing = db.query(models.Ingredient).get(ingredient_id)
    product = db.query(models.StoreProduct).get(store_product_id)
    if not ing or not product:
        raise HTTPException(404, "Ingrediente o producto no encontrado")
    link = models.IngredientProductLink(
        ingredient_id=ingredient_id,
        store_product_id=store_product_id,
        is_preferred=is_preferred,
    )
    db.add(link)
    db.commit()
    return {"ok": True}


@router.delete("/{ingredient_id}/link/{link_id}")
def unlink_ingredient_product(ingredient_id: str, link_id: str, db: Session = Depends(get_db)):
    link = db.query(models.IngredientProductLink).get(link_id)
    if not link or link.ingredient_id != ingredient_id:
        raise HTTPException(404, "Vínculo no encontrado")
    db.delete(link)
    db.commit()
    return {"ok": True}


def _normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


@router.get("/products/search", response_model=list[schemas.StoreProductOut])
def search_store_products(
    q: str,
    exclude: str | None = None,
    category_hint: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Búsqueda de productos del catálogo, pensada para no confundir productos
    parecidos (ej: "arroz blanco" vs "arroz con leche"):

    - Cada PALABRA de `q` debe aparecer como palabra completa (no substring
      suelto) en el nombre del producto — así "arroz" no matchea "arrozal"
      ni cosas raras, pero tampoco excluye por accidente variantes válidas.
    - `exclude`: palabras separadas por coma; si CUALQUIERA aparece en el
      nombre del producto, ese producto se descarta. Se usa normalmente con
      el `exclude_keywords` guardado en el Ingredient vinculado
      (ej: exclude="con leche,dulce" para el ingrediente "arroz blanco").
    - `category_hint`: si se pasa, los productos de esa categoría (prefijo)
      se ordenan primero.
    - Resultados ordenados por: coincidencia más específica primero, luego precio.
    """
    q_norm = _normalizar(q)
    palabras = [p for p in re.split(r"\s+", q_norm) if p]
    if not palabras:
        return []

    exclude_words = [_normalizar(w) for w in (exclude or "").split(",") if w.strip()]

    # Se buscan candidatos por separado en cada tienda (en vez de un límite
    # global sin orden) para que ninguna tienda quede eclipsada por otra si
    # los productos están agrupados físicamente en la tabla (ej: por cómo se
    # cargó el CSV). Sin esto, una búsqueda podía traer 500 candidatos casi
    # todos de una sola tienda y nunca llegar a ver productos de la otra.
    tiendas = [row[0] for row in db.query(models.StoreProduct.store).distinct().all()]
    if not tiendas:
        tiendas = [None]

    candidatos = []
    for tienda in tiendas:
        query = db.query(models.StoreProduct).filter(models.StoreProduct.name.ilike(f"%{palabras[0]}%"))
        if tienda is not None:
            query = query.filter(models.StoreProduct.store == tienda)
        candidatos.extend(query.limit(250).all())

    resultados = []
    for prod in candidatos:
        nombre_norm = _normalizar(prod.name)
        nombre_tokens = set(re.split(r"\W+", nombre_norm))

        # todas las palabras de la búsqueda deben estar como palabra completa
        if not all(p in nombre_tokens or p in nombre_norm for p in palabras):
            continue

        # ninguna palabra de exclusión debe aparecer
        if any(ex and ex in nombre_norm for ex in exclude_words):
            continue

        # score de relevancia: coincide con la categoría sugerida primero,
        # luego nombre más corto (más específico/menos "ruido"), luego precio
        categoria_prioridad = 0 if category_hint and prod.category and prod.category.startswith(category_hint) else 1
        resultados.append(((categoria_prioridad, len(nombre_norm), prod.price), prod))

    resultados.sort(key=lambda t: t[0])
    return [prod for _, prod in resultados[:30]]
